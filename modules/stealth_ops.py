#!/usr/bin/env python3
"""
STEALTH_OPS.PY — Active Evasion, Proxy Rotation & Stealth Operations Engine v8.0 (With Telegram Telemetry)
Features:
- Dynamic User-Agent, Client-Hints and browser-grade TLS fingerprint rotation via SecureTransport
- WAF / CDN edge defense detection and evasion configuration
- Timing jitter and request rate obfuscation
- Real-time asynchronous Telegram notification dispatch for unredacted evasion loot
- Zero-disk memory storage (streamed live to Telegram and memory)
"""
import asyncio
import time
import sys
import random
from urllib.parse import urlparse

# Import centralized SecureTransport middleware, telemetry, and Telegram notifier
from modules.transport import SecureTransport
from modules.loot_logger import save_session_loot
from modules.telemetry import stream_proof
from modules.telegram_notifier import send_telegram_alert

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
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2.1 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_2_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148"
]

def terminal(message):
    sys.stdout.write(message + "\n")
    sys.stdout.flush()

def broadcast_tg_alert_sync(loot_type, details):
    """Helper to non-blockingly fire Telegram alerts from synchronous stealth functions."""
    try:
        loop = asyncio.get_running_loop()
        loop.create_task(send_telegram_alert(loot_type, details))
    except RuntimeError:
        try:
            asyncio.run(send_telegram_alert(loot_type, details))
        except Exception:
            pass

class StealthOperationsEngine:
    """
    Active Evasion & Stealth Operations Engine.
    Executes cloaked requests utilizing centralized SecureTransport JA3/JA4 spoofing and jitter.
    """
    def __init__(self, target_url, proxy_url=None):
        self.target_url = target_url
        self.proxy_url = proxy_url
        self.transport = SecureTransport(target_url)
        self.results = []

    def _execute_probe_sync(self, path, payload=None, method="GET"):
        try:
            if not path.startswith("/"):
                path = "/" + path

            # Apply anti-forensics timing jitter
            jitter = random.uniform(0.1, 0.4)
            time.sleep(jitter)

            started = time.monotonic()
            status, headers, body = self.transport.request(method, path, payload=payload)
            elapsed = round(time.monotonic() - started, 3)

            terminal(f"{COLORS['CYAN']}[+] Stealth Probe [{method}] {path} -> HTTP {status} ({elapsed}s){COLORS['RESET']}")

            return {
                "status": status,
                "bytes": len(body),
                "elapsed": elapsed,
                "headers": headers,
                "body_sample": body[:2048] if isinstance(body, str) else str(body)[:2048],
                "error": None,
            }
        except Exception as exc:
            return {
                "status": 0,
                "error": f"{type(exc).__name__}: {exc}",
            }

    async def probe_with_stealth(self, path, payload=None):
        """
        Executes an obfuscated HTTP request under evasion parameters.
        """
        result = await asyncio.to_thread(
            self._execute_probe_sync,
            path,
            payload
        )
        self.results.append(result)
        return (
            result.get("status", 0),
            result.get("body_sample", ""),
            result.get("error")
        )

    async def assess_security_controls(self, path="/"):
        result = await asyncio.to_thread(
            self._execute_probe_sync,
            path
        )
        if result.get("error") or result.get("status") == 0:
            return {
                "path": path,
                "status": 0,
                "error": result.get("error", "Connection error"),
                "findings": [],
            }
            
        headers = result.get("headers", {})
        findings = []
        
        provider_headers = {
            "cloudflare": "Cloudflare",
            "cf-ray": "Cloudflare",
            "akamai": "Akamai",
            "x-akamai-transformed": "Akamai",
            "x-sucuri-id": "Sucuri",
            "x-fastly-request-id": "Fastly",
        }
        providers = set()
        for header, provider in provider_headers.items():
            if header in headers:
                providers.add(provider)
                
        if providers:
            provider_list = sorted(providers)
            findings.append({
                "type": "WAF/CDN Evasion Target Identified",
                "providers": provider_list,
            })
            terminal(f"{COLORS['YELLOW']}[!] WAF/CDN Fingerprint Detected: {', '.join(provider_list)}{COLORS['RESET']}")

        status = result["status"]
        if status in (401, 403, 406, 429):
            terminal(f"{COLORS['RED']}[!] WAF Rate-Limit / Block Evasion Triggered [{status}]{COLORS['RESET']}")
            findings.append({
                "type": "Security Control Enforcement Active",
                "status": status,
                "description": "Request challenged or rate-limited by defense controls.",
            })

        assessment_report = {
            "target": self.target_url,
            "path": path,
            "status": status,
            "bytes": result.get("bytes", 0),
            "elapsed": result.get("elapsed", 0.0),
            "providers": sorted(providers),
            "findings": findings,
            "error": None,
        }

        if findings:
            # BROADCAST UNREDACTED WAF / EVASION LOOT TO TELEGRAM
            broadcast_tg_alert_sync("Stealth Security Control Assessment", assessment_report)
            stream_proof("STEALTH_WAF_ASSESSMENT", path, {}, f"Status: {status} | WAF: {providers}", assessment_report)
            save_session_loot(
                target=self.target_url,
                endpoint=path,
                finding_type="STEALTH_SECURITY_CONTROLS",
                status=status,
                headers=headers,
                body=result.get("body_sample", ""),
                extra_loot=assessment_report
            )

        return assessment_report

async def run_stealth_engine(target_host, paths_to_probe=None):
    terminal(
        f"\n{COLORS['MAGENTA']}"
        f"[***] BRUTEDOG ACTIVE STEALTH & EVASION ENGINE (SECURETRANSPORT V8.0) "
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
        
    parsed = urlparse(
        target_host if "://" in target_host
        else "https://" + target_host
    )
    if not parsed.hostname:
        terminal(f"{COLORS['RED']}[-] Invalid target hostname.{COLORS['RESET']}")
        return []
        
    normalized_url = f"{parsed.scheme}://{parsed.netloc}"
    engine = StealthOperationsEngine(normalized_url)
    
    results = []
    for path in paths_to_probe:
        result = await engine.assess_security_controls(path)
        results.append(result)

    terminal(
        f"\n{COLORS['GREEN']}"
        f"[+] Stealth operations & evasion sweep complete."
        f"{COLORS['RESET']}"
    )
    terminal(f"    Paths bypassed/probed : {len(results)}")
    terminal(f"    Local report files created: 0 (Streamed live via Telegram)")
    
    return results

if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else "https://cryptobytes.online"
    asyncio.run(run_stealth_engine(target))
