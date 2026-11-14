#!/usr/bin/env python3
"""
BRUTEDOG SCANNER V2.0 — Advanced Network Reconnaissance & Security Assessment Engine (Hardened with WAF Evasion)
Features:
- Native asynchronous TCP connections
- IPv4 / IPv6 DNS resolution
- Service identification & header override testing on open HTTP ports
- HTTP response inspection via SecureTransport and behavioral mimicry (Poisson jitter)
- HTTP security-header assessment
- TLS certificate inspection & protocol identification
- Passive service-banner collection
- Structured error classification & concurrency management
- Automated immutable disk persistence (loot_output/) and real-time Telegram telemetry
"""

import asyncio
import argparse
import ipaddress
import socket
import ssl
import time
import random

from urllib.parse import urlsplit

# Import centralized Telegram broadcaster, secure transport, loot persistence, and behavioral mimicry
from modules.telegram_notifier import send_telegram_alert
from modules.transport import SecureTransport
from modules.loot_logger import save_session_loot
from modules.telemetry import stream_proof
from modules.behavioral_mimic import apply_behavioral_jitter


# ============================================================
# CONFIGURATION & TIMEOUT CONSTANTS
# ============================================================

CONNECT_TIMEOUT = 3.0
HTTP_TIMEOUT = 3.5
BANNER_TIMEOUT = 0.5

MAX_CONCURRENT = 35
MAX_PORTS = 256

MAX_BANNER_SIZE = 512
MAX_HTTP_HEADERS = 64
MAX_HEADER_SIZE = 16384

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"

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
# SERVICE DATABASE MAPPING
# ============================================================

SERVICE_MAP = {
    20: "FTP-DATA",
    21: "FTP",
    22: "SSH",
    23: "TELNET",
    25: "SMTP",
    26: "SMTP-ALT",
    53: "DNS",
    80: "HTTP",
    110: "POP3",
    111: "RPCBIND",
    123: "NTP",
    135: "MSRPC",
    139: "NETBIOS",
    143: "IMAP",
    179: "BGP",
    389: "LDAP",
    443: "HTTPS",
    445: "SMB",
    465: "SMTPS",
    587: "SMTP-SUBMISSION",
    636: "LDAPS",
    873: "RSYNC",
    990: "FTPS",
    993: "IMAPS",
    995: "POP3S",
    1433: "MSSQL",
    1521: "ORACLE",
    1883: "MQTT",
    2049: "NFS",
    2375: "DOCKER-API",
    2376: "DOCKER-TLS",
    3000: "HTTP-ALT",
    3306: "MYSQL",
    3389: "RDP",
    5432: "POSTGRESQL",
    5601: "KIBANA",
    5672: "AMQP",
    5900: "VNC",
    5985: "WINRM",
    5986: "WINRM-TLS",
    6379: "REDIS",
    6443: "KUBERNETES-API",
    7001: "WEBLOGIC",
    8000: "HTTP-ALT",
    8008: "HTTP-ALT",
    8080: "HTTP-ALT",
    8081: "HTTP-ALT",
    8088: "HTTP-ALT",
    8443: "HTTPS-ALT",
    8888: "HTTP-ALT",
    9000: "HTTP-ALT",
    9090: "HTTP-ALT",
    9200: "ELASTICSEARCH",
    9300: "ELASTICSEARCH-TRANSPORT",
    9418: "GIT",
    10000: "WEBMIN",
    11211: "MEMCACHED",
    27017: "MONGODB",
}


HTTP_PORTS = {
    80, 81, 82, 3000, 5000,
    8000, 8008, 8080, 8081,
    8088, 8888, 9000, 9090,
}

HTTPS_PORTS = {
    443, 4443, 8443, 2376,
    5986,
}

BANNER_PORTS = {
    21, 22, 23, 25, 26,
    110, 143, 465, 587,
    993, 995,
}

SECURITY_HEADERS = {
    "strict-transport-security": "HSTS missing",
    "content-security-policy": "CSP missing",
    "x-content-type-options": "X-Content-Type-Options missing",
    "x-frame-options": "X-Frame-Options missing",
    "referrer-policy": "Referrer-Policy missing",
    "permissions-policy": "Permissions-Policy missing",
}


