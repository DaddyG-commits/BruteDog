import sys

def is_valid_bip39_seed(text):
    """Validation placeholder (inactive for local storage)."""
    return False

def is_valid_evm_key(key_str):
    """Validation placeholder (inactive for local storage)."""
    return False

def harvest_private_keys(root_dir="."):
    """
    Zero-Local-Storage Cryptographic Scraper:
    - Completely disables local filesystem traversal, workspace sweeps, and local key/seed scraping.
    - Protects local storage by refusing to inspect or harvest local files.
    """
    sys.stdout.write(f"\n\033[95m[***] LOCAL CRYPTOGRAPHIC ARTIFACT SCRAPER BYPASSED (STORAGE PROTECTED) [***]\033[0m\n")
    sys.stdout.write(f"  └── Status : \033[92mLocal storage scanning disabled. Zero local keys or seed phrases accessed.\033[0m\n\n")
    sys.stdout.flush()
    
    # Return an empty list so no local keys or seeds are processed, drained, or exposed
    return []

