#!/usr/bin/env python3
"""
KEYHARVESTER.PY — Active Cryptographic Secret & Artifact Discovery Engine
Features:
- Live unredacted extraction of EVM private keys, Bitcoin WIFs, and BIP39 seed phrases
- Direct on-screen terminal streaming of harvested raw secrets and API tokens
- Zero-disk memory storage (no report files written)
"""
import re
import sys
import hashlib

COLORS = {
    "RED": "\033[91m",
    "GREEN": "\033[92m",
    "YELLOW": "\033[93m",
    "CYAN": "\033[96m",
    "MAGENTA": "\033[95m",
    "RESET": "\033[0m",
    "BOLD": "\033[1m",
}

def terminal(message):
    sys.stdout.write(message + "\n")
    sys.stdout.flush()

def is_valid_bip39_seed(text):
    if not isinstance(text, str):
        return False
    words = text.strip().lower().split()
    if len(words) not in (12, 15, 18, 21, 24):
        return False
    if not all(
        word.isalpha() and 1 <= len(word) <= 8
        for word in words
    ):
        return False
    return True

def is_valid_evm_key(key_str):
    if not isinstance(key_str, str):
        return False
    clean = key_str.strip()
    if clean.startswith(("0x", "0X")):
        clean = clean[2:]
    if not re.fullmatch(r"[a-fA-F0-9]{64}", clean):
        return False
    try:
        value = int(clean, 16)
    except ValueError:
        return False
    curve_order = (
        0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFE
        BAAEDCE6AF48A03BBFD25E8CD0364141
    )
    return 0 < value < curve_order

def _record_finding(findings, seen, secret, secret_type, offset):
    """
    Record and actively stream unredacted harvested secrets live to the terminal.
    """
    dedup_key = (secret_type, secret)
    if dedup_key in seen:
        return
    seen.add(dedup_key)
    
    findings.append({
        "type": secret_type,
        "secret_value": secret,
        "source": "Supplied target response",
        "offset": offset,
        "exposed": True,
    })
    
    terminal(
        f"\n{COLORS['RED']}{COLORS['BOLD']}[***] LIVE SECRET EXPOSURE HARVESTED [{secret_type}] [***]{COLORS['RESET']}"
    )
    terminal(
        f"  ├── Offset      : {offset}"
    )
    terminal(
        f"  └── Raw Secret  : {COLORS['GREEN']}{secret}{COLORS['RESET']}"
    )

def harvest_private_keys(target_source_data=""):
    """
    Active Cryptographic Secret-Exposure & Harvesting Engine.
    Scans target response text for EVM keys, Bitcoin WIFs, and seed phrases,
    streaming raw unredacted values live to stdout.
    """
    terminal(
        f"\n{COLORS['MAGENTA']}[***] "
        f"ACTIVE CRYPTOGRAPHIC SECRET DISCOVERY & HARVESTING "
        f"[***]{COLORS['RESET']}"
    )
    findings = []
    seen = set()
    
    if not target_source_data:
        terminal(
            f"{COLORS['CYAN']}[*] No target response supplied for harvesting."
            f"{COLORS['RESET']}"
        )
        return findings

    content = str(target_source_data)
    
    # -------------------------------------------------
    # 1. EVM Private-Key Candidates
    # -------------------------------------------------
    hex_pattern = re.compile(
        r"(?<![a-fA-F0-9])(?:0x)?[a-fA-F0-9]{64}"
        r"(?![a-fA-F0-9])"
    )
    for match in hex_pattern.finditer(content):
        candidate = match.group(0)
        if is_valid_evm_key(candidate):
            _record_finding(
                findings,
                seen,
                candidate,
                "EVM Private Key",
                match.start()
            )

    # -------------------------------------------------
    # 2. Bitcoin WIF Candidates
    # -------------------------------------------------
    wif_pattern = re.compile(
        r"(?<![1-9A-HJ-NP-Za-km-z])"
        r"[5KL][1-9A-HJ-NP-Za-km-z]{50,51}"
        r"(?![1-9A-HJ-NP-Za-km-z])"
    )
    for match in wif_pattern.finditer(content):
        _record_finding(
            findings,
            seen,
            match.group(0),
            "Bitcoin WIF",
            match.start()
        )

    # -------------------------------------------------
    # 3. Mnemonic Seed Candidates
    # -------------------------------------------------
    word_pattern = re.compile(r"\b[a-zA-Z]{1,8}\b")
    words = list(word_pattern.finditer(content))
    allowed_lengths = (12, 15, 18, 21, 24)
    for window_size in allowed_lengths:
        if len(words) < window_size:
            continue
        for index in range(len(words) - window_size + 1):
            window = words[index:index + window_size]
            candidate = " ".join(
                item.group(0).lower()
                for item in window
            )
            if not is_valid_bip39_seed(candidate):
                continue
            _record_finding(
                findings,
                seen,
                candidate,
                "BIP39 Seed Phrase",
                window[0].start()
            )
            break

    # -------------------------------------------------
    # 4. Final Terminal Summary
    # -------------------------------------------------
    terminal(
        f"\n{COLORS['GREEN']}[+] Cryptographic harvesting scan complete."
        f"{COLORS['RESET']}"
    )
    terminal(
        f"    Total Secrets Harvested : {len(findings)}"
    )
    terminal(
        f"    Local Files Created     : 0 (Streamed live on screen)"
    )
    
    return findings