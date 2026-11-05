import asyncio
import sys
from modules.loader import load_targets, load_wordlist
from modules.engine import run_engine
from modules.logger import setup_logger

BANNER = r"""
  _                    ____   ____ _   _ _   _ ___ _   _  ____ 
 | |    ___   __ _  __ / ___| / ___| | | | \ | |_ _| \ | |/ ___|
 | |   / _ \ / _` |/ _ \___ \| |  _| |_| |  \| || ||  \| | |  _ 
 | |__| (_) | (_| | (_) |__) | |_| |  _  | |\  || || |\  | |_| |
 |_____\___/ \__, |\___/____/ \____|_| |_|_| \_|___|_| \_|\____|
             |___/                                              
"""

def main():
    # Initialize the structured logger (logs to console and 'logs/' folder)
    logger = setup_logger()

    print(BANNER)
    print("=" * 60)
    print("         SYSTEM TASK MONITOR & LOGGING ENGINE")
    print("=" * 60)

    try:
        logger.info("Loading configuration targets and wordlists...")
        targets = load_targets("config/targets.json")
        passwords = load_wordlist("config/passwords.txt")
    except Exception as e:
        logger.error(f"Configuration Error: {e}")
        sys.exit(1)

    print(f"[*] Loaded Dynamic Targets : {len(targets)} hosts")
    print(f"[*] Loaded Dictionary Keys : {len(passwords)} entries")
    print(f"[*] Starting execution pipeline...\n")
    logger.info(f"Execution started with {len(targets)} targets and {len(passwords)} passwords.")

    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    valid_hits, duration = asyncio.run(run_engine(targets, passwords))

    print("\n" + "=" * 60)
    print(f"[*] Execution Complete in {duration:.2f} seconds.")
    print(f"[*] Total Confirmed Matches: {len(valid_hits)}")
    print("=" * 60)
    
    logger.info(f"Execution completed in {duration:.2f}s. Total matches: {len(valid_hits)}")

if __name__ == "__main__":
    main()