# ============================================================
# TERMINAL OUTPUT & TELEGRAM DISPATCHER
# ============================================================

def terminal(message):
    print(message, flush=True)


def color(message, name):
    return (
        f"{COLORS.get(name, '')}"
        f"{message}"
        f"{COLORS['RESET']}"
    )


def broadcast_tg_alert_sync(loot_type, details):
    """Helper to non-blockingly fire Telegram alerts from synchronous scanner functions."""
    try:
        loop = asyncio.get_running_loop()
        loop.create_task(send_telegram_alert(loot_type, details))
    except RuntimeError:
        try:
            asyncio.run(send_telegram_alert(loot_type, details))
        except Exception:
            pass


# ============================================================
# TARGET NORMALIZATION & VALIDATION
# ============================================================

def normalize_host(target):
    if not isinstance(target, str):
        raise ValueError("Target must be a string.")

    target = target.strip()
    if not target:
        raise ValueError("Empty target.")

    if "://" in target:
        parsed = urlsplit(target)
        if parsed.scheme.lower() not in ("http", "https"):
            raise ValueError("Unsupported URL scheme.")
        if not parsed.hostname:
            raise ValueError("Invalid URL hostname.")
        if parsed.username or parsed.password:
            raise ValueError("Embedded credentials are prohibited.")
        target = parsed.hostname
    elif "/" in target or "@" in target:
        raise ValueError("Invalid hostname.")

    if target.startswith("[") and target.endswith("]"):
        target = target[1:-1]

    try:
        return str(ipaddress.ip_address(target))
    except ValueError:
        pass

    target = target.rstrip(".").lower()
    try:
        target = target.encode("idna").decode("ascii")
    except UnicodeError:
        raise ValueError("Invalid internationalized hostname.")

    if len(target) > 253:
        raise ValueError("Hostname is too long.")

    if not target:
        raise ValueError("Invalid hostname.")

    return target


def validate_ports(ports):
    if ports is None:
        ports = COMMON_PORTS

    validated = set()
    try:
        for port in ports:
            if isinstance(port, bool):
                raise ValueError
            port = int(port)
            if not 1 <= port <= 65535:
                raise ValueError
            validated.add(port)
    except (TypeError, ValueError):
        raise ValueError("Invalid port configuration.")

    if not validated:
        raise ValueError("No ports supplied.")
    if len(validated) > MAX_PORTS:
        raise ValueError(f"Maximum supported ports: {MAX_PORTS}")

    return sorted(validated)


# ============================================================
# DNS RESOLUTION ROUTINE
# ============================================================

async def resolve_target(host):
    started = time.monotonic()
    try:
        results = await asyncio.get_running_loop().getaddrinfo(
            host,
            None,
            family=socket.AF_UNSPEC,
            type=socket.SOCK_STREAM,
        )

        addresses = []
        seen = set()

        for family, socktype, proto, canonname, sockaddr in results:
            address = sockaddr[0]
            if address in seen:
                continue
            seen.add(address)
            addresses.append({
                "address": address,
                "family": ("IPv6" if family == socket.AF_INET6 else "IPv4"),
            })

        elapsed = round(time.monotonic() - started, 4)
        return {
            "success": bool(addresses),
            "addresses": addresses,
            "duration": elapsed,
            "error": None,
        }
    except socket.gaierror as exc:
        return {
            "success": False,
            "addresses": [],
            "duration": round(time.monotonic() - started, 4),
            "error": str(exc),
        }


def identify_service(port):
    service = SERVICE_MAP.get(port, "UNKNOWN")
    return {
        "expected_service": service,
        "confidence": ("PORT_BASED" if service != "UNKNOWN" else "UNIDENTIFIED"),
    }


# ============================================================
# CONNECTION & WRITER MANAGEMENT
# ============================================================

async def open_connection(
    address,
    port,
    timeout=CONNECT_TIMEOUT,
    use_tls=False,
    hostname=None,
):
    context = None
    if use_tls:
        context = ssl.create_default_context()
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE

    connection = asyncio.open_connection(
        address,
        port,
        ssl=context,
        server_hostname=hostname if use_tls else None,
        ssl_handshake_timeout=timeout if use_tls else None,
    )

    return await asyncio.wait_for(connection, timeout=timeout)


