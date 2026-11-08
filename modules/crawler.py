#!/usr/bin/env python3
"""
CRAWLER.PY v7.3 — Advanced Stateful DOM Form Inspector & Red-Team Recon Engine
Senior Red Team Edition: Dynamic form input mapping, CSRF extraction, and adaptive auth probing.
Includes strategic asset/wallet/transaction route injection.
"""
import json
import random
import re
import sys
from urllib.parse import urlparse, urljoin
from bs4 import BeautifulSoup  # Robust HTML parser for deep DOM inspection

from modules.dom_sink_inspector import inspect_js_bundle

OTP_DEBUG_KEYS = ["otp", "code", "pin", "debug", "token", "verification", "secret", "auth_code"]

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
        sys.stdout.write("\033[95m[***] EVALUATING STATE-SKIPPING & BOLA VECTORS [***]\033[0m\n")
        sys.stdout.flush()
        
        vulnerabilities = []
        restricted_endpoints = self.state_graph[ApplicationState.AUTHENTICATED_ACTIVE].union(
            self.state_graph[ApplicationState.PRIVILEGED_ADMIN]
        )

        for ep in restricted_endpoints:
            status, headers, body = transport.request("GET", ep)
            if status in [200, 201]:
                sys.stdout.write(f"\033[91m[!] BINGO! State-Skipping / BOLA Vulnerability detected at: {ep} [HTTP {status}]\033[0m\n")
                vulnerabilities.append(ep)
            else:
                sys.stdout.write(f"\033[90m[-] Protected state gate enforced at {ep} [HTTP {status}]\033[0m\n")
            sys.stdout.flush()
        return vulnerabilities

def log(msg, color="\033[92m"):
    sys.stdout.write(f"{color}{msg}\033[0m\n")
    sys.stdout.flush()

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
    session_output = transport.cookie_jar
    operator_creds = {}

    target_forms = [f for f in form_intels if any(k in f.get('action', '').lower() for k in ['login', 'register', 'signin', 'signup', 'auth'])]
    
    if not target_forms:
        target_forms = [
            {"action": "/api/auth/register", "method": "POST", "inputs": [{"name": "email"}, {"name": "password"}, {"name": "username"}]},
            {"action": "/user/register", "method": "POST", "inputs": [{"name": "email"}, {"name": "password"}]}
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
            elif 'token' in name or 'csrf' in name:
                payload[inp['name']] = inp.get('default', 'dummy_token')
            else:
                payload[inp['name']] = f"test_{rand_id}"

        if not any('email' in k.lower() for k in payload):
            payload['email'] = operator_email
        if not any('pass' in k.lower() for k in payload):
            payload['password'] = operator_pass

        log(f"[*] Probing auth action [{method}] {action_url} with mapped payload fields: {list(payload.keys())}", "\033[96m")
        
        status, headers, body = transport.request(method, action_url, payload=payload)
        detected_codes = inspect_json_for_leaked_codes(body)
        if detected_codes:
            leaked_secrets.update(detected_codes)

        if status in [200, 201, 302]:
            cookie_header = headers.get("set-cookie")
            if cookie_header:
                extracted_cookies = {}
                for cookie_part in cookie_header.split(";"):
                    if "=" in cookie_part:
                        k, v = cookie_part.strip().split("=", 1)
                        if k.lower() not in ["path", "expires", "domain", "samesite", "secure", "httponly"]:
                            extracted_cookies[k] = v
                session_output = extracted_cookies if extracted_cookies else transport.cookie_jar
            
            operator_creds = payload
            log(f"[+] Auth gate interaction successful at {action_url} [HTTP {status}]", "\033[92m")
            return session_output, operator_creds, leaked_secrets

    return session_output, operator_creds, leaked_secrets

def crawl_target(transport):
    log("\n[***] INITIALIZING ADVANCED STATEFUL RECON & DOM CRAWLER (v7.3) [***]", "\033[95m")
    discovered_endpoints = set()
    discovered_scripts = set()
    all_forms_intel = []
    
    # Strategic seed paths including wallet, transaction, homepage, and asset routes
    seed_paths = [
        transport.base_path or "/", 
        "/homepage",
        "/home",
        "/wallet",
        "/transaction",
        "/transactions",
        "/login", 
        "/api", 
        "/signup", 
        "/dashboard", 
        "/admin", 
        "/settings", 
        "/transfer", 
        "/user/register",
        "/user/wallet",
        "/user/dashboard",
        "/api/user/wallet",
        "/api/v1/wallet"
    ]

    href_pattern = re.compile(r'href=["\']([^"\']+)["\']', re.I)
    action_pattern = re.compile(r'action=["\']([^"\']+)["\']', re.I)
    api_pattern = re.compile(r'["\'](/api/[^"\']+)["\']', re.I)
    script_pattern = re.compile(r'src=["\']([^"\']+\.js[^"\']*)["\']', re.I)
    endpoint_in_js = re.compile(r'["\'](/v?\d?/[a-zA-Z0-9_/_-]+)["\']', re.I)

    for path in seed_paths:
        status, headers, html = transport.request("GET", path)
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
        s_status, _, s_content = transport.request("GET", script_path)
        if s_status == 200 and isinstance(s_content, str):
            for match in endpoint_in_js.findall(s_content):
                if len(match) > 3 and not any(match.endswith(ext) for ext in ['.js', '.css', '.png']):
                    discovered_endpoints.add(match)
            try:
                hidden_routes, _ = inspect_js_bundle(s_content)
                for route in hidden_routes:
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

    return {
        "endpoints": filtered_endpoints,
        "state_graph": state_graph,
        "bola_vulnerabilities": bola_vulns,
        "session_cookie": session_cookie,
        "operator_credentials": operator_creds,
        "leaked_secrets": leaked_secrets
    }
