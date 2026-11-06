#!/usr/bin/env python3
import asyncio
import socket
import ssl
import time
import http.client
from urllib.parse import urlsplit
# ============================================================
# CONFIGURATION
# ============================================================
CONNECT_TIMEOUT = 2.0
MAX_CONCURRENT = 40
COMMON_PORTS = [
    20, 21, 22, 23, 25, 26, 53, 67, 68,
    80, 81, 82, 88, 110, 111, 123, 135,
    137, 138, 139, 143, 161, 162, 179,
    194, 389, 443, 445, 465, 500, 502,
    514, 515, 587, 593, 623, 631, 636,
    873, 902, 989, 990, 993, 995, 1080,
    1194, 1433, 1521, 1701, 1723, 1883,
    2049, 2082, 2083, 2086, 2087, 2181,
    2375, 2376, 3000, 3306, 3389, 3690,
    4443, 5000, 5432, 5601, 5672, 5900,
    5985, 5986, 6379, 6443, 7001, 8000,
    8008, 8080, 8081, 8088, 8443, 8888,
    9000, 9090, 9200, 9300, 9418, 10000,
    11211, 27017
]
COLORS = {
    "RED": "\033[91m",
    "GREEN": "\033[92m",
    "YELLOW": "\033[93m",
    "CYAN": "\033[96m",
    "MAGENTA": "\033[95m",
    "RESET": "\033[0m",
}
# ============================================================
# TERMINAL OUTPUT
# ============================================================
def terminal(message):
    print(message, flush=True)
# ============================================================
# TARGET NORMALIZATION
# ============================================================
def normalize_host(target):
    if not isinstance(target, str) or not target.strip():
        raise ValueError("Invalid target.")
    target = target.strip()
    if "://" in target:
        parsed = urlsplit(target)
        if parsed.scheme not in ("http", "https"):
            raise ValueError("Unsupported URL scheme.")
        if not parsed.hostname:
            raise ValueError("Invalid hostname.")
        if parsed.username or parsed.password:
            raise ValueError("Embedded credentials are not accepted.")
        return parsed.hostname
    if "/" in target:
        raise ValueError("Expected a hostname, not a URL path.")
    return target
# ============================================================
# SERVICE IDENTIFICATION
# ============================================================
SERVICE_MAP = {
    20: "FTP-DATA",
    21: "FTP",
    22: "SSH",
    23: "TELNET",
    25: "SMTP",
    53: "DNS",
    80: "HTTP",
    110: "POP3",
    143: "IMAP",
    443: "HTTPS",
    445: "SMB",
    465: "SMTPS",
    587: "SMTP-SUBMISSION",
    993: "IMAPS",
    995: "POP3S",
    1433: "MSSQL",
    1521: "ORACLE",
    2049: "NFS",
    3306: "MYSQL",
    3389: "RDP",
    5432: "POSTGRESQL",
    5900: "VNC",
    6379: "REDIS",
    8080: "HTTP-ALT",
    8443: "HTTPS-ALT",
    9200: "ELASTICSEARCH",
    27017: "MONGODB",
}
# ============================================================
# BASIC BANNER IDENTIFICATION
# ============================================================
def read_banner(sock):
    try:
        sock.settimeout(0.8)
        data = sock.recv(512)
        if not data:
            return ""
        return data.decode(
            "utf-8",
            errors="replace"
        ).strip()
    except (socket.timeout, OSError):
        return ""
# ============================================================
# HTTP / HTTPS INSPECTION
# ============================================================
def inspect_http(host, port, use_ssl):
    conn = None
    try:
        if use_ssl:
            context = ssl.create_default_context()
            conn = http.client.HTTPSConnection(
                host,
                port,
                context=context,
                timeout=CONNECT_TIMEOUT
            )
        else:
            conn = http.client.HTTPConnection(
                host,
                port,
                timeout=CONNECT_TIMEOUT
            )
        conn.request(
            "HEAD",
            "/",
            headers={
                "Host": host,
                "User-Agent": "BruteDog-Security-Scanner/5.3",
                "Connection": "close",
            }
        )
        response = conn.getresponse()
        status_line = (
            f"HTTP/{response.version / 10:.1f} "
            f"{response.status} {response.reason}"
        )
        server = response.getheader("Server", "")
        return {
            "status_line": status_line,
            "server": server,
        }
    except ssl.SSLCertVerificationError:
        return {
            "status_line": "TLS certificate verification failed",
            "server": "",
        }
    except Exception as exc:
        return {
            "status_line": f"HTTP inspection unavailable: {type(exc).__name__}",
            "server": "",
        }
    finally:
        if conn:
            try:
                conn.close()
            except Exception:
                pass