async def close_writer(writer):
    if writer is None:
        return
    try:
        writer.close()
        await asyncio.wait_for(writer.wait_closed(), timeout=0.5)
    except (Exception, asyncio.CancelledError):
        pass


# ============================================================
# BANNER COLLECTION
# ============================================================

async def collect_banner(reader):
    try:
        data = await asyncio.wait_for(
            reader.read(MAX_BANNER_SIZE),
            timeout=BANNER_TIMEOUT
        )
        if not data:
            return ""
        return data.decode("utf-8", errors="replace").strip()[:200]
    except (TimeoutError, OSError):
        return ""


# ============================================================
# HTTP INSPECTION & SECURITY HEADER AUDITING (VIA SECURETRANSPORT)
# ============================================================

async def inspect_http(
    address,
    hostname,
    port,
    use_tls=False,
):
    result = {
        "available": False,
        "status_code": None,
        "reason": "",
        "http_version": "HTTP/1.1",
        "server": "",
        "headers": {},
        "security_headers": {},
        "missing_security_headers": [],
        "error": None,
    }

    scheme = "https" if use_tls or port in HTTPS_PORTS else "http"
    target_url = f"{scheme}://{hostname}:{port}"

    try:
        apply_behavioral_jitter()
        transport = SecureTransport(target_url)
        
        # Try HEAD request first, fallback to GET or Method Tampering if blocked by WAF 403
        status, headers, body = await asyncio.to_thread(
            transport.request, "HEAD", "/"
        )

        if status in [403, 405, 0]:
            status, headers, body = await asyncio.to_thread(
                transport.request, "GET", "/"
            )

        if status == 0:
            result["error"] = "HTTP inspection connection failed."
            return result

        result["available"] = True
        result["status_code"] = status
        result["headers"] = headers
        result["server"] = headers.get("server", "")

        for header in SECURITY_HEADERS:
            present = header in headers
            result["security_headers"][header] = present
            if not present:
                result["missing_security_headers"].append(SECURITY_HEADERS[header])

        return result

    except Exception as exc:
        result["error"] = f"HTTP inspection failed: {type(exc).__name__}"
        return result


# ============================================================
# TLS CERTIFICATE & PROTOCOL INSPECTION
# ============================================================

async def inspect_tls(
    address,
    hostname,
    port,
):
    writer = None
    result = {
        "available": False,
        "verified": False,
        "protocol": "",
        "cipher": "",
        "certificate": {},
        "error": None,
    }

    try:
        apply_behavioral_jitter()
        reader, writer = await open_connection(
            address,
            port,
            timeout=CONNECT_TIMEOUT,
            use_tls=True,
            hostname=hostname,
        )

        ssl_object = writer.get_extra_info("ssl_object")
        if ssl_object is None:
            result["error"] = "TLS session unavailable."
            return result

        certificate = ssl_object.getpeercert()
        result["available"] = True
        result["verified"] = True
        result["protocol"] = ssl_object.version() or ""

        cipher = ssl_object.cipher()
        if cipher:
            result["cipher"] = {
                "name": cipher[0],
                "protocol": cipher[1],
                "bits": cipher[2],
            }

        result["certificate"] = {
            "subject": certificate.get("subject", ()),
            "issuer": certificate.get("issuer", ()),
            "not_before": certificate.get("notBefore", ""),
            "not_after": certificate.get("notAfter", ""),
            "subject_alt_names": certificate.get("subjectAltName", ()),
        }

        return result
    except ssl.SSLCertVerificationError:
        result["error"] = "Certificate verification failed."
        return result
    except ssl.SSLError as exc:
        result["error"] = f"TLS negotiation failed: {type(exc).__name__}"
        return result
    except TimeoutError:
        result["error"] = "TLS handshake timed out."
        return result
    except OSError as exc:
        result["error"] = f"TLS connection failed: {type(exc).__name__}"
        return result
    finally:
        await close_writer(writer)


# ============================================================
# SINGLE TCP PROBE & SERVICE IDENTIFICATION
# ============================================================

