#!/usr/bin/env python3
"""
CRAWLER.PY v6.3 — Aggressive Stateful Recon, Auto-Provisioning & JSON Code Leak Inspector
Features:
- Integrated with centralized SecureTransport for TLS/cookie session synchronization
- Live autonomous test-account registration & session cookie/JWT capture
- Automated JSON response inspection & regex sniffing for leaked OTPs / debug codes
- Deep client-side JavaScript bundle & source code route harvesting (enhanced with DOM sink inspection)
- Aggressive HTML form action, method, and input mapping
- Zero-disk in-memory intelligence collection
"""
import json
import random
import re
import sys
import time
from urllib.parse import urlparse, urljoin, urlsplit

# Import the DOM sink inspector for advanced JS route harvesting
from modules.dom_sink_inspector import inspect_js_bundle

# Common keys developers accidentally leave in JSON responses or debug endpoints
OTP_DEBUG_KEYS = ["otp", "code", "pin", "debug", "token", "verification", "secret", "auth_code"]

def log(msg, color="\033[92m"):
    sys.stdout.write(f"{color}{msg}\033[0m\n")
    sys.stdout.flush()

def inspect_json_for_leaked_codes(response_body):
    """
    Scans JSON response bodies and raw strings for leaked OTPs, 
    debug codes, or temporary verification secrets left by developers.
    """
    leaked_codes = {}
    if not response_body:
        return leaked_codes
        
    try:
        data = json.loads(response_body)
        if isinstance(data, dict):
            for key, value in data.items():
                if any(k in key.lower() for k in OTP_DEBUG_KEYS):
                    leaked_codes[key] = value
        elif isinstance(data, list):
            pass
    except json.JSONDecodeError:
        pass

    # Regex fallback to sniff out unparsed keys or mixed HTML/JSON debug payloads
    for key in OTP_DEBUG_KEYS:
        pattern = rf'["\']?{key}["\']?\s*[:=]\s*["\']?([a-zA-Z0-9_\-]{4,12)["\']?'
        match = re.search(pattern, response_body, re.I)
        if match and key not in leaked_codes:
            leaked_codes[key] = match.group(1)
            
    return leaked_codes

def register_operator_account(transport, endpoints):
    """
    Intelligently identifies registration endpoints, provisions a burner account,
    captures session cookies/JWTs, and inspects JSON bodies for leaked OTP/debug codes.
    """
    log("[*] Searching for registration/signup vector to provision operator session...", "\033[94m")
    reg_paths = [ep for ep in endpoints if any(k in ep.lower() for k in ["register", "signup", "join", "create-account"])]
    if not reg_paths:
        reg_paths = ["/api/auth/register", "/api/register", "/register", "/signup"]
        
    rand_id = random.randint(10000, 99999)
    operator_email = f"brutedog_operator_{rand_id}@target-audit.com"
    operator_pass = f"P@ssw0rd_{rand_id}!"
    
    payload = {
        "email": operator_email,
        "username": f"operator_{rand_id}",
        "password": operator_pass
    }
    
    leaked_secrets = {}
    for path in reg_paths:
        status, headers, body = transport.request("POST", path, payload=payload)
        
        # Inspect response for JSON/OTP code leaks
        detected_codes = inspect_json_for_leaked_codes(body)
        if detected_codes:
            log(f"[!] BINGO! Developer leaked codes/tokens in JSON response at {path}: {detected_codes}", "\033[91m")
            leaked_secrets.update(detected_codes)

        if status in [200, 201, 302]:
            set_cookie = headers.get("set-cookie", transport.cookie_jar)
            log(f"[+] Autonomous account provisioned successfully at {path} [HTTP {status}]", "\033[92m")
            log(f"    └── Operator Identity: {operator_email}", "\033[96m")
            return set_cookie, payload, leaked_secrets
            
    log("[-] Direct registration auto-provisioning bypassed or requires manual parameters.", "\033[93m")
    return transport.cookie_jar, {}, leaked_secrets

