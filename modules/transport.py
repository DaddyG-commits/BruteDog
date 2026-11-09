#!/usr/bin/env python3
"""
TRANSPORT.PY v6.4 — Centralized Stealth HTTP, TLS Evasion & Behavioral Middleware
Ensures all modules share cookies, headers, and bypass edge firewalls seamlessly.
"""
import http.client
import json
import ssl
import socket
import time
from urllib.parse import urlsplit

# Import advanced evasion & behavioral modules
from modules.tls_evasion import create_spoofed_ssl_context
from modules.behavioral_mimic import apply_behavioral_jitter, get_randomized_hints

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

class SecureTransport:
    def __init__(self, target_url):
        parsed = urlsplit(target_url)
        self.host = parsed.hostname
        self.secure = parsed.scheme == "https"
        self.port = parsed.port or (443 if self.secure else 80)
        self.base_path = parsed.path.rstrip("/")
        self.cookie_jar = ""

    def update_cookies(self, new_cookies):
        if new_cookies:
            self.cookie_jar = new_cookies

    def request(self, method, path, payload=None, extra_headers=None, retries=3):
        # Inject randomized human-like velocity jitter to defeat anti-bot limiters
        apply_behavioral_jitter()

        endpoint = f"{self.base_path}{path}" if not path.startswith(self.base_path) else path
        
        headers = {
            "Host": self.host,
            "User-Agent": USER_AGENT,
            "Accept": "text/html,application/json,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Connection": "close"
        }

        # Inject randomized browser client hints
        headers.update(get_randomized_hints())

        if self.cookie_jar:
            headers["Cookie"] = self.cookie_jar

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

                return res.status, resp_headers, data

            except (ssl.SSLError, socket.timeout, ConnectionError, OSError):
                # If a socket drops mid-handshake or hits an EOF, back off slightly and retry
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