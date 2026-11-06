import sys

def send_breach_alert(target, hit_details):
    """
    Zero-Network Terminal Interceptor & Artifact Streamer:
    - Eliminates external SMTP transmissions.
    - Streams breach telemetry, recovered emails, and private keys instantly in high-contrast plain text to stdout.
    """
    sys.stdout.write(f"\n\033[1m\033[91m[***] LIVE BREACH & ARTIFACT ALERT INTERCEPTED [***]\033[0m\n")
    sys.stdout.write(f"  ├── Target Domain   : {target}\n")
    sys.stdout.write(f"  ├── Vector Type     : \033[92m{hit_details.get('type', 'N/A')}\033[0m\n")
    sys.stdout.write(f"  ├── Endpoint        : \033[92m{hit_details.get('endpoint', 'N/A')}\033[0m\n")
    sys.stdout.write(f"  ├── Target Port     : {hit_details.get('port', 'N/A')}\n")
    sys.stdout.write(f"  ├── Username        : \033[92m{hit_details.get('user', 'N/A')}\033[0m\n")
    sys.stdout.write(f"  ├── Password/Key    : \033[91m{hit_details.get('password', 'N/A')}\033[0m\n")
    
    # Explicitly stream harvested email & private key data if present
    harvested_email = hit_details.get('email', hit_details.get('harvested_email', 'N/A'))
    private_key = hit_details.get('private_key', hit_details.get('key_content', 'N/A'))
    
    sys.stdout.write(f"  ├── Harvested Email : \033[96m{harvested_email}\033[0m\n")
    sys.stdout.write(f"  ├── Private Key/Seed: \033[93m{private_key}\033[0m\n")
    sys.stdout.write(f"  ├── Status Code     : {hit_details.get('status', 'N/A')}\n")
    sys.stdout.write(f"  └── Timestamp       : {hit_details.get('timestamp', 'N/A')}\n")
    sys.stdout.flush()

    return True, "Alert and artifacts streamed live to terminal."
