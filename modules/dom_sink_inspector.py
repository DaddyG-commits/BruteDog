#!/usr/bin/env python3
"""
DOM_SINK_INSPECTOR.PY v8.6 — Client-Side Bundle & Route Harvester
"""
import asyncio
import hashlib
import re
import sys
from urllib.parse import urljoin
import urllib.request

from modules.behavioral_mimic import apply_behavioral_jitter
from modules.loot_logger import save_session_loot
from modules.telegram_notifier import send_telegram_alert
from modules.telemetry import stream_proof

ENDPOINT_PATTERN = re.compile(r"""["'](/api/[a-zA-Z0-9_\-/]+|/v\d+/[a-zA-Z0-9_\-/]+)["']""", re.I)
SECRET_PATTERN = re.compile(r"""["']([a-zA-Z0-9_\-]{20,45})["']""", re.I)


async def broadcast_tg_alert_async(loot_type, details):
    try:
        await send_telegram_alert(loot_type, details)
    except Exception:
        pass


def broadcast_tg_alert_sync(loot_type, details):
    """Schedules non-blocking notifications when called from synchronous contexts."""
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


def _fetch_if_url(target_or_content: str, timeout: int = 5) -> tuple[str, str]:
    text = (target_or_content or "").strip()
    if not text.startswith(("http://", "https://")):
        return text, "bundle.js"
    try:
        req = urllib.request.Request(text, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read(250_000).decode("utf-8", errors="ignore")
            return raw, urljoin(text, "/")
    except Exception:
        return "", text


def inspect_js_bundle(bundle_content, target_context="https://example.com", source_label="bundle.js"):
    """Parses script source text for route/token patterns and records structured results."""
    apply_behavioral_jitter()
    discovered_routes = set()
    potential_secrets = set()

    if not bundle_content or not isinstance(bundle_content, str):
        return [], []

    for match in ENDPOINT_PATTERN.findall(bundle_content):
        if len(match) > 3 and not match.endswith((".js", ".css", ".png", ".jpg", ".svg")):
            discovered_routes.add(match)

    for match in SECRET_PATTERN.findall(bundle_content):
        if len(match) > 20 and not match.startswith(("http", "sha", "data")):
            potential_secrets.add(match)

    routes_list = sorted(discovered_routes)
    secrets_list = sorted(potential_secrets)

    if routes_list or secrets_list:
        loot_hash = hashlib.sha256(bundle_content.encode("utf-8", errors="ignore")).hexdigest()
        bundle_evidence = {
            "source_file": source_label,
            "integrity_hash": loot_hash,
            "discovered_routes": routes_list,
            "potential_secrets": secrets_list,
        }
        broadcast_tg_alert_sync("DOM Bundle Inspection Artifacts Harvested", bundle_evidence)
        stream_proof("DOM_BUNDLE_HARVEST", source_label, {"hash": loot_hash}, bundle_content[:300], bundle_evidence)
        save_session_loot(
            target=target_context,
            endpoint=source_label,
            finding_type="DOM_BUNDLE_INSPECTION_ARTEFACTS",
            status=200,
            headers={},
            body=bundle_content,
            extra_loot=bundle_evidence,
        )

    return routes_list, secrets_list


async def inspect_dom_sinks(target_or_content=None, details=None, source_label="bundle.js", **kwargs):
    """Async entry point compatible with single-argument target calls and explicit detail calls."""
    if isinstance(target_or_content, str) and details is not None:
        await broadcast_tg_alert_async(target_or_content, details)
        return {"status": "notified", "routes": [], "secrets": []}

    content, resolved_source = _fetch_if_url(str(target_or_content or ""))
    label = kwargs.get("endpoint") or source_label or resolved_source
    target_ctx = str(target_or_content or "https://example.com")
    routes, secrets = await asyncio.to_thread(inspect_js_bundle, content, target_ctx, label)
    return {
        "status": "completed",
        "target": target_ctx,
        "routes": routes,
        "secrets": secrets,
    }


if __name__ == "__main__":
    if len(sys.argv) > 1:
        with open(sys.argv[1], "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()
            routes, secrets = inspect_js_bundle(content, source_label=sys.argv[1])
            print(f"[+] Discovered Routes ({len(routes)}): {routes}")
            print(f"[+] Potential Secrets ({len(secrets)}): {secrets}")
    else:
        print("Usage: python3 dom_sink_inspector.py <js_bundle_file>")
