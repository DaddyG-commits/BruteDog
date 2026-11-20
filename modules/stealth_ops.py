#!/usr/bin/env python3
"""
STEALTH_OPS.PY v8.6 — Transport Pacing & Security Control Assessment Module
"""
import asyncio
import hashlib
import inspect
import sys
import time
from urllib.parse import urlparse

from modules.behavioral_mimic import apply_behavioral_jitter
from modules.loot_logger import save_session_loot
from modules.telegram_notifier import send_telegram_alert
from modules.telemetry import stream_proof
from modules.transport import SecureTransport

COLORS = {
    "RED": "\033[91m",
    "GREEN": "\033[92m",
    "YELLOW": "\033[93m",
    "CYAN": "\033[96m",
    "MAGENTA": "\033[95m",
    "RESET": "\033[0m",
    "BOLD": "\033[1m",
}

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2.1 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64; rv:123.0) Gecko/20100101 Firefox/123.0",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_3_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148",
]


def terminal(message):
    sys.stdout.write(str(message) + "\n")
    sys.stdout.flush()


async def broadcast_tg_alert_async(loot_type, details):
    try:
        await send_telegram_alert(loot_type, details)
    except Exception:
        pass


def broadcast_tg_alert_sync(loot_type, details):
    """Schedules non-blocking notifications when invoked from synchronous code."""
    try:
        loop = asyncio.get_running_loop()
        if loop.is_running():
            task = loop.create_task(broadcast_tg_alert_async(loot_type, details))
            task.add_done_callback(lambda t: t.exception() if not t.cancelled() else None)
        else:
            asyncio.run(broadcast_tg_alert_async(loot_type, details))
    except RuntimeError:
        try:
            asyncio.run(broadcast_tg_alert_async(loot_type, details))
        except Exception:
            pass


