#!/usr/bin/env python3
"""
LOADER.PY — Configuration & Wordlist Ingestion Engine v7.5
Features:
- Safe JSON target configuration parsing with exception handling
- High-performance wordlist ingestion with comment and whitespace filtering
- Automated directory path validation (`config/`)
"""
import json
import os

def load_targets(filepath="config/targets.json"):
    """
    Loads target definitions and scopes from JSON configuration.
    """
    if not os.path.exists(filepath):
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        raise FileNotFoundError(f"[!] Target configuration file not found: {filepath}. Directory created.")
    
    with open(filepath, "r", encoding="utf-8") as f:
        try:
            targets = json.load(f)
            return targets
        except json.JSONDecodeError as e:
            raise ValueError(f"[!] Invalid JSON format in {filepath}: {e}")

def load_wordlist(filepath="config/passwords.txt"):
    """
    Ingests credential wordlists, stripping whitespace and filtering out comments.
    """
    if not os.path.exists(filepath):
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        raise FileNotFoundError(f"[!] Wordlist file not found: {filepath}. Directory created.")
    
    with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
        passwords = [line.strip() for line in f if line.strip() and not line.startswith("#")]
    return passwords
