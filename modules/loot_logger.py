#!/usr/bin/env python3
"""
BRUTEDOG LOOT LOGGER v8.6 — Artifact & Response Persistence Module
"""
import asyncio
from datetime import datetime
import hashlib
import json
import os
import re

from modules.telegram_notifier import send_telegram_alert

LOOT_DIR = "loot_output"

CHALLENGE_PATTERNS = [
    r"<title>\s*security check\s*</title>",
    r"just a moment\.\.\.",
    r"checking your browser",
    r"cf-browser-verification",
    r"cdn-cgi/challenge-platform",
    r"__cf_chl_",
    r"ddos-guard",
    r"incapsula",
    r"sucuri website firewall",
    r'<meta\s+name=["\']robots["\']\s+content=["\']noindex,\s*nofollow["\']',
]
_CHALLENGE_RE = re.compile("|".join(CHALLENGE_PATTERNS), re.IGNORECASE)
_SAFE_NAME_RE = re.compile(r"[^A-Za-z0-9._-]+")
_background_tasks: set[asyncio.Task] = set()


def should_persist_loot(finding_type: str, status: int, body: str, extra_loot: dict = None) -> tuple[bool, str]:
    """Filters out challenge pages and non-actionable responses before disk/alert writes."""
    if status in (401, 403, 404, 405, 406, 429, 502, 503):
        return False, f"HTTP {status}"

    content = body if isinstance(body, str) else ""
    extra_text = json.dumps(extra_loot, default=str) if isinstance(extra_loot, dict) else ""
    combined = f"{content}\n{extra_text}".strip()

    if _CHALLENGE_RE.search(combined):
        return False, "Challenge/WAF page signature"

    stripped = content.lstrip().lower()
    is_html = stripped.startswith("<!doctype html") or stripped.startswith("<html")
    finding_upper = str(finding_type or "").upper()
    html_findings = {"XSS", "DOM_XSS", "OPEN_REDIRECT", "CORS_MISCONFIG", "HTML_INJECTION"}
    if is_html and not any(tag in finding_upper for tag in html_findings):
        return False, "HTML shell for non-HTML finding"

    return True, ""


async def _send_alert_with_timeout(loot_type: str, details: dict) -> None:
    try:
        await asyncio.wait_for(send_telegram_alert(loot_type, details), timeout=8)
    except Exception:
        pass


def broadcast_tg_alert_sync(loot_type, details):
    """Non-blockingly fires alerts from synchronous logger functions."""
    try:
        loop = asyncio.get_running_loop()
        if not loop.is_closed():
            task = loop.create_task(_send_alert_with_timeout(loot_type, details))
            _background_tasks.add(task)
            task.add_done_callback(_background_tasks.discard)
    except RuntimeError:
        try:
            asyncio.run(_send_alert_with_timeout(loot_type, details))
        except Exception:
            pass


def _sanitize_segment(raw: str, fallback: str) -> str:
    cleaned = str(raw or "").replace("https://", "").replace("http://", "").replace("..", "")
    cleaned = _SAFE_NAME_RE.sub("_", cleaned).strip("._")
    return (cleaned[:80] or fallback)


def save_session_loot(
    target: str,
    endpoint: str,
    finding_type: str,
    status: int,
    headers: dict,
    body: str,
    extra_loot: dict = None,
):
    allowed, reason = should_persist_loot(finding_type, status, body, extra_loot)
    if not allowed:
        print(
            f"\033[93m[~] Skipped artifact persistence [{finding_type}] on {endpoint}: {reason}\033[0m",
            flush=True,
        )
        return None

    os.makedirs(LOOT_DIR, exist_ok=True)
    now = datetime.now()
    timestamp = now.strftime("%Y%m%d_%H%M%S")
    micro_tag = f"{now.microsecond:06d}"

    safe_target = _sanitize_segment(target, "target")
    safe_endpoint = _sanitize_segment(endpoint, "root")
    safe_finding = _sanitize_segment(finding_type, "finding")

    body_content = body if isinstance(body, str) else str(body or "")
    loot_hash = hashlib.sha256(body_content.encode("utf-8", errors="ignore")).hexdigest()
    short_hash = loot_hash[:8]

    base_filename = os.path.join(
        LOOT_DIR,
        f"{safe_target}_{safe_endpoint}_{safe_finding}_{timestamp}_{micro_tag}_{short_hash}",
    )

    html_filename = f"{base_filename}_session_loot.html"
    with open(html_filename, "w", encoding="utf-8") as f:
        f.write(f"<!-- TARGET: {target} -->\n")
        f.write(f"<!-- ENDPOINT: {endpoint} -->\n")
        f.write(f"<!-- FINDING: {finding_type} (HTTP {status}) -->\n")
        f.write(f"<!-- INTEGRITY_HASH_SHA256: {loot_hash} -->\n")
        f.write(f"<!-- TIMESTAMP: {timestamp} -->\n\n")
        f.write(body_content)

    json_filename = f"{base_filename}_metadata.json"
    loot_payload = {
        "target": target,
        "endpoint": endpoint,
        "finding_type": finding_type,
        "status": status,
        "headers": dict(headers) if isinstance(headers, dict) else {},
        "integrity_hash": loot_hash,
        "extra_loot": extra_loot if isinstance(extra_loot, dict) else {},
        "timestamp": timestamp,
        "saved_files": [html_filename, json_filename],
    }
    with open(json_filename, "w", encoding="utf-8") as f:
        json.dump(loot_payload, f, indent=4, default=str)

    broadcast_tg_alert_sync(f"Loot Persisted [{finding_type}]", loot_payload)
    print(
        f"\033[92m[+] LOOT PERSISTED: Saved artifacts -> {html_filename} & {json_filename} [SHA-256: {loot_hash[:16]}...]\033[0m",
        flush=True,
    )
    return loot_payload
