#!/usr/bin/env python3
"""
BEHAVIORAL_MIMIC.PY — Human Pacing & Telemetry Jitter Wrapper
Features:
- Injects randomized human-like micro-delays between requests
- Rotates realistic Sec-Ch-Ua client hints and browser metadata headers
"""
import time
import random

BROWSER_HINTS = [
    {"sec-ch-ua": '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"', "sec-ch-ua-mobile": "?0", "sec-ch-ua-platform": '"Windows"'},
    {"sec-ch-ua": '"Not_A Brand";v="8", "Safari";v="17", "Apple Safari";v="17"', "sec-ch-ua-mobile": "?0", "sec-ch-ua-platform": '"macOS"'},
    {"sec-ch-ua": '"Not_A Brand";v="8", "Firefox";v="121", "Mozilla";v="121"', "sec-ch-ua-mobile": "?0", "sec-ch-ua-platform": '"Linux"'}
]

def apply_behavioral_jitter():
    """
    Introduces a randomized human-like delay (between 0.3s and 1.2s) 
    to prevent triggering rapid-fire rate-limiting defenses.
    """
    delay = random.uniform(0.3, 1.2)
    time.sleep(delay)

def get_randomized_hints():
    """
    Returns randomized browser telemetry hints for request headers.
    """
    return random.choice(BROWSER_HINTS)
