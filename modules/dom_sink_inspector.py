#!/usr/bin/env python3
"""
DOM_SINK_INSPECTOR.PY — Client-Side JavaScript Bundle & Route Harvester
Features:
- Extracts hidden API endpoints, fetch/axios routes, and internal paths from JS bundles
- Sniffs hardcoded configuration tokens or secret keys in client-side source code
"""
import re
import json

# Regex patterns for uncovering hidden API routes and endpoints inside JS chunks
ENDPOINT_PATTERN = re.compile(r'["\'](/api/[a-zA-Z0-9_\-/]+|/v\d+/[a-zA-Z0-9_\-/]+)["\']', re.I)
SECRET_PATTERN = re.compile(r'["\']([a-zA-Z0-9_\-]{20,45})["\']', re.I)

def inspect_js_bundle(bundle_content):
    """
    Parses JavaScript source text to uncover hidden routes and embedded credentials.
    """
    discovered_routes = set()
    potential_secrets = set()

    if not bundle_content:
        return discovered_routes, potential_secrets

    for match in ENDPOINT_PATTERN.findall(bundle_content):
        if len(match) > 3 and not match.endswith(('.js', '.css', '.png', '.jpg')):
            discovered_routes.add(match)

    for match in SECRET_PATTERN.findall(bundle_content):
        # Filter out common benign strings (UUIDs, standard hashes length checks)
        if len(match) > 20 and not match.startswith(('http', 'sha', 'data')):
            potential_secrets.add(match)

    return sorted(list(discovered_routes)), sorted(list(potential_secrets))