class StealthOperationsEngine:
    """Executes paced transport requests and summarizes edge/HTTP control indicators."""

    def __init__(self, target_url, proxy_url=None):
        self.target_url = target_url
        self.proxy_url = proxy_url
        self.transport = SecureTransport(target_url)
        self.results = []

    async def close(self):
        close_fn = getattr(self.transport, "close", None) or getattr(self.transport, "aclose", None)
        if callable(close_fn):
            try:
                res = close_fn()
                if inspect.isawaitable(res):
                    await res
            except Exception:
                pass

    def _execute_probe_sync(self, path, payload=None, method="GET"):
        try:
            clean_path = str(path or "/")
            if not clean_path.startswith("/"):
                clean_path = "/" + clean_path

            apply_behavioral_jitter()

            started = time.monotonic()
            status, headers, body = self.transport.request(method, clean_path, payload=payload)
            elapsed = round(time.monotonic() - started, 3)

            terminal(f"{COLORS['CYAN']}[+] Probe [{method}] {clean_path} -> HTTP {status} ({elapsed}s){COLORS['RESET']}")

            body_str = body if isinstance(body, str) else str(body or "")
            loot_hash = hashlib.sha256(body_str.encode("utf-8", errors="ignore")).hexdigest()

            return {
                "path": clean_path,
                "status": int(status or 0),
                "bytes": len(body_str),
                "elapsed": elapsed,
                "headers": dict(headers) if isinstance(headers, dict) else {},
                "integrity_hash": loot_hash,
                "body_sample": body_str[:2048],
                "error": None,
            }
        except Exception as exc:
            return {
                "path": str(path or "/"),
                "status": 0,
                "bytes": 0,
                "elapsed": 0.0,
                "headers": {},
                "integrity_hash": "",
                "body_sample": "",
                "error": f"{type(exc).__name__}: {exc}",
            }

    async def probe_with_stealth(self, path, payload=None):
        """Executes a paced HTTP request and returns (status, body_sample, error)."""
        result = await asyncio.to_thread(self._execute_probe_sync, path, payload)
        self.results.append(result)
        return (
            result.get("status", 0),
            result.get("body_sample", ""),
            result.get("error"),
        )

    async def assess_security_controls(self, path="/", persist_on_signal: bool = False):
        result = await asyncio.to_thread(self._execute_probe_sync, path)
        self.results.append(result)

        if result.get("error") or result.get("status", 0) == 0:
            return {
                "path": result.get("path", path),
                "status": 0,
                "error": result.get("error", "Connection error"),
                "findings": [],
            }

        headers = result.get("headers", {})
        lower_headers = {str(k).lower(): str(v).lower() for k, v in headers.items()}
        findings = []

        provider_markers = {
            "cf-ray": "Cloudflare",
            "cf-cache-status": "Cloudflare",
            "x-akamai-transformed": "Akamai",
            "akamai-origin-hop": "Akamai",
            "x-sucuri-id": "Sucuri",
            "x-fastly-request-id": "Fastly",
        }
        providers = set()
        for header_key, provider in provider_markers.items():
            if header_key in lower_headers:
                providers.add(provider)

        server_val = lower_headers.get("server", "")
        if "cloudflare" in server_val:
            providers.add("Cloudflare")
        elif "akamai" in server_val:
            providers.add("Akamai")
        elif "fastly" in server_val:
            providers.add("Fastly")

        if providers:
            provider_list = sorted(providers)
            findings.append({
                "type": "Edge/CDN Control Identified",
                "providers": provider_list,
            })
            terminal(f"{COLORS['YELLOW']}[!] Edge/CDN Header Fingerprint: {', '.join(provider_list)}{COLORS['RESET']}")

        status = result["status"]
        if status in (401, 403, 406, 429):
            terminal(f"{COLORS['RED']}[!] Access / Rate-Limit Status [{status}] on {result['path']}{COLORS['RESET']}")
            findings.append({
                "type": "Access or Rate Control Response",
                "status": status,
                "description": "Endpoint returned a restricted or rate-limited HTTP status.",
            })

        assessment_report = {
            "target": self.target_url,
            "path": result["path"],
            "status": status,
            "bytes": result.get("bytes", 0),
            "elapsed": result.get("elapsed", 0.0),
            "integrity_hash": result.get("integrity_hash", ""),
            "providers": sorted(providers),
            "findings": findings,
            "error": None,
        }

        # Only persist/notify when explicitly requested and actionable edge throttling/auth signals appear
        if persist_on_signal and status in (401, 403, 429) and providers:
            broadcast_tg_alert_sync("Edge Control Enforcement Signal", assessment_report)
            stream_proof("EDGE_CONTROL_SIGNAL", result["path"], {}, f"Status: {status} | Edge: {sorted(providers)}", assessment_report)
            save_session_loot(
                target=self.target_url,
                endpoint=result["path"],
                finding_type="EDGE_CONTROL_SIGNAL",
                status=status,
                headers=headers,
                body=result.get("body_sample", ""),
                extra_loot=assessment_report,
            )

        return assessment_report


async def run_stealth_engine(target_host, paths_to_probe=None, persist_on_signal=False):
    terminal(
        f"\n{COLORS['MAGENTA']}"
        f"[***] BRUTEDOG TRANSPORT & CONTROL ASSESSMENT (SECURETRANSPORT V8.6) "
        f"[{target_host}] [***]"
        f"{COLORS['RESET']}"
    )
    if not paths_to_probe:
        paths_to_probe = [
            "/",
            "/api/health",
            "/login",
            "/admin",
        ]

    raw = str(target_host or "").strip()
    parsed = urlparse(raw if "://" in raw else "https://" + raw)
    if not parsed.hostname:
        terminal(f"{COLORS['RED']}[-] Invalid target hostname.{COLORS['RESET']}")
        return []

    normalized_url = f"{parsed.scheme}://{parsed.netloc}"
    engine = StealthOperationsEngine(normalized_url)
    results = []

    try:
        for path in paths_to_probe:
            result = await engine.assess_security_controls(path, persist_on_signal=persist_on_signal)
            results.append(result)
    finally:
        await engine.close()

    terminal(
        f"\n{COLORS['GREEN']}"
        f"[+] Transport & control assessment complete."
        f"{COLORS['RESET']}"
    )
    terminal(f"    Paths probed : {len(results)}")
    return results


if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else "https://example.invalid"
    asyncio.run(run_stealth_engine(target))


async def execute_stealth_operations(target_host, paths_to_probe=None, *args, **kwargs):
    return await run_stealth_engine(
        target_host,
        paths_to_probe=paths_to_probe,
        persist_on_signal=bool(kwargs.get("persist_on_signal", False)),
    )

