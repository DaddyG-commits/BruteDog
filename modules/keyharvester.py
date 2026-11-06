import re
import sys

def is_valid_bip39_seed(text):
    words = text.strip().lower().split()
    if len(words) not in [12, 24]:
        return False
    for w in words:
        if not w.isalpha() or len(w) < 3 or len(w) > 8:
            return False
    code_indicators = ["import", "def", "class", "return", "self", "setup", "sys", "from", "http", "git", "file", "print"]
    if any(ind in words for ind in code_indicators):
        return False
    return True

def is_valid_evm_key(key_str):
    clean = key_str[2:] if key_str.startswith("0x") else key_str
    if len(clean) != 64:
        return False
    try:
        int(clean, 16)
        if clean == "0" * 64 or "test" in clean.lower():
            return False
        return True
    except ValueError:
        return False

def harvest_private_keys(target_source_data=""):
    """
    Remote-Target Cryptographic Artifact Scraper:
    - Scans remote target responses, source code, or endpoint payloads for keys and seed phrases.
    - Zero local filesystem access.
    """
    sys.stdout.write(f"\n\033[95m[***] ENGAGING REMOTE TARGET CRYPTOGRAPHIC ARTIFACT SCRAPER [***]\033[0m\n")
    sys.stdout.flush()
    
    harvested_artifacts = []
    hex_key_pattern = re.compile(r'\b(?:0x)?[a-fA-F0-9]{64}\b')
    btc_wif_pattern = re.compile(r'\b[5KL][1-9A-HJ-NP-Za-km-z]{50,51}\b')
    
    if not target_source_data:
        sys.stdout.write(f"  └── Status : \033[36mNo target payload supplied for remote key parsing.\033[0m\n\n")
        sys.stdout.flush()
        return harvested_artifacts

    content = str(target_source_data)

    # 1. Scan for EVM Private Keys
    for match in hex_key_pattern.findall(content):
        if is_valid_evm_key(match):
            full_key = match if match.startswith("0x") else "0x" + match
            artifact = {"type": "Hex Private Key (EVM)", "key_content": full_key, "source": "Remote Target"}
            if artifact not in harvested_artifacts:
                harvested_artifacts.append(artifact)
                sys.stdout.write(f"\n\033[1m\033[91m[***] LIVE REMOTE EVM KEY EXPOSED [***]\033[0m\n")
                sys.stdout.write(f"  └── Key : \033[92m{full_key}\033[0m\n")
                sys.stdout.flush()
                
    # 2. Scan for Bitcoin WIF Keys
    for match in btc_wif_pattern.findall(content):
        artifact = {"type": "Bitcoin WIF Key", "key_content": match, "source": "Remote Target"}
        if artifact not in harvested_artifacts:
            harvested_artifacts.append(artifact)
            sys.stdout.write(f"\n\033[1m\033[91m[***] LIVE REMOTE BTC WIF EXPOSED [***]\033[0m\n")
            sys.stdout.write(f"  └── WIF : \033[92m{match}\033[0m\n")
            sys.stdout.flush()

    # 3. Scan for True BIP39 Seed Phrases
    words = content.split()
    if len(words) >= 12:
        for i in range(len(words) - 11):
            chunk = " ".join(words[i:i+12])
            if is_valid_bip39_seed(chunk):
                artifact = {"type": "BIP39 Seed Phrase", "key_content": chunk, "source": "Remote Target"}
                if artifact not in harvested_artifacts:
                    harvested_artifacts.append(artifact)
                    sys.stdout.write(f"\n\033[1m\033[91m[***] LIVE REMOTE SEED PHRASE EXPOSED [***]\033[0m\n")
                    sys.stdout.write(f"  └── Phrase : \033[93m{chunk}\033[0m\n")
                    sys.stdout.flush()
                    break

    sys.stdout.write(f" \033[36m[*] Remote target artifact scan complete. Verified remote keys: {len(harvested_artifacts)}\033[0m\n\n")
    sys.stdout.flush()
    return harvested_artifacts
