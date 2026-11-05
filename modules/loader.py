import json
import os

def load_targets(filepath="config/targets.json"):
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"[!] Target configuration file not found: {filepath}")
    
    with open(filepath, "r") as f:
        try:
            targets = json.load(f)
            return targets
        except json.JSONDecodeError as e:
            raise ValueError(f"[!] Invalid JSON format in {filepath}: {e}")

def load_wordlist(filepath="config/passwords.txt"):
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"[!] Wordlist file not found: {filepath}")
    
    with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
        # Read lines, strip whitespace, and filter out empty lines or comments
        passwords = [line.strip() for line in f if line.strip() and not line.startswith("#")]
    return passwords