def crawl_target(transport):
    log("\n[***] INITIALIZING AGGRESSIVE STATEFUL RECON & CRAWLER (v6.3) [***]", "\033[95m")
    discovered_endpoints = set()
    discovered_scripts = set()
    seed_paths = [transport.base_path or "/", "/login", "/api", "/signup", "/dashboard", "/admin", "/settings", "/transfer"]

    # Advanced regex patterns
    href_pattern = re.compile(r'href=["\']([^"\']+)["\']', re.I)
    action_pattern = re.compile(r'action=["\']([^"\']+)["\']', re.I)
    api_pattern = re.compile(r'["\'](/api/[^"\']+)["\']', re.I)
    script_pattern = re.compile(r'src=["\']([^"\']+\.js[^"\']*)["\']', re.I)
    endpoint_in_js = re.compile(r'["\'](/v?\d?/[a-zA-Z0-9_/_-]+)["\']', re.I)

    # Phase 1: Deep Seed Spidering
    for path in seed_paths:
        status, headers, html = transport.request("GET", path)
        if status == 0:
            continue
            
        log(f"[*] Recon Spider -> {path} [HTTP {status}]", "\033[94m")
        discovered_endpoints.add(path)

        # Sniff JSON leaks on general crawl responses too
        leaked_in_page = inspect_json_for_leaked_codes(html)
        if leaked_in_page:
            log(f"[!] Leaked data found in page response at {path}: {leaked_in_page}", "\033[91m")

        # Extract hrefs
        for link in href_pattern.findall(html):
            if link.startswith("http"):
                p = urlparse(link)
                if p.hostname == transport.host:
                    discovered_endpoints.add(p.path)
            elif link.startswith("/"):
                discovered_endpoints.add(link)

        # Extract form actions
        for action in action_pattern.findall(html):
            if action.startswith("/"):
                discovered_endpoints.add(action)

        # Extract API strings
        for api in api_pattern.findall(html):
            discovered_endpoints.add(api)

        # Extract JS bundle links (Dev Source Inspection)
        for script in script_pattern.findall(html):
            if script.startswith("/"):
                discovered_scripts.add(script)
            elif not script.startswith("http"):
                discovered_scripts.add(urljoin(path, script))

    # Phase 2: Client-Side JS Bundle Harvesting & DOM Sink Inspection
    log(f"[*] Harvesting {len(discovered_scripts)} client-side JavaScript source bundles for hidden routes...", "\033[94m")
    for script_path in list(discovered_scripts)[:15]:
        s_status, _, s_content = transport.request("GET", script_path)
        if s_status == 200:
            # Original regex check
            for match in endpoint_in_js.findall(s_content):
                if len(match) > 3 and not any(match.endswith(ext) for ext in ['.js', '.css', '.png']):
                    discovered_endpoints.add(match)
            
            # Integrated DOM sink inspector parse
            hidden_routes, _ = inspect_js_bundle(s_content)
            for route in hidden_routes:
                discovered_endpoints.add(route)

    # Filter out static assets
    filtered_endpoints = sorted(list({
        ep for ep in discovered_endpoints 
        if not any(ep.endswith(ext) for ext in ['.png', '.jpg', '.jpeg', '.css', '.ico', '.svg', '.woff', '.gif'])
    }))

    log(f"[+] Crawler Intelligence Complete. Discovered {len(filtered_endpoints)} unique active routes.", "\033[92m")

    # Phase 3: Autonomous Operator Provisioning & Code Leak Sniffing
    session_cookie, operator_creds, leaked_secrets = register_operator_account(transport, filtered_endpoints)

    return {
        "endpoints": filtered_endpoints,
        "session_cookie": session_cookie,
        "operator_credentials": operator_creds,
        "leaked_secrets": leaked_secrets
    }
