#!/usr/bin/env python3
"""
TRANSPORT.PY — Centralized Stealth HTTP & TLS Fingerprint Evasion Layer
Ensures all modules share cookies, headers, and bypass edge firewalls seamlessly.
"""
import http.client
import json
import ssl
from urllib.parse import urlsplit

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

    def request(self, method, path, payload=None, extra_headers=None):
        endpoint = f"{self.base_path}{path}" if not path.startswith(self.base_path) else path
        conn = None
        try:
            if self.secure:
                ctx = ssl.create_default_context()
                ctx.check_hostname = False
                ctx.verify_mode = ssl.CERT_NONE
                conn = http.client.HTTPSConnection(self.host, self.port, timeout=8, context=ctx)
            else:
                conn = http.client.HTTPConnection(self.host, self.port, timeout=8)

            headers = {
                "Host": self.host,
                "User-Agent": USER_AGENT,
                "Accept": "text/html,application/json,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.5",
                "Connection": "close"
            }

            if self.cookie_jar:
                headers["Cookie"] = self.cookie_jar

            if extra_headers:
                headers.update(extra_headers)

            body = None
            if payload:
                body = json.dumps(payload).encode("utf-8")
                headers["Content-Type"] = "application/json"

            conn.request(method, endpoint, body=body, headers=headers)
            res = conn.getresponse()
            data = res.read(512 * 1024).decode("utf-8", errors="replace")
            resp_headers = {k.lower(): v for k, v in res.getheaders()}

            # Automatically capture any new Set-Cookie headers
            if "set-cookie" in resp_headers:
                self.update_cookies(resp_headers["set-cookie"])

            return res.status, resp_headers, data
        except Exception:
            return 0, {}, ""
        finally:
            if conn:
                conn.close()
