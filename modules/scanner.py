#!/usr/bin/env python3
"""
============================================================
 BRUTEDOG - ADVANCED SOURCE INTELLIGENCE PARSER
 Live endpoint discovery and sensitive-data exposure auditing.

 Python 3.10+
============================================================
"""

import asyncio
import http.client
import ssl
import re
import json
import os
import time

from datetime import datetime, timezone
from urllib.parse import urlsplit, urljoin, urlunsplit


# ============================================================
# CONFIGURATION
# ============================================================

MAX_CONCURRENCY = 15
REQUEST_TIMEOUT = 8
MAX_RESPONSE_SIZE = 2 * 1024 * 1024
MAX_JS_FILES = 20

REPORT_DIR = "reports/intelligence"

LEAK_PATHS = [
    "/",
    "/.env",
    "/.env.local",
    "/.env.production",
    "/env",
    "/config.js",
    "/config.json",
    "/api/config",
    "/health",
    "/debug/vars",
    "/actuator/env",
    "/server-status",
    "/phpinfo.php",
    "/.git/config",
    "/.git/HEAD",
    "/backup.zip",
    "/backup.tar.gz",
    "/database.sql",
    "/db.sql",
    "/swagger.json",
    "/openapi.json",
    "/api-docs",
    "/robots.txt",
    "/sitemap.xml",
    "/wp-config.php.bak",
]

SECRET_PATTERNS = {
    "AWS_ACCESS_KEY": (
        r"\bAKIA[0-9A-Z]{16}\b"
    ),
    "JWT_TOKEN": (
        r"\beyJ[A-Za-z0-9_-]{10,}\."
        r"[A-Za-z0-9_-]{10,}\."
        r"[A-Za-z0-9_-]{10,}\b"
    ),
    "PRIVATE_KEY_HEADER": (
        r"-----BEGIN (?:RSA |EC |OPENSSH )?"
        r"PRIVATE KEY-----"
    ),
    "EMAIL_ADDRESS": (
        r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\."
        r"[A-Za-z]{2,}\b"
    ),
    "POSSIBLE_SECRET_ASSIGNMENT": (
        r"""(?i)\b(password|passwd|secret|api_key|"""
        r"""access_token|client_secret)\b"""
        r"""\s*[:=]\s*["'][^"'\s]{6,}["']"""
    ),
    "EVM_PRIVATE_KEY_PATTERN": (
        r"\b(?:0x)?[a-fA-F0-9]{64}\b"
    ),
    "BITCOIN_WIF_PATTERN": (
        r"\b[5KL][1-9A-HJ-NP-Za-km-z]{50,51}\b"
    ),
}

JS_PATTERN = re.compile(
    r"""(?:src|href)\s*=\s*["']([^"']+\.js(?:\?[^"']*)?)["']""",
    re.IGNORECASE
)


# ============================================================
# TARGET NORMALIZATION
# ============================================================

def normalize_target(target):

    target = target.strip()

    if "://" not in target:
        target = "https://" + target

    parsed = urlsplit(target)

    if not parsed.hostname:
        raise ValueError("Invalid target.")

    if parsed.scheme not in ("http", "https"):
        raise ValueError("Only HTTP and HTTPS are supported.")

    hostname = parsed.hostname.encode(
        "idna"
    ).decode("ascii")

    port = parsed.port or (
        443 if parsed.scheme == "https" else 80
    )

    return {
        "scheme": parsed.scheme,
        "hostname": hostname,
        "port": port,
        "base_url": urlunsplit((
            parsed.scheme,
            parsed.netloc,
            "",
            "",
            ""
        ))
    }


# ============================================================
# REDACTION
# ============================================================

def redact_value(value):

    if not value:
        return "[REDACTED]"

    if len(value) <= 8:
        return "[REDACTED]"

    return value[:4] + "..." + value[-4:]


# ============================================================
# SECRET DETECTION
# ============================================================

