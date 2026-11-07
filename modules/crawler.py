#!/usr/bin/env python3
"""
CRAWLER.PY — Dynamic Endpoint & API Route Discovery Module
Features:
- Pure Python HTML parsing and link extraction
- Automatic detection of internal links, form actions, and API endpoints
- Zero-disk in-memory route collection
"""
import http.client
import re
import ssl
import sys
from urllib.parse import urlparse, urljoin, urlsplit

USER_AGENT = "BruteDog-Offensive-Crawler/5.5"

def log(msg, color="\033[92m"):
    sys.stdout.write(f"{color}{msg}\033[0m\n")
    sys.stdout.flush()

def fetch_page(host, port, path, secure):
    conn = None
    try:
        if secure:
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
            conn = http.client.HTTPSConnection(host, port, timeout=6, context=ctx)
        else:
            conn = http.client.HTTPConnection(host, port, timeout=6)
            
        headers = {"User-Agent": USER_AGENT, "Accept": "text/html,application/json,*/*"}
        conn.request("GET", path, headers=headers)
        res = conn.getresponse()
        data = res.read(256 * 1024).decode("utf-8", errors="replace")
        return res.status, data
    except Exception:
        return 0, ""
    finally:
        if conn:
            conn.close()

def crawl_target(target_url):
    log("\n[***] INITIALIZING DYNAMIC ENDPOINT CRAWLER [***]", "\033[95m")
    parsed = urlsplit(target_url if "://" in target_url else f"https://{target_url}")
    host = parsed.hostname
    secure = parsed.scheme == "https"
    port = parsed.port or (443 if secure else 80)
    base_path = parsed.path.rstrip("/")
    
    discovered_endpoints = set()
    seed_paths = [base_path or "/", "/login", "/api", "/signup", "/dashboard"]

    # Regex patterns to extract hrefs, form actions, and potential API paths from HTML/JS
    href_pattern = re.compile(r'href=["\']([^"\']+)["\']', re.I)
    action_pattern = re.compile(r'action=["\']([^"\']+)["\']', re.I)
    api_pattern = re.compile(r'["\'](/api/[^"\']+)["\']', re.I)

    for path in seed_paths:
        status, html = fetch_page(host, port, path, secure)
        if status == 0:
            continue
            
        log(f"[*] Crawled {path} [HTTP {status}]", "\033[94m")
        discovered_endpoints.add(path)

        # Extract links
        for link in href_pattern.findall(html):
            if link.startswith("http"):
                p = urlparse(link)
                if p.hostname == host:
                    discovered_endpoints.add(p.path)
            elif link.startswith("/"):
                discovered_endpoints.add(link)

        # Extract form actions
        for action in action_pattern.findall(html):
            if action.startswith("/"):
                discovered_endpoints.add(action)

        # Extract hardcoded API strings in JS/HTML
        for api in api_pattern.findall(html):
            discovered_endpoints.add(api)

    # Filter out static assets (images, css, js files) to keep targets focused on logic/auth
    filtered = [
        ep for ep in discovered_endpoints 
        if not any(ep.endswith(ext) for ext in ['.png', '.jpg', '.jpeg', '.css', '.ico', '.svg', '.woff', '.png'])
    ]

    log(f"[+] Crawler complete. Discovered {len(filtered)} unique dynamic endpoints.", "\033[92m")
    return sorted(list(filtered))
