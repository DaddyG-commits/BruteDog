import httpx
import logging
from typing import Dict, Any, Optional, Union

logger = logging.getLogger("BruteDog.SessionPool")

class PersistentSessionPool:
    """
    Manages persistent sessions, cookie jars, and headers across HTTP/2 multiplexed 
    requests to prevent session drops during high-concurrency race conditions.
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
        }
        logger.info(f"[+] Initialized PersistentSessionPool for target: {self.base_url} (HTTP/2: {self.http2})")

    def update_headers(self, new_headers: Dict[str, str]) -> None:
        """Dynamically update default headers (e.g., Authorization Bearer tokens)."""
        self.default_headers.update(new_headers)
        logger.debug(f"[+] Session headers updated: list of keys -> {list(new_headers.keys())}")

    def get_client(self, timeout: float = 10.0) -> httpx.Client:
        """Returns a synchronous httpx.Client sharing the persistent cookie jar."""
        client = httpx.Client(
            base_url=self.base_url,
            cookies=self.cookie_jar,
            headers=self.default_headers,
            verify=self.verify_ssl,
            http2=self.http2,
            timeout=timeout,
            follow_redirects=True
        )
        return client

    def get_async_client(self, timeout: float = 10.0) -> httpx.AsyncClient:
        """Returns an asynchronous httpx.AsyncClient sharing the persistent cookie jar and HTTP/2 settings."""
        client = httpx.AsyncClient(
            base_url=self.base_url,
            cookies=self.cookie_jar,
            headers=self.default_headers,
            verify=self.verify_ssl,
            http2=self.http2,
            timeout=timeout,
            follow_redirects=True
        )
        return client

    def sync_cookies(self, response_cookies: Union[httpx.Cookies, dict, str]) -> None:
        """Manually synchronize external cookie responses into the master jar safely, handling strings/dicts."""
        try:
            if isinstance(response_cookies, str):
                # If a raw string cookie header is passed, parse it safely
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