# ============================================================
# SINGLE TCP PORT PROBE
# ============================================================
def probe_port(host, port):
    result = {
        "port": port,
        "open": False,
        "details": {
            "service": SERVICE_MAP.get(port, "UNKNOWN"),
            "banner": "",
            "details": {},
        },
    }
    sock = None
    try:
        sock = socket.create_connection(
            (host, port),
            timeout=CONNECT_TIMEOUT
        )
        result["open"] = True
        service = SERVICE_MAP.get(port, "UNKNOWN")
        banner = ""
        if port not in (80, 443, 8080, 8443):
            banner = read_banner(sock)
        result["details"]["banner"] = banner[:200]
        if port in (80, 8080):
            result["details"]["details"] = inspect_http(
                host,
                port,
                False
            )
        elif port in (443, 8443):
            result["details"]["details"] = inspect_http(
                host,
                port,
                True
            )
        return result
    except (socket.timeout, ConnectionRefusedError, OSError):
        return result
    finally:
        if sock:
            try:
                sock.close()
            except Exception:
                pass
# ============================================================
# ASYNC SCANNER
# ============================================================
async def run_port_scanner(target_host, ports=None):
    """
    Live TCP port scanner.
    Compatible with:
        result = await run_port_scanner(hostname)
    Returns:
        {
            status,
            target,
            ports_tested,
            open_count,
            closed_count,
            open_ports,
            duration
        }
    No report files are created.
    """
    started = time.monotonic()
    try:
        host = normalize_host(target_host)
    except ValueError as exc:
        terminal(
            f"{COLORS['RED']}[-] {exc}{COLORS['RESET']}"
        )
        return {
            "status": "FAILED",
            "error": str(exc),
            "open_ports": [],
        }
    if ports is None:
        ports = COMMON_PORTS
    ports = sorted(set(int(port) for port in ports))
    if not ports or any(port < 1 or port > 65535 for port in ports):
        return {
            "status": "FAILED",
            "error": "Invalid port list.",
            "open_ports": [],
        }
    terminal(
        f"\n{COLORS['MAGENTA']}"
        f"[***] BRUTEDOG LIVE TCP SCANNER [***]"
        f"{COLORS['RESET']}"
    )
    terminal(
        f"{COLORS['CYAN']}[*] Target: {host}"
        f"{COLORS['RESET']}"
    )
    terminal(
        f"[*] Ports scheduled: {len(ports)}"
    )
    terminal(
        f"[*] Maximum concurrency: {MAX_CONCURRENT}"
    )
    semaphore = asyncio.Semaphore(MAX_CONCURRENT)
    open_ports = []
    completed = 0
    async def scan_one(port):
        nonlocal completed
        async with semaphore:
            result = await asyncio.to_thread(
                probe_port,
                host,
                port
            )
            completed += 1
            if result["open"]:
                open_ports.append(result)
                service = result["details"]["service"]
                terminal(
                    f"{COLORS['GREEN']}"
                    f"[OPEN] TCP/{port} — {service}"
                    f"{COLORS['RESET']}"
                )
            elif completed % 15 == 0:
                terminal(
                    f"{COLORS['CYAN']}"
                    f"[*] Progress: {completed}/{len(ports)}"
                    f"{COLORS['RESET']}"
                )
            return result
    try:
        await asyncio.gather(
            *(scan_one(port) for port in ports)
        )
    except Exception as exc:
        terminal(
            f"{COLORS['RED']}[-] Scanner error: {exc}"
            f"{COLORS['RESET']}"
        )
        return {
            "status": "FAILED",
            "target": host,
            "error": str(exc),
            "open_ports": open_ports,
        }
    elapsed = round(
        time.monotonic() - started,
        2
    )
    open_ports.sort(
        key=lambda item: item["port"]
    )
    open_count = len(open_ports)
    result = {
        "status": "COMPLETED",
        "target": host,
        "ports_tested": len(ports),
        "open_count": open_count,
        "closed_count": len(ports) - open_count,
        "open_ports": open_ports,
        "duration": elapsed,
    }
    terminal(
        f"\n{COLORS['GREEN']}"
        f"[+] TCP assessment completed."
        f"{COLORS['RESET']}"
    )
    terminal(
        f"    Ports tested: {len(ports)}"
    )
    terminal(
        f"    Open ports: {open_count}"
    )
    terminal(
        f"    Closed/unavailable: {len(ports) - open_count}"
    )
    terminal(
        f"    Duration: {elapsed} seconds"
    )
    terminal(
        f"    Local files created: 0\n"
    )
    return result
# ============================================================
# COMMAND-LINE ENTRY POINT
# ============================================================
if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(
        description="BruteDog Live TCP Scanner"
    )
    parser.add_argument(
        "target",
        help="Target hostname"
    )
    args = parser.parse_args()
    asyncio.run(
        run_port_scanner(args.target)
    )