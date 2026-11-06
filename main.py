#!/usr/bin/env python3
import asyncio
import sys
import socket
import time
import ipaddress
from urllib.parse import urlsplit
from modules.parser import parse_target_source
from modules.scanner import run_port_scanner
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
        BRUTEDOG V5.3 — LIVE SECURITY ASSESSMENT
        NETWORK RECONNAISSANCE / SOURCE INTELLIGENCE
════════════════════════════════════════════════════════════
{RESET}
"""
# ============================================================
# TERMINAL OUTPUT
# ============================================================
def log(message, color=GREEN):
    print(
        f"{color}{message}{RESET}",
        flush=True
    )
def section(title):
    print()
    log("=" * 65, NEON_BLUE)
    log(f" {title}", BOLD)
    log("=" * 65, NEON_BLUE)
def display_progress(message):
    print(
        f"{CYAN}[*] {message}{RESET}",
        flush=True
    )
# ============================================================
# TARGET VALIDATION
# ============================================================
ALLOWED_DOMAIN = "cryptobytes.online"
def normalize_target(raw_target):
    raw_target = raw_target.strip()
    if not raw_target:
        raise ValueError("Empty target.")
    if "://" not in raw_target:
        raw_target = "https://" + raw_target
    parsed = urlsplit(raw_target)
    if parsed.scheme not in ("http", "https"):
        raise ValueError("Only HTTP and HTTPS targets are supported.")
    if not parsed.hostname:
        raise ValueError("Invalid hostname.")
    hostname = parsed.hostname.encode(
        "idna"
    ).decode("ascii").lower()
    if not (
        hostname == ALLOWED_DOMAIN
        or hostname.endswith("." + ALLOWED_DOMAIN)
    ):
        raise ValueError(
            f"Target outside configured scope: {ALLOWED_DOMAIN}"
        )
    port = parsed.port or (
        443 if parsed.scheme == "https" else 80
    )
    if not 1 <= port <= 65535:
        raise ValueError("Invalid target port.")
    return {
        "hostname": hostname,
        "scheme": parsed.scheme,
        "port": port,
        "url": f"{parsed.scheme}://{hostname}:{port}"
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
            type=socket.SOCK_STREAM
        )
        addresses = sorted({
            result[4][0]
            for result in results
        })
        if not addresses:
            return False, []
        for address in addresses:
            ip = ipaddress.ip_address(address)
            if ip.is_unspecified:
                return False, []
        log(f"[DNS] Resolved addresses: {', '.join(addresses)}")
        return True, addresses
    except socket.gaierror as exc:
        log(f"[DNS ERROR] {exc}", RED)
        return False, []
# ============================================================
# PORT SCANNER DISPLAY
# ============================================================
def display_scanner_results(result):
    if not isinstance(result, dict):
        log(
            "[WARNING] Scanner returned an unexpected result.",
            YELLOW
        )
        return
    if result.get("status") != "COMPLETED":
        log(
            f"[SCANNER] {result.get('status')}",
            RED
        )
        return
    open_ports = result.get("open_ports", [])
    log(
        f"Ports tested: {result.get('ports_tested', 0)}"
    )
    log(
        f"Open ports: {result.get('open_count', 0)}"
    )
    log(
        f"Closed/unavailable ports: "
        f"{result.get('closed_count', 0)}"
    )
    if not open_ports:
        log("[RESULT] No open ports detected.", YELLOW)
        return
    section("OPEN SERVICE DISCOVERY")
    for item in open_ports:
        details = item.get("details", {})
        log(
            f"[OPEN] TCP/{item.get('port')}",
            GREEN
        )
        if isinstance(details, dict):
            if details.get("service"):
                print(
                    f"       Service: {details['service']}"
                )
            if details.get("banner"):
                print(
                    f"       Banner: {details['banner'][:150]}"
                )
            http_details = details.get("details", {})
            if isinstance(http_details, dict):
                if http_details.get("status_line"):
                    print(
                        f"       HTTP: {http_details['status_line']}"
                    )
                if http_details.get("server"):
                    print(
                        f"       Server: {http_details['server']}"
                    )
# ============================================================
# SOURCE INTELLIGENCE DISPLAY
# ============================================================
def display_parser_results(result):
    if not isinstance(result, dict):
        log(
            "[PARSER] Unexpected parser result.",
            RED
        )
        return
    summary = result.get("summary", {})
    section("SOURCE INTELLIGENCE RESULTS")
    print(
        f"Endpoints tested: "
        f"{summary.get('endpoints_tested', 0)}"
    )
    print(
        f"JavaScript discovered: "
        f"{summary.get('javascript_files_discovered', 0)}"
    )
    print(
        f"JavaScript tested: "
        f"{summary.get('javascript_files_tested', 0)}"
    )
    print(
        f"Exposed resources: "
        f"{summary.get('exposed_resources', 0)}"
    )
    print(
        f"Secret pattern matches: "
        f"{summary.get('secret_pattern_matches', 0)}"
    )
    findings = result.get("findings", [])
    if findings:
        section("DETECTED SECRET INDICATORS")
        for index, finding in enumerate(findings, 1):
            print(
                f"{YELLOW}[{index}] "
                f"{finding.get('type')}{RESET}"
            )
            print(
                f"    Source: {finding.get('source')}"
            )
            print(
                f"    Evidence: {finding.get('evidence')}"
            )
            print(
                f"    Validation: "
                f"{finding.get('validation')}"
            )
    else:
        log(
            "[RESULT] No secret-pattern matches detected.",
            YELLOW
        )
    exposed = result.get("exposed_resources", [])
    if exposed:
        section("HTTP-ACCESSIBLE RESOURCES")
        for item in exposed:
            print(
                f"[HTTP {item.get('status')}] "
                f"{item.get('path')} "
                f"({item.get('bytes')} bytes)"
            )
# ============================================================
# MAIN EXECUTION
# ============================================================
async def async_main():
    started = time.monotonic()
    scanner_result = None
    parser_result = None
    scanner_error = None
    parser_error = None
    print("\033[2J\033[H")
    print(BANNER)
    log("[SYSTEM] BruteDog initialized.")
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
    # --------------------------------------------------------
    # EXECUTION CONFIRMATION
    # --------------------------------------------------------
    confirmation = input(
        f"\n{YELLOW}"
        "Confirm you control this target. Type YES: "
        f"{RESET}"
    ).strip()
    if confirmation != "YES":
        log("[ABORT] Confirmation not received.", RED)
        return
    # --------------------------------------------------------
    # PHASE 1 — NETWORK RECONNAISSANCE
    # --------------------------------------------------------
    section("PHASE 1 — NETWORK RECONNAISSANCE")
    try:
        display_progress("Starting TCP port assessment.")
        scanner_result = await run_port_scanner(
            hostname
        )
        display_scanner_results(scanner_result)
    except Exception as exc:
        scanner_error = str(exc)
        log(
            f"[SCANNER ERROR] {scanner_error}",
            RED
        )
    # --------------------------------------------------------
    # PHASE 2 — SOURCE INTELLIGENCE
    # --------------------------------------------------------
    section("PHASE 2 — SOURCE INTELLIGENCE")
    try:
        display_progress(
            "Starting endpoint and source exposure assessment."
        )
        parser_result = await parse_target_source(
            hostname
        )
        display_parser_results(parser_result)
    except Exception as exc:
        parser_error = str(exc)
        log(
            f"[PARSER ERROR] {parser_error}",
            RED
        )
    # --------------------------------------------------------
    # FINAL SUMMARY
    # --------------------------------------------------------
    elapsed = time.monotonic() - started
    section("FINAL EXECUTION SUMMARY")
    print(f"Target: {target['url']}")
    print(
        f"Scanner: "
        f"{'COMPLETED' if scanner_result else 'FAILED'}"
    )
    print(
        f"Parser: "
        f"{'COMPLETED' if parser_result else 'FAILED'}"
    )
    print(
        f"Execution time: {elapsed:.2f} seconds"
    )
    if scanner_error:
        print(f"Scanner error: {scanner_error}")
    if parser_error:
        print(f"Parser error: {parser_error}")
    log(
        "LIVE ASSESSMENT FINISHED",
        MATRIX_GREEN
    )
    log(
        "Results displayed in terminal memory only.",
        NEON_BLUE
    )
    log(
        "No main.py report files created.",
        NEON_BLUE
    )
# ============================================================
# ENTRY POINT
# ============================================================
def main():
    try:
        asyncio.run(async_main())
    except KeyboardInterrupt:
        log(
            "\n[INTERRUPTED] Assessment stopped by operator.",
            YELLOW
        )
    except Exception as exc:
        log(
            f"\n[FATAL ERROR] {exc}",
            RED
        )
if __name__ == "__main__":
    main()