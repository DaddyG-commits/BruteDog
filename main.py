import asyncio
import sys
import time
from modules.loader import load_wordlist
from modules.parser import parse_target_source
from modules.engine import run_autonomous_engine

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

# Scaled down by 50% for optimal mobile terminal view (3 rows instead of 6)
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
    
    # Futuristic input prompt
    target = input(f"{CYAN}{BOLD}[SYS_PROMPT] >> Enter Target Host/Domain (e.g., cryptobyt.online): {RESET}").strip()
    if not target:
        print(f"{RED}[CRITICAL] Target parameter missing. Aborting protocol.{RESET}")
        sys.exit(1)

    print(f"\n{YELLOW}[INIT] Injecting payloads and loading local wordlist dictionaries...{RESET}")
    time.sleep(0.4)
    
    try:
        passwords = load_wordlist("config/passwords.txt")
    except Exception as e:
        print(f"{RED}[ERROR] Wordlist mount failed: {e}{RESET}")
        sys.exit(1)

    print(f"{GREEN}[SUCCESS] Wordlist Secured : {len(passwords)} candidate vectors loaded.{RESET}")

    # Step 1: Real-time DOM & Source Code Vulnerability Audit
    asyncio.run(parse_target_source(target))

    print(f"{MAGENTA}{BOLD}[ENGINE] Spawning asynchronous threads and initializing socket rings...\n{RESET}")
    time.sleep(0.5)

    # Step 2: Launch Wireshark Packet Telemetry & Stealth Brute-Force Engine
    hits, duration = asyncio.run(run_autonomous_engine(target, passwords))

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
