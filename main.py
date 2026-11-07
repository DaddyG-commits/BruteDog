#!/usr/bin/env python3
"""
BRUTEDOG V6.3 — LIVE SECURITY ASSESSMENT & RED-TEAM ORCHESTRATION ENGINE
Main Orchestrator:
- Pre-flight DNS and target scope validation
- Network reconnaissance & port scanning
- Source intelligence & credential exposure parsing
- Autonomous multi-protocol brute-forcing, cloud pivoting, and replaying
- High-concurrency race condition and logic fuzzing integration
- Live terminal streaming with zero-disk memory persistence
"""
import asyncio
import sys
import socket
import time
import ipaddress
from urllib.parse import urlsplit

# Import framework modules
from modules.db_assault import run_nosql_assault
from modules.session_hijack import run_session_hijack
from modules.race_condition import run_race_condition_test
from modules.drainer import run_drainer_engine
from modules.parser import parse_target_source
from modules.scanner import run_port_scanner
from modules.engine import run_autonomous_engine
from modules.replayer import replay_and_inject_payloads
from modules.bruter import execute_active_assault_engine
from modules.cloud_apex import run_cloud_apex
from modules.pivot import run_pivot_engine
from modules.dumper import harvest_email_intelligence
from modules.keyharvester import harvest_private_keys
from modules.stealth_ops import run_stealth_engine

# ============================================================
# TERMINAL COLORS
# ============================================================
CYAN = "\033[96m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
RESET = "\033[0m"
BOLD = "\033[1m"
MATRIX_GREEN = "\033[38;5;46m"
NEON_BLUE = "\033[38;5;51m"

# ============================================================
# BANNER
# ============================================================
BANNER = f"""{MATRIX_GREEN}{BOLD}
 ██████╗ ██████╗ ██╗   ██╗████████╗███████╗██████╗
 ██╔══██╗██╔══██╗██║   ██║╚══██╔══╝██╔════╝██╔══██╗
 ██████╔╝██████╔╝██║   ██║   ██║   █████╗  ██║  ██║
 ██╔══██╗██╔══██╗██║   ██║   ██║   ██╔══╝  ██║  ██║
 ██████╔╝██║  ██║╚██████╔╝   ██║   ███████╗██████╔╝
{RESET}{NEON_BLUE}
════════════════════════════════════════════════════════════
        BRUTEDOG V6.3 — STATEFUL RED-TEAM ORCHESTRATION
        AUTONOMOUS OFFENSIVE ENGINE / LIVE TELEMETRY STREAMING
════════════════════════════════════════════════════════════
{RESET}
"""

# ============================================================
# TERMINAL OUTPUT
# ============================================================
def log(message, color=GREEN):
    print(f"{color}{message}{RESET}", flush=True)

def section(title):
    print()
    log("=" * 65, NEON_BLUE)
    log(f" {title}", BOLD)
    log("=" * 65, NEON_BLUE)

def display_progress(message):
    print(f"{CYAN}[*] {message}{RESET}", flush=True)

# ============================================================
# TARGET VALIDATION
# ============================================================
def normalize_target(raw_target):
    raw_target = raw_target.strip()
    if not raw_target:
        raise ValueError("Empty target.")
    if "://" not in raw_target:
        raw_target = "https://" + raw_target
    parsed = urlsplit(raw_target)
    if parsed.scheme not in ("http", "https"):
        raise ValueError(
            "Only HTTP and HTTPS targets are supported."
        )
    if not parsed.hostname:
        raise ValueError("Invalid hostname.")
    if parsed.username or parsed.password:
        raise ValueError(
            "Embedded target credentials are not accepted."
        )
    hostname = parsed.hostname.encode(
        "idna"
    ).decode("ascii").lower()
    
    if not hostname:
        raise ValueError("Invalid target hostname.")
        
    try:
        port = parsed.port or (
            443 if parsed.scheme == "https" else 80
        )
    except ValueError:
        raise ValueError("Invalid target port.")
    if not 1 <= port <= 65535:
        raise ValueError("Invalid target port.")
    return {
        "hostname": hostname,
        "scheme": parsed.scheme,
        "port": port,
        "url": f"{parsed.scheme}://{hostname}:{port}",
    }

