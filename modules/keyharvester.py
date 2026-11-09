#!/usr/bin/env python3
"""
KEYHARVESTER.PY — Active Cryptographic Secret & Artifact Discovery Engine v7.5
Features:
- Live unredacted extraction of EVM private keys, Bitcoin WIFs, and BIP39 seed phrases
- Direct on-screen terminal streaming of harvested raw secrets and API tokens
- Automated immutable disk persistence (loot_output/) via centralized framework logger
- Anti-noise validation filters for high-precision cryptographic detection
"""
import re
import sys
import hashlib

# Import centralized framework telemetry and immutable loot persistence
from modules.loot_logger import save_session_loot
from modules.telemetry import stream_proof

COLORS = {
    "RED": "\033[91m",
    "GREEN": "\033[92m",
    "YELLOW": "\033[93m",
    "CYAN": "\033[96m",
    "MAGENTA": "\033[95m",
    "RESET": "\033[0m",
    "BOLD": "\033[1m",
}

# Common non-seed words appearing in HTML logs or error text to prevent false positives
NOISE_WORDS = {
    "target", "https", "http", "online", "results", "url", "favicon", "ico", 
    "path", "status", "text", "html", "redirect", "none", "findings", "error", 
    "elapsed", "request", "response", "content", "type", "header", "server",
    "well", "known", "file", "index", "main", "script", "style", "css", "png"
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
    
    for word in words:
        if not word.isalpha() or not (3 <= len(word) <= 8):
            return False
        if word in NOISE_WORDS:
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
    
    curve_order = int(
        "FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFE"
        "BAAEDCE6AF48A03BBFD25E8CD0364141",
        16
    )
    return 0 < value < curve_order

def _record_finding(findings, seen, secret, secret_type, offset, target_context="Target Response"):
    dedup_key = (secret_type, secret)
    if dedup_key in seen:
        return
    seen.add(dedup_key)
    
    findings.append({
        "type": secret_type,
        "secret_value": secret,
        "source": target_context,
        "offset": offset,
        "exposed": True,
    })
    
    terminal(
        f"\n{COLORS['RED']}{COLORS['BOLD']}[***] LIVE SECRET EXPOSURE HARVESTED [{secret_type}] [***]{COLORS['RESET']}"
    )
    terminal(f"  ├── Offset      : {offset}")
    terminal(f"  └── Raw Secret  : {COLORS['GREEN']}{secret}{COLORS['RESET']}")

    # STREAM TELEMETRY & PERSIST CRYPTOGRAPHIC LOOT TO DISK IMMEDIATELY
    stream_proof("CRYPTO_SECRET_HARVESTED", f"offset_{offset}", {"secret_type": secret_type}, secret[:12] + "...", {"exposed": True})
    save_session_loot(
        target=target_context,
        endpoint=f"crypto_offset_{offset}",
        finding_type=f"CRYPTO_HARVEST_{secret_type.replace(' ', '_').upper()}",
        status=200,
        headers={},
        body=secret,
        extra_loot={"secret_type": secret_type, "offset": offset, "raw_secret": secret}
    )

def harvest_private_keys(target_source_data="", target_context="https://cryptobytes.online"):
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
    
    # 1. EVM Private-Key Candidates
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
                match.start(),
                target_context
            )

    # 2. Bitcoin WIF Candidates
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
            match.start(),
            target_context
        )

    # 3. Mnemonic Seed Candidates (Filtered)
    word_pattern = re.compile(r"\b[a-zA-Z]{3,8}\b")
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
                window[0].start(),
                target_context
            )
            break

    terminal(
        f"\n{COLORS['GREEN']}[+] Cryptographic harvesting scan complete."
        f"{COLORS['RESET']}"
    )
    terminal(f"    Total Secrets Harvested : {len(findings)}")
    terminal(f"    Secured to Disk         : loot_output/")
    return findings

if __name__ == "__main__":
    if len(sys.argv) > 1:
        with open(sys.argv[1], "r", encoding="utf-8", errors="ignore") as f:
            harvest_private_keys(f.read(), sys.argv[1])
    else:
        print("Usage: python3 keyharvester.py <target_response_file>")
