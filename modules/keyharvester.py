import os
import re
import json
import time

def harvest_private_keys(target_dir="."):
    """
    Advanced multi-asset harvester: Scans the target environment for cryptographic 
    private keys, WIF formats, Solana base58 keys, XRP secrets, and BIP39 seed phrases.
    """
    print(f"\n\033[95m[***] DEPLOYING MULTI-ASSET PRIVATE KEY & SEED HARVESTER [***]\033[0m")
    
    key_patterns = {
        "RSA Private Key": r"-----BEGIN RSA PRIVATE KEY-----[\s\S]*?-----END RSA PRIVATE KEY-----",
        "OpenSSH Private Key": r"-----BEGIN OPENSSH PRIVATE KEY-----[\s\S]*?-----END OPENSSH PRIVATE KEY-----",
        "EC Private Key": r"-----BEGIN EC PRIVATE KEY-----[\s\S]*?-----END EC PRIVATE KEY-----",
        "Generic Private Key": r"-----BEGIN PRIVATE KEY-----[\s\S]*?-----END PRIVATE KEY-----",
        "EVM Hex Private Key": r"\b0x[a-fA-F0-9]{64}\b",
        "Bitcoin/Litecoin WIF": r"\b[5KL][1-9A-HJ-NP-Za-km-z]{50,51}\b",
        "Solana Base58 Key": r"\b[1-9A-HJ-NP-Za-km-z]{87,88}\b",
        "XRP Secret Key": r"\bs[1-9A-HJ-NP-Za-km-z]{28,30}\b",
        "BIP39 Seed Phrase (12/24 Word)": r"\b([a-z]{3,8}\s){11,23}[a-z]{3,8}\b"
    }

    harvested_keys = []

    # Walk directory tree for key files or text containing credentials
    for root, dirs, files in os.walk(target_dir):
        if any(skip in root for skip in ["reports", ".git", "node_modules", "__pycache__"]):
            continue
        for file in files:
            file_path = os.path.join(root, file)
            try:
                with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read()
                    
                for key_type, pattern in key_patterns.items():
                    matches = re.findall(pattern, content)
                    for match in matches:
                        # Normalize regex group tuples if matched via bip39 phrase capture
                        key_val = match[0] if isinstance(match, tuple) else match
                        
                        print(f"\n\033[91m[!] PLAINTEXT ASSET FOUND [{key_type}] in {file_path}:\033[0m")
                        print(f"\033[33m{key_val}\033[0m\n")
                        
                        harvested_keys.append({
                            "type": key_type,
                            "source_file": file_path,
                            "key_content": key_val,
                            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
                        })
            except Exception:
                continue

    if harvested_keys:
        os.makedirs("reports/keys", exist_ok=True)
        report_path = "reports/keys/harvested_private_keys.json"
        with open(report_path, "w") as f:
            json.dump(harvested_keys, f, indent=4)
        print(f" \033[92m[+] Serialized {len(harvested_keys)} keys/seeds to {report_path}\033[0m")
    else:
        print(f" \033[90m[-] No actionable keys exposed in current scan scope.\033[0m")
    
    return harvested_keys