# ============================================================
# DNS VALIDATION
# ============================================================
def validate_target_host(host):
    display_progress(f"Resolving target: {host}")
    try:
        results = socket.getaddrinfo(
            host,
            None,
            family=socket.AF_UNSPEC,
            type=socket.SOCK_STREAM,
        )
        addresses = sorted({
            result[4][0]
            for result in results
        })
        if not addresses:
            return False, []
        for address in addresses:
            ip = ipaddress.ip_address(address)
            if (
                ip.is_unspecified
                or ip.is_multicast
                or ip.is_loopback
                or ip.is_link_local
            ):
                log(
                    f"[DNS WARNING] Unusable address detected: {ip}",
                    RED,
                )
                return False, []
        log(
            f"[DNS] Resolved addresses: {', '.join(addresses)}"
        )
        return True, addresses
    except socket.gaierror as exc:
        log(f"[DNS ERROR] {exc}", RED)
        return False, []

# ============================================================
# DISPLAY HELPERS FOR MODULE RESULTS
# ============================================================
def display_scanner_results(result):
    if not isinstance(result, dict):
        log("[WARNING] Scanner returned unexpected result.", YELLOW)
        return
    open_ports = result.get("open_ports", [])
    log(f"Open ports detected: {len(open_ports)}")
    for item in open_ports:
        log(f"[OPEN] TCP/{item.get('port')}", GREEN)

def display_parser_results(result):
    if not isinstance(result, dict):
        return
    section("SOURCE INTELLIGENCE & EXPOSURE RESULTS")
    findings = result.get("findings", [])
    log(f"Findings detected: {len(findings)}")

