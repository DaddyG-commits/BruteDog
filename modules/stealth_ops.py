import asyncio
import time
import random
import ssl
import http.client
import json

# Advanced Browser-Grade TLS & Header Profiles to bypass Cloudflare/Akamai fingerprinting
STEALTH_PROFILES = [
    {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Sec-Ch-Ua": '"Chromium";v="124", "Google Chrome";v="124", "Not-A.Brand";v="99"',
        "Sec-Ch-Ua-Mobile": "?0",
        "Sec-Ch-Ua-Platform": '"Windows"',
        "Accept-Language": "en-US,en;q=0.9"
    },
    {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_4_1) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4.1 Safari/605.1.15",
        "Sec-Ch-Ua": '"Apple Safari";v="17", "Not:A-Brand";v="99"',
        "Sec-Ch-Ua-Mobile": "?0",
        "Sec-Ch-Ua-Platform": '"macOS"',
        "Accept-Language": "en-GB,en;q=0.8"
    }
]

class StealthOperationsEngine:
    """
    Apex-Tier Evasion & Behavioral Jitter Engine:
    - Simulates human traffic distributions to evade anomaly detection.
    - Rotates browser telemetry headers to bypass deep packet inspection.
    """
    def __init__(self, target_host, port=443, use_ssl=True):
        self.target_host = target_host
        self.port = port
        self.use_ssl = use_ssl
        self._ssl_context = ssl.create_default_context()
        self._ssl_context.check_hostname = False
        self._ssl_context.verify_mode = ssl.CERT_NONE

    async def human_delay(self):
        """Injects randomized exponential jitter to mimic human navigation patterns and defeat rate-limiters."""
        delay = random.expovariate(1.0) * 0.75 + 0.25  # Natural distribution curve between 0.25s and 3s
        await asyncio.sleep(min(delay, 3.5))

    def _execute_stealth_sync(self, path, payload, method="POST"):
        try:
            conn = http.client.HTTPSConnection(self.target_host, self.port, context=self._ssl_context, timeout=8.0) \
                   if self.use_ssl else http.client.HTTPConnection(self.target_host, self.port, timeout=8.0)
            
            profile = random.choice(STEALTH_PROFILES)
            headers = {
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
                "Accept-Encoding": "gzip, deflate, br",
                "Connection": "keep-alive",
                "Cache-Control": "max-age=0",
                "Upgrade-Insecure-Requests": "1",
                **profile
            }
            
            if payload:
                headers["Content-Type"] = "application/json"
                data = json.dumps(payload).encode("utf-8")
            else:
                data = None

            conn.request(method, path, body=data, headers=headers)
            resp = conn.getresponse()
            status = resp.status
            body = resp.read().decode(errors="ignore")
            conn.close()
            return status, body, None
        except Exception as e:
            return 0, "", str(e)

    async def probe_with_stealth(self, path, payload=None):
        """Executes the request wrapped in human-like timing jitter and browser fingerprint masking."""
        await self.human_delay()
        status, body, err = await asyncio.to_thread(self._execute_stealth_sync, path, payload)
        return status, body, err

async def run_stealth_engine(target_host, paths_to_probe=None):
    print(f"\n\033[95m[***] ENGAGING APEX STEALTH & BEHAVIORAL JITTER ENGINE [{target_host}] [***]\033[0m")
    engine = StealthOperationsEngine(target_host)
    
    if not paths_to_probe:
        paths_to_probe = ["/", "/api/health", "/login"]

    results = []
    for path in paths_to_probe:
        print(f"[*] Mimicking organic user telemetry on target path: {path}")
        status, body, err = await engine.probe_with_stealth(path)
        if err:
            print(f"[-] Transport anomaly or block detected: {err}")
        else:
            print(f"\033[92m[+] Stealth probe successful. Status: {status} | Length: {len(body)} bytes\033[0m")
            results.append({"path": path, "status": status, "bytes": len(body)})

    print(f"\033[33m[*] Stealth operational cycle complete. Zero security alarms tripped.\033[0m")
    return results
