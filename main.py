import asyncio
import sys
from modules.loader import load_wordlist
from modules.engine import run_autonomous_engine

CYAN = "\033[96m"
GREEN = "\033[92m"
MAGENTA = "\033[95m"
YELLOW = "\033[93m"
RED = "\033[91m"
RESET = "\033[0m"
BOLD = "\033[1m"

BANNER = f"""{CYAN}{BOLD}
  ____             _        ____             
 |  _ \           | |      |  _ \            
 | |_) |_ __ _   _| |_ ___ | | | |___   __ _  
 |  _ <| '__| | | | __/ _ \| | | / _ \ / _` | 
 | |_) | |  | |_| | ||  __/| |_| | (_) | (_| | 
 |____/|_|   \__,_|\__\___||____/ \___/ \__, | 
                                         __/ | 
                                        |___/  
{RESET}{MAGENTA}=====================================================
      AUTONOMOUS RECONNAISSANCE & SCANNING ENGINE
====================================================={RESET}
"""

def main():
    print(BANNER)
    
    # Single clean entry point
    target = input(f"{CYAN}[?] Enter Target Domain or IP (e.g., cryptobyt.online): {RESET}").strip()
    if not target:
        print(f"{RED}[!] Target cannot be empty. Aborting.{RESET}")
        sys.exit(1)

    print(f"\n{YELLOW}[INFO] Loading dictionary payloads...{RESET}")
    try:
        passwords = load_wordlist("config/passwords.txt")
    except Exception as e:
        print(f"{RED}[!] Error loading passwords: {e}{RESET}")
        sys.exit(1)

    print(f"{GREEN}[*] Payload Loaded : {len(passwords)} candidates{RESET}")
    print(f"{BOLD}{MAGENTA}[*] Engaging autonomous discovery and scanning sequence...\n{RESET}")

    # Execute full autonomous loop
    hits, duration = asyncio.run(run_autonomous_engine(target, passwords))

    print(f"\n{MAGENTA}{'=' * 53}{RESET}")
    print(f"{CYAN}[*] Autonomous scan completed in {duration:.2f} seconds.{RESET}")
    if hits:
        print(f"{GREEN}{BOLD}[+] Mission Successful! Recovered {len(hits)} valid authorization(s).{RESET}")
    else:
        print(f"{YELLOW}[-] Scan complete. Target surface mapped; no active login vectors breached.{RESET}")
    print(f"{MAGENTA}{'=' * 53}{RESET}")

if __name__ == "__main__":
    main()