# ============================================================
# MAIN EXECUTION ORCHESTRATION
# ============================================================
async def async_main():
    started = time.monotonic()
    print("\033[2J\033[H")
    print(BANNER)
    log("[SYSTEM] BruteDog Active Orchestrator Initialized (v6.3).")

    # --------------------------------------------------------
    # TARGET INPUT
    # --------------------------------------------------------
    raw_target = input(
        f"{MATRIX_GREEN}{BOLD}"
        "[TARGET] Enter your domain: "
        f"{RESET}"
    ).strip()
    try:
        target = normalize_target(raw_target)
    except ValueError as exc:
        log(f"[ABORT] {exc}", RED)
        return

    hostname = target["hostname"]
    section("PRE-FLIGHT VALIDATION")
    valid, addresses = validate_target_host(hostname)
    if not valid:
        log("[ABORT] DNS validation failed.", RED)
        return

    log(f"Target: {target['url']}")
    log(f"Hostname: {hostname}")
    log(f"Port: {target['port']}")
    log(f"Protocol: {target['scheme'].upper()}")

    # --------------------------------------------------------
    # EXECUTION CONFIRMATION
    # --------------------------------------------------------
    confirmation = input(
        f"\n{YELLOW}"
        "Confirm authorization and operational intent. Type YES: "
        f"{RESET}"
    ).strip()
    if confirmation != "YES":
        log("[ABORT] Confirmation not received.", RED)
        return

    # --------------------------------------------------------
    # PHASE 1 — NETWORK RECONNAISSANCE & STEALTH PROBING
    # --------------------------------------------------------
    section("PHASE 1 — NETWORK RECON & STEALTH OPS")
    try:
        display_progress("Executing stealth operations and security control assessment.")
        await run_stealth_engine(target["url"])
        
        display_progress("Starting TCP port assessment.")
        scanner_result = await run_port_scanner(hostname)
        display_scanner_results(scanner_result)
    except Exception as exc:
        log(f"[RECON ERROR] {exc}", RED)

    # --------------------------------------------------------
    # PHASE 2 — SOURCE INTELLIGENCE & KEY HARVESTING
    # --------------------------------------------------------
    section("PHASE 2 — SOURCE INTELLIGENCE & CRYPTO HARVESTING")
    try:
        display_progress("Parsing target source and extracting exposure indicators.")
        parser_result = await asyncio.to_thread(parse_target_source, target["url"])
        display_parser_results(parser_result)

        response_blob = str(parser_result)
        harvest_private_keys(response_blob)
    except Exception as exc:
        log(f"[PARSER ERROR] {exc}", RED)

    # --------------------------------------------------------
    # PHASE 3 — STATEFUL CRAWLING, AUTH STUFFING & REPLAY
    # --------------------------------------------------------
    section("PHASE 3 — STATEFUL CRAWL, AUTH STUFFING & REPLAYER")
    try:
        display_progress("Executing stateful crawler, autonomous operator provisioning, and live telemetry engine.")
        await run_autonomous_engine(target_host=target["url"])

        display_progress("Replaying secondary attack queue & executing session token fabrication.")
        await replay_and_inject_payloads(target["url"])
    except Exception as exc:
        log(f"[ENGINE ERROR] {exc}", RED)

    # --------------------------------------------------------
    # PHASE 3.5 — AGGRESSIVE DB ASSAULT, SESSION HIJACKING & RACE CONDITIONS
    # --------------------------------------------------------
    section("PHASE 3.5 — AGGRESSIVE DB ASSAULT, SESSION HIJACKING & CONCURRENCY")
    try:
        display_progress("Executing time-based blind SQLi and NoSQL operator injection.")
        await run_nosql_assault(target["url"], port=target["port"], use_ssl=(target["scheme"] == "https"))

        display_progress("Executing JWT secret cracking and cookie privilege escalation fuzzing.")
        await run_session_hijack(target["url"], port=target["port"], use_ssl=(target["scheme"] == "https"))

        display_progress("Firing high-concurrency race condition threads against transaction endpoints.")
        await run_race_condition_test(target["url"], port=target["port"], use_ssl=(target["scheme"] == "https"))
    except Exception as exc:
        log(f"[EXPLOIT/CONCURRENCY ERROR] {exc}", RED)

    # --------------------------------------------------------
    # PHASE 4 — MULTI-PROTOCOL BRUTE-FORCE & MAILBOX EXPLOITATION
    # --------------------------------------------------------
    section("PHASE 4 — MULTI-PROTOCOL & MAILBOX EXPLOITATION")
    try:
        display_progress("Launching multi-protocol brute-force (SSH, FTP, RDP, XML-RPC).")
        await execute_active_assault_engine(target["url"])

        display_progress("Launching active IMAP mailbox brute-force and credential harvesting.")
        await harvest_email_intelligence(hostname)
    except Exception as exc:
        log(f"[BRUTE ERROR] {exc}", RED)

    # --------------------------------------------------------
    # PHASE 5 — CLOUD INFRASTRUCTURE PIVOT & LIQUIDITY AUDIT
    # --------------------------------------------------------
    section("PHASE 5 — CLOUD INFRASTRUCTURE & LIQUIDITY AUDIT")
    try:
        display_progress("Executing cloud control plane pivot and IMDS metadata exfiltration.")
        await run_cloud_apex(target["url"])

        display_progress("Running autonomous pivot engine and covert exfiltration preparation.")
        await run_pivot_engine(target["url"])

        display_progress("Executing active multi-chain liquidity audit & sweep routing.")
        await run_drainer_engine(target["url"])
    except Exception as exc:
        log(f"[DRAINER/CLOUD ERROR] {exc}", RED)

    # --------------------------------------------------------
    # FINAL SUMMARY
    # --------------------------------------------------------
    elapsed = time.monotonic() - started
    section("FINAL EXECUTION SUMMARY")
    print(f"Target: {target['url']}")
    print(f"Execution time: {elapsed:.2f} seconds")
    log("LIVE RED-TEAM ATTACK FINISHED", MATRIX_GREEN)
    log("All intelligence and telemetry streamed live on-screen.", NEON_BLUE)
    log("Zero report files written to disk.", NEON_BLUE)

# ============================================================
# ENTRY POINT
# ============================================================
def main():
    try:
        asyncio.run(async_main())
    except KeyboardInterrupt:
        log("\n[INTERRUPTED] Assessment stopped by operator.", YELLOW)
    except Exception as exc:
        log(f"\n[FATAL ERROR] {exc}", RED)

if __name__ == "__main__":
    main()