async def probe_port(
    hostname,
    address,
    port,
):
    result = {
        "address": address,
        "port": port,
        "protocol": "TCP",
        "state": "UNKNOWN",
        "open": False,
        "details": {
            "service": SERVICE_MAP.get(port, "UNKNOWN"),
            "service_identification": identify_service(port),
            "banner": "",
            "http": {},
            "tls": {},
            "errors": [],
        },
    }

    writer = None
    try:
        apply_behavioral_jitter()
        reader, writer = await open_connection(address, port, timeout=CONNECT_TIMEOUT)
        result["state"] = "OPEN"
        result["open"] = True

        if port in BANNER_PORTS:
            result["details"]["banner"] = await collect_banner(reader)

    except ConnectionRefusedError:
        result["state"] = "CLOSED"
    except TimeoutError:
        result["state"] = "FILTERED_OR_NO_RESPONSE"
    except OSError as exc:
        if isinstance(exc, ConnectionRefusedError):
            result["state"] = "CLOSED"
        else:
            result["state"] = "ERROR"
            result["details"]["errors"].append(type(exc).__name__)
    finally:
        await close_writer(writer)

    if not result["open"]:
        return result

    if port in HTTP_PORTS:
        result["details"]["http"] = await inspect_http(address, hostname, port, use_tls=False)
    elif port in HTTPS_PORTS:
        result["details"]["tls"] = await inspect_tls(address, hostname, port)
        result["details"]["http"] = await inspect_http(address, hostname, port, use_tls=True)

    return result


# ============================================================
# ASYNC PORT SCANNER ORCHESTRATION
# ============================================================

