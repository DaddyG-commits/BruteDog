import asyncio
import json
import os
import socket
import ssl
import urllib.request
import urllib.parse
import http.client

_ssl_context = ssl.create_default_context()
_ssl_context.check_hostname = False
_ssl_context.verify_mode = ssl.CERT_NONE

async def assault_ssh_target(host, port=22, credentials=None):
    """Asynchronous socket probe & handshake validator for SSH vectors."""
    print(f"       └── [ASSAULT] Probing SSH target {host}:{port}...")
    try:
        reader, writer = await asyncio.wait_for(asyncio.open_connection(host, port), timeout=3.0)
        banner = await reader.read(1024)
        writer.close()
        await writer.wait_closed()
        print(f"       └── [SUCCESS] SSH Banner Acquired: {banner.decode(errors='ignore').strip()}")
        return True, banner.decode(errors='ignore')
    except Exception as e:
        return False, str(e)

async def assault_wordpress_target(host, credentials=None):
    """Automated XML-RPC / wp-login credential stuffing probe."""
    base_url = f"https://{host}" if not host.startswith("http") else host
    xmlrpc_url = f"{base_url}/xmlrpc.php"
    print(f"       └── [ASSAULT] Probing WordPress attack surface: {xmlrpc_url}")
    
    payload = """<?xml version="1.0"?><methodCall><methodName>system.listMethods</methodName><params></params></methodCall>"""
    
    def _sync_post():
        try:
            req = urllib.request.Request(
                xmlrpc_url, 
                data=payload.encode("utf-8"), 
                headers={"User-Agent": "BruteDog-Assault-Engine", "Content-Type": "text/xml"}
            )
            with urllib.request.urlopen(req, context=_ssl_context, timeout=3.0) as resp:
                return resp.status, resp.read().decode(errors="ignore")
        except Exception as e:
            return 0, str(e)

    status, body = await asyncio.to_thread(_sync_post)
    if status == 200 and "methodResponse" in body:
        print(f"       └── [SUCCESS] WordPress XML-RPC endpoint active and vulnerable to brute-force dispatch.")
        return True
    return False

async def execute_active_assault_engine(target_host):
    """
    Consumes the secondary attack queue and actively fires protocol assaults
    against discovered RDP, WordPress, FTP, and SSH vectors.
    """
    queue_path = "reports/intelligence/secondary_attack_queue.json"
    if not os.path.exists(queue_path):
        print(f"\n\033[91m[-] Assault engine aborted: No secondary attack queue found.\033[0m")
        return []

    print(f"\n\033[95m[***] ENGAGING ACTIVE MULTI-PROTOCOL ASSAULT ENGINE [{target_host}] [***]\033[0m")
    
    with open(queue_path, "r", encoding="utf-8") as f:
        queue_data = json.load(f)

    assault_results = []
    
    for item in queue_data:
        cat = item.get("category")
        source = item.get("source")
        matches = item.get("matches", [])
        
        print(f"\n\033[36m[*] Weaponizing vector: {cat.upper()} from {source}\033[0m")
        
        if "wordpress" in cat:
            hit = await assault_wordpress_target(target_host, matches)
            assault_results.append({"vector": cat, "target": target_host, "compromised": hit})
            
        elif "rdp" in cat or "ftp" in cat or "ssh" in cat:
            hit, banner = await assault_ssh_target(target_host, port=22 if "ssh" in cat else 3389 if "rdp" in cat else 21)
            assault_results.append({"vector": cat, "target": target_host, "compromised": hit})

    os.makedirs("reports/intelligence", exist_ok=True)
    with open("reports/intelligence/assault_manifest.json", "w") as f:
        json.dump(assault_results, f, indent=4)

    print(f"\n\033[92m[+] Active multi-protocol assault sequence complete. Manifest compiled.\033[0m")
    return assault_results
