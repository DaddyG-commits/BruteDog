#!/usr/bin/env python3
"""
BEHAVIORAL_MIMIC.PY v8.6 — Pacing Jitter, Client Hints & Browser Fallback Helper
"""
import asyncio
import hashlib
import os
import random
import time

from modules.loot_logger import save_session_loot
from modules.telemetry import stream_proof

BROWSER_HINTS = [
    {
        "sec-ch-ua": '"Not_A Brand";v="8", "Chromium";v="122", "Google Chrome";v="122"',
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": '"Windows"',
    },
    {
        "sec-ch-ua": '"Not_A Brand";v="8", "Safari";v="17.2", "Apple Safari";v="17.2"',
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": '"macOS"',
    },
    {
        "sec-ch-ua": '"Not_A Brand";v="8", "Firefox";v="123", "Mozilla";v="123"',
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": '"Linux"',
    },
    {
        "sec-ch-ua": '"Chromium";v="122", "Not(A:Brand";v="99", "Google Chrome";v="122"',
        "sec-ch-ua-mobile": "?1",
        "sec-ch-ua-platform": '"Android"',
    },
]


def _compute_jitter_delay(base_mean=0.08, min_delay=0.02, max_delay=0.25) -> float:
    if os.environ.get("BRUTEDOG_NO_JITTER", "").strip().lower() in ("1", "true", "yes"):
        return 0.0
    mean = max(0.01, float(base_mean))
    low = max(0.0, float(min_delay))
    high = max(low, float(max_delay))
    delay = random.expovariate(1.0 / mean)
    return max(low, min(delay, high))


def apply_behavioral_jitter(base_mean=0.08, min_delay=0.02, max_delay=0.25):
    """Applies a short bounded exponential jitter delay for synchronous callers."""
    clamped_delay = _compute_jitter_delay(base_mean=base_mean, min_delay=min_delay, max_delay=max_delay)
    if clamped_delay > 0:
        time.sleep(clamped_delay)
    return clamped_delay


async def async_apply_behavioral_jitter(base_mean=0.08, min_delay=0.02, max_delay=0.25):
    """Applies a short bounded exponential jitter delay without blocking an async loop."""
    clamped_delay = _compute_jitter_delay(base_mean=base_mean, min_delay=min_delay, max_delay=max_delay)
    if clamped_delay > 0:
        await asyncio.sleep(clamped_delay)
    return clamped_delay


def get_randomized_hints():
    """Returns a fresh copy of randomized client hint headers."""
    return dict(random.choice(BROWSER_HINTS))


async def solve_edge_challenge_with_browser(target_url):
    """Attempts Playwright browser session capture if installed; returns None safely otherwise."""
    try:
        from playwright.async_api import async_playwright
    except ImportError:
        return None

    browser = None
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=True,
                args=[
                    "--disable-blink-features=AutomationControlled",
                    "--no-sandbox",
                    "--disable-setuid-sandbox",
                    "--disable-infobars",
                ],
            )
            context = await browser.new_context(
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
                ),
                viewport={"width": 1920, "height": 1080},
                ignore_https_errors=True,
            )
            page = await context.new_page()
            await page.goto(target_url, timeout=12000, wait_until="domcontentloaded")
            await page.wait_for_timeout(1500)

            cookies = await context.cookies()
            cookie_string = "; ".join(
                [f"{c['name']}={c['value']}" for c in cookies if isinstance(c, dict) and c.get("name")]
            )

            if cookie_string:
                loot_hash = hashlib.sha256(cookie_string.encode("utf-8", errors="ignore")).hexdigest()
                payload = {
                    "target": target_url,
                    "cookies": cookie_string,
                    "integrity_hash": loot_hash,
                }
                stream_proof("BROWSER_SESSION_CAPTURE", target_url, {}, cookie_string[:100], payload)
                save_session_loot(
                    target=target_url,
                    endpoint="browser_capture",
                    finding_type="BROWSER_SESSION_CAPTURED",
                    status=200,
                    headers={},
                    body=cookie_string,
                    extra_loot=payload,
                )

            return cookie_string or None
    except Exception:
        return None
    finally:
        if browser is not None:
            try:
                await browser.close()
            except Exception:
                pass
