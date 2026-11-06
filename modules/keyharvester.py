import os
import re
import json
import time

def harvest_private_keys(target_dir="."):
    """
    Scans the environment for cryptographic private keys, SSH keys, 
    and wallet keys, displaying them in plaintext and saving reports.
    """
    print(f"\n\033[95m[***] DEPLOYING PRIVATE KEY & ASSET HARVESTER [***]\033[0m")
    
    key_patterns = {
        "RSA Private Key": r"-----BEGIN RSA PRIVATE KEY-----[\s\S]*?-----END RSA PRIVATE KEY-----",
        "OpenSSH Private Key": r"-----BEGIN OPENSSH PRIVATE KEY-----[\s\S]*?-----END OPENSSH PRIVATE KEY-----",
        "EC Private Key": r"-----BEGIN EC PRIVATE KEY-----[\s\S]*?-----END EC PRIVATE KEY-----",
        "Generic Private Key": r"-----BEGIN PRIVATE KEY-----[\s\S]*?-----END PRIVATE KEY-----",
        "Crypto Hex Private Key": r"\b0x[a-fA-F0-9]{64}\b"
    }

    harvested_keys = []

    # Walk directory tree for key files or text containing keys
    for root, dirs, files in os.walk(target_dir):
        # Skip heavy system or report folders
        if "reports" in root or ".git" in root:
            continue
        for file in files:
            file_path = os.path.join(root, file)
            try:
                with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read()
                    
                for key_type, pattern in key_patterns.items():
                    matches = re.findall(pattern, content)
                    for match in matches:
                        print(f"\n\033[91m[!] PLAINTEXT PRIVATE KEY FOUND [{key_type}] in {file_path}:\033[0m")
                        print(f"\033[33m{match}\033[0m\n")
                        
                        harvested_keys.append({
                            "type": key_type,
                            "source_file": file_path,
                            "key_content": match,
                            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
                        })
            except Exception:
                continue

    if harvested_keys:
        os.makedirs("reports/keys", exist_ok=True)
        report_path = "reports/keys/harvested_private_keys.json"
        with open(report_path, "w") as f:
            json.dump(harvested_keys, f, indent=4)
        print(f" \033[92m[+] Serialized {len(harvested_keys)} private keys to {report_path}\033[0m")
    else:
        print(f" \033[90m[-] No private keys exposed in current directory scan scope.\033[0m")
    
    return harvested_keys