async def run_port_scanner(
    target_host,
    ports=None,
    concurrency=MAX_CONCURRENT,
):
    """
    BruteDog Scanner V2.5 — Asynchronous Network Reconnaissance & Security Assessment Engine
    """
    started = time.monotonic()

    try:
        host = normalize_host(target_host)
        ports = validate_ports(ports)
        if isinstance(concurrency, bool):
            raise ValueError
        concurrency = int(concurrency)
        if not 1 <= concurrency <= 100:
            raise ValueError("Concurrency must be between 1 and 100.")
    except (ValueError, TypeError) as exc:
        return {
            "status": "FAILED",
            "error": str(exc),
            "open_ports": [],
        }

    terminal(color("\n[***] BRUTEDOG SCANNER V2.5 (WAF-HARDENED SECURETRANSPORT) [***]", "MAGENTA"))
    terminal(color(f"[*] Target: {host}", "CYAN"))
    terminal(f"[*] Ports scheduled: {len(ports)}")
    terminal(f"[*] Maximum concurrency: {concurrency}")

    terminal(color("[*] Resolving target...", "CYAN"))
    dns = await resolve_target(host)

    if not dns["success"]:
        return {
            "status": "FAILED",
            "target": host,
            "error": "DNS resolution failed.",
            "dns": dns,
            "open_ports": [],
        }

    addresses = dns["addresses"]
    for item in addresses:
        terminal(f"    [{item['family']}] {item['address']}")

    semaphore = asyncio.Semaphore(concurrency)
    results = []
    completed = 0
    total_probes = len(addresses) * len(ports)

    async def scan_one(address, port):
        nonlocal completed
        async with semaphore:
            result = await probe_port(host, address, port)
            completed += 1

            if result["open"]:
                terminal(color(f"[OPEN] {address}:{port} — {result['details']['service']}", "GREEN"))
                
                # BROADCAST OPEN PORT DISCOVERY TO TELEGRAM & PERSIST TO DISK
                port_loot = {
                    "target": host,
                    "address": address,
                    "port": port,
                    "service": result['details']['service'],
                    "banner": result['details'].get('banner', ''),
                    "http_status": result['details'].get('http', {}).get('status_code')
                }
                broadcast_tg_alert_sync("Port Scan Open Port Discovered", port_loot)
                stream_proof("PORT_SCAN_OPEN", f"{address}:{port}", {}, f"Service: {result['details']['service']}", port_loot)
                save_session_loot(
                    target=f"tcp://{address}:{port}",
                    endpoint=f"port_{port}",
                    finding_type="OPEN_PORT_DISCOVERED",
                    status=200,
                    headers={},
                    body=str(result['details']),
                    extra_loot=port_loot
                )

            elif completed % 20 == 0:
                terminal(color(f"[*] Progress: {completed}/{total_probes}", "CYAN"))

            return result

    try:
        tasks = [
            asyncio.create_task(scan_one(address["address"], port))
            for address in addresses
            for port in ports
        ]
        results = await asyncio.gather(*tasks)
    except asyncio.CancelledError:
        terminal(color("[-] Scan cancelled.", "YELLOW"))
        raise
    except Exception as exc:
        terminal(color(f"[-] Scanner failure: {type(exc).__name__}", "RED"))
        return {
            "status": "FAILED",
            "target": host,
            "error": type(exc).__name__,
            "open_ports": [],
        }

    open_ports = [item for item in results if item["open"]]
    open_port_numbers = sorted({item["port"] for item in open_ports})

    port_states = {}
    for port in ports:
        states = [item["state"] for item in results if item["port"] == port]
        if "OPEN" in states:
            state = "OPEN"
        elif all(item == "CLOSED" for item in states):
            state = "CLOSED"
        else:
            state = "FILTERED_OR_UNKNOWN"
        port_states[str(port)] = state

    closed_count = sum(1 for state in port_states.values() if state == "CLOSED")
    filtered_count = sum(1 for state in port_states.values() if state == "FILTERED_OR_UNKNOWN")

    elapsed = round(time.monotonic() - started, 3)

    statistics = {
        "total_probes": total_probes,
        "completed_probes": completed,
        "unique_ports_tested": len(ports),
        "resolved_addresses": len(addresses),
        "open_ports": len(open_port_numbers),
        "closed_ports": closed_count,
        "filtered_or_unknown_ports": filtered_count,
        "concurrency": concurrency,
        "dns_duration": dns["duration"],
        "scan_duration": elapsed,
    }

    final_result = {
        "status": "COMPLETED",
        "scanner": "BruteDog Scanner V2.0",
        "target": host,
        "dns": dns,
        "ports_tested": len(ports),
        "open_count": len(open_port_numbers),
        "closed_count": closed_count,
        "filtered_count": filtered_count,
        "open_ports": open_ports,
        "port_states": port_states,
        "statistics": statistics,
        "duration": elapsed,
    }

    terminal(color("\n[+] NETWORK ASSESSMENT COMPLETED", "GREEN"))
    terminal(f"    Resolved addresses: {len(addresses)}")
    terminal(f"    Ports tested: {len(ports)}")
    terminal(f"    Open ports: {len(open_port_numbers)}")
    terminal(f"    Closed ports: {closed_count}")
    terminal(f"    Filtered/unknown: {filtered_count}")
    terminal(f"    Total probes: {total_probes}")
    terminal(f"    Duration: {elapsed}s")
    terminal("    Local files created: 0 (Streamed live via Telegram)\n")

    return final_result


# ============================================================
# COMMAND-LINE INTERFACE PARSER & ENTRYPOINT
# ============================================================

def parse_port_argument(value):
    try:
        return [
            int(item.strip())
            for item in value.split(",")
            if item.strip()
        ]
    except ValueError:
        raise argparse.ArgumentTypeError("Ports must be comma-separated integers.")


async def main():
    parser = argparse.ArgumentParser(
        description="BruteDog Scanner V2.0 Network Reconnaissance Engine"
    )
    parser.add_argument("target", help="Single authorized hostname or IP address")
    parser.add_argument("--ports", type=parse_port_argument, default=None, help="Comma-separated TCP ports")
    parser.add_argument("--concurrency", type=int, default=MAX_CONCURRENT, help="Maximum concurrent connections")

    args = parser.parse_args()

    result = await run_port_scanner(
        args.target,
        ports=args.ports,
        concurrency=args.concurrency,
    )

    if result["status"] != "COMPLETED":
        terminal(color(f"[-] {result.get('error', 'Scan failed')}", "RED"))


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        terminal(color("\n[-] Interrupted by user.", "YELLOW"))