def scan_text_for_secrets(text, source):

    findings = []

    for category, pattern in SECRET_PATTERNS.items():

        try:
            matches = re.finditer(pattern, text)

            for match in matches:

                value = match.group(0)

                findings.append({
                    "type": category,
                    "source": source,
                    "evidence": redact_value(value),
                    "offset": match.start(),
                    "length": len(value),
                    "validation": "PATTERN_MATCH_ONLY"
                })

        except re.error:
            continue

    return findings


# ============================================================
# HTTP FETCH
# ============================================================

def fetch_sync(target, path):

    scheme = target["scheme"]
    hostname = target["hostname"]
    port = target["port"]

    connection = None

    try:

        if scheme == "https":

            context = ssl.create_default_context()

            connection = http.client.HTTPSConnection(
                hostname,
                port,
                timeout=REQUEST_TIMEOUT,
                context=context
            )

        else:

            connection = http.client.HTTPConnection(
                hostname,
                port,
                timeout=REQUEST_TIMEOUT
            )

        connection.request(
            "GET",
            path,
            headers={
                "Host": hostname,
                "User-Agent": "BruteDog-Exposure-Audit/2.0",
                "Accept": "*/*",
                "Connection": "close"
            }
        )

        response = connection.getresponse()

        body = response.read(MAX_RESPONSE_SIZE + 1)

        truncated = len(body) > MAX_RESPONSE_SIZE

        body = body[:MAX_RESPONSE_SIZE]

        return {
            "path": path,
            "status": response.status,
            "headers": dict(response.getheaders()),
            "body": body.decode(
                "utf-8",
                errors="replace"
            ),
            "bytes_received": len(body),
            "truncated": truncated,
            "error": None
        }

    except Exception as exc:

        return {
            "path": path,
            "status": 0,
            "headers": {},
            "body": "",
            "bytes_received": 0,
            "truncated": False,
            "error": str(exc)
        }

    finally:

        if connection:
            connection.close()


# ============================================================
# SAME-ORIGIN JAVASCRIPT DISCOVERY
# ============================================================

def extract_js_urls(html, target):

    discovered = set()

    for match in JS_PATTERN.finditer(html):

        candidate = urljoin(
            target["base_url"],
            match.group(1)
        )

        parsed = urlsplit(candidate)

        expected_scheme = target["scheme"]
        expected_host = target["hostname"]
        expected_port = target["port"]

        candidate_port = parsed.port or (
            443 if parsed.scheme == "https" else 80
        )

        if (
            parsed.scheme != expected_scheme
            or parsed.hostname != expected_host
            or candidate_port != expected_port
        ):
            continue

        discovered.add(
            urlunsplit((
                "",
                "",
                parsed.path,
                parsed.query,
                ""
            ))
        )

    return sorted(discovered)[:MAX_JS_FILES]


# ============================================================
# REPORT DIRECTORY
# ============================================================

def ensure_report_directory():

    os.makedirs(
        REPORT_DIR,
        exist_ok=True
    )


# ============================================================
# MAIN PARSER
# ============================================================

async def parse_target_source(host):

    started = time.monotonic()

    target = normalize_target(host)

    semaphore = asyncio.Semaphore(
        MAX_CONCURRENCY
    )

    findings = []
    endpoint_results = []
    js_results = []

    async def fetch_limited(path):

        async with semaphore:

            return await asyncio.to_thread(
                fetch_sync,
                target,
                path
            )

    # --------------------------------------------------------
    # PHASE 1: ENDPOINT DISCOVERY
    # --------------------------------------------------------

    initial_results = await asyncio.gather(
        *[
            fetch_limited(path)
            for path in LEAK_PATHS
        ]
    )

    for result in initial_results:

        endpoint_results.append({
            "path": result["path"],
            "status": result["status"],
            "bytes": result["bytes_received"],
            "truncated": result["truncated"],
            "error": result["error"]
        })

        if result["status"] == 0:
            continue

        if result["status"] in (200, 206):

            body = result["body"]

            findings.extend(
                scan_text_for_secrets(
                    body,
                    result["path"]
                )
            )

    # --------------------------------------------------------
    # PHASE 2: JAVASCRIPT DISCOVERY
    # --------------------------------------------------------

    root_result = next(
        (
            item for item in initial_results
            if item["path"] == "/"
        ),
        None
    )

    js_paths = []

    if root_result and root_result["status"] == 200:

        js_paths = extract_js_urls(
            root_result["body"],
            target
        )

    # --------------------------------------------------------
    # PHASE 3: JAVASCRIPT ANALYSIS
    # --------------------------------------------------------

    if js_paths:

        js_responses = await asyncio.gather(
            *[
                fetch_limited(path)
                for path in js_paths
            ]
        )

        for result in js_responses:

            js_results.append({
                "path": result["path"],
                "status": result["status"],
                "bytes": result["bytes_received"],
                "truncated": result["truncated"]
            })

            if result["status"] in (200, 206):

                findings.extend(
                    scan_text_for_secrets(
                        result["body"],
                        result["path"]
                    )
                )

    # --------------------------------------------------------
    # PHASE 4: CLASSIFICATION
    # --------------------------------------------------------

    unique_findings = []
    seen = set()

    for finding in findings:

        key = (
            finding["type"],
            finding["source"],
            finding["offset"]
        )

        if key not in seen:

            seen.add(key)
            unique_findings.append(finding)

    exposed_resources = [
        item for item in endpoint_results
        if item["status"] in (200, 206)
        and item["path"] != "/"
    ]

    duration = round(
        time.monotonic() - started,
        3
    )

    report = {
        "tool": "BruteDog",
        "module": "Source Intelligence Parser",
        "version": "2.0",
        "target": target["base_url"],
        "timestamp": datetime.now(
            timezone.utc
        ).isoformat(),
        "duration_seconds": duration,
        "summary": {
            "endpoints_tested": len(endpoint_results),
            "javascript_files_discovered": len(js_paths),
            "javascript_files_tested": len(js_results),
            "exposed_resources": len(exposed_resources),
            "secret_pattern_matches": len(unique_findings)
        },
        "endpoint_results": endpoint_results,
        "javascript_results": js_results,
        "exposed_resources": exposed_resources,
        "findings": unique_findings,
        "limitations": [
            "Pattern matches are not proof of valid credentials.",
            "HTTP 200 does not establish sensitive-data exposure.",
            "Authentication requirements may affect discovery.",
            "Secret values are redacted from reports.",
            "Responses exceeding the size limit are truncated."
        ]
    }

    # --------------------------------------------------------
    # PHASE 5: REPORT STORAGE
    # --------------------------------------------------------

    ensure_report_directory()

    timestamp = int(time.time())

    report_path = os.path.join(
        REPORT_DIR,
        f"source_audit_{timestamp}.json"
    )

    with open(
        report_path,
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            report,
            file,
            indent=4
        )

    print("\n====================================")
    print(" BRUTEDOG SOURCE AUDIT COMPLETE")
    print("====================================")

    print(f"Target: {target['base_url']}")

    print(
        f"Endpoints tested: "
        f"{len(endpoint_results)}"
    )

    print(
        f"JavaScript files discovered: "
        f"{len(js_paths)}"
    )

    print(
        f"Exposed resources: "
        f"{len(exposed_resources)}"
    )

    print(
        f"Secret pattern matches: "
        f"{len(unique_findings)}"
    )

    print(f"Duration: {duration}s")

    print(f"Report: {report_path}")

    return report


# ============================================================
# STANDALONE EXECUTION
# ============================================================

if __name__ == "__main__":

    import argparse

    parser = argparse.ArgumentParser(
        description="BruteDog Source Intelligence Parser"
    )

    parser.add_argument(
        "target",
        help="Target hostname or URL"
    )

    args = parser.parse_args()

    asyncio.run(
        parse_target_source(args.target)
    )