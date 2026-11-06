import http.client
import ssl
import urllib.parse
import re
import sys
import time
import json
import os

# Global SSL context
_ssl_context = ssl.create_default_context()
_ssl_context.check_hostname = False
_ssl_context.verify_mode = ssl.CERT_NONE

async def parse_target_source(host):
    """
    Performs real-time source code scraping, security header analysis,
    regex-based secret extraction, and automated session cookie/JWT harvesting.
    """
    print(f"\n\033[95m[***] DEPLOYING DOM & SESSION HIJACKING PARSER V2.0 [***]\033[0m")
    print(f"\033[90m[TARGET] Fetching raw HTML, headers, and cookies from https://{host}...\033[0m\n")
    
    findings = {
        "headers_missing": [],
        "exposed_secrets": [],
        "hidden_endpoints": [],
        "insecure_forms": [],
        "harvested_sessions": []
    }

    try:
        # Fetch root HTML and headers over HTTPS
        conn = http.client.HTTPSConnection(host, 443, context=_ssl_context, timeout=5.0)
        conn.request("GET", "/", headers={"User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15"})
        resp = conn.getresponse()
        html_body = resp.read().decode(errors="ignore")
        headers = dict(resp.getheaders())
        resp_raw_headers = resp.msg._headers  # Captures multiple Set-Cookie headers if present
        conn.close()

        print(f" \033[92m[+] Successfully pulled {len(html_body)} bytes of raw DOM source code.\033[0m")

        # 1. Security Headers Audit
        security_headers = [
            "Strict-Transport-Security",
            "Content-Security-Policy",
            "X-Frame-Options",
            "X-Content-Type-Options",
            "X-XSS-Protection"
        ]
        
        print(f"\n\033[36m[*] Auditing HTTP Response Headers...\033[0m")
        for header in security_headers:
            if any(header.lower() == k.lower() for k in headers.keys()):
                print(f"   \033[92m[SECURE] {header}\033[0m")
            else:
                print(f"   \033[91m[VULN] Missing Security Header -> {header}\033[0m")
                findings["headers_missing"].append(header)

        # 2. Automated Session Cookie & JWT Exfiltration
        print(f"\n\033[36m[*] Extracting session cookies, JWT tokens, and authorization artifacts...\033[0m")
        
        # Extract all Set-Cookie headers
        raw_cookies = [val for key, val in resp_raw_headers if key.lower() == 'set-cookie']
        
        # Regex patterns for secrets & tokens
        jwt_pattern = r'eyJ[A-Za-z0-9-_=]+\.[A-Za-z0-9-_=]+\.?[A-Za-z0-9-_.+/=]*'
        api_key_pattern = r'(?:api[_-]?key|secret[_-]?token|bearer)\s*[:=]\s*["\']([a-zA-Z0-9_\-]{16,40})["\']'
        
        jwts = re.findall(jwt_pattern, html_body, re.IGNORECASE)
        api_keys = re.findall(api_key_pattern, html_body, re.IGNORECASE)

        session_payload = {
            "target": host,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "set_cookies": raw_cookies,
            "jwts": jwts,
            "api_keys": api_keys
        }

        if raw_cookies or jwts:
            print(f"   \033[92m[+++] CRITICAL SESSION INTELLIGENCE FOUND!\033[0m")
            if raw_cookies:
                print(f"       -> Harvested {len(raw_cookies)} Set-Cookie strings.")
            if jwts:
                print(f"       -> Harvested {len(jwts)} JWT tokens.")
            
            # Serialize directly to reports/sessions/ for instant session cloning
            os.makedirs("reports/sessions", exist_ok=True)
            session_file = f"reports/sessions/session_{host.replace('.', '_')}.json"
            with open(session_file, "w") as f:
                json.dump(session_payload, f, indent=4)
            print(f"       -> Serialized to: {session_file}")
            findings["harvested_sessions"].append(session_file)
        else:
            print(f"   \033[90m[-] No active session tokens or cookies exposed in response headers.\033[0m")

        # 3. Regex-Based Secret & API Key Extraction from Source Code
        secret_patterns = {
            "Google API Key": r"AIza[0-9A-Za-z-_]{35}",
            "AWS Access Key": r"AKIA[0-9A-Z]{16}",
            "Firebase URL": r"https://[a-z0-9-]+\.firebaseio\.com",
            "Private Key Block": r"-----BEGIN PRIVATE KEY-----",
            "Generic Bearer Token": r"bearer\s+[a-zA-Z0-9_\-\.]+"
        }

        for secret_name, pattern in secret_patterns.items():
            matches = re.findall(pattern, html_body, re.IGNORECASE)
            if matches:
                print(f"   \033[91m[!] Exposed {secret_name} detected in DOM source! Matches: {len(matches)}\033[0m")
                findings["exposed_secrets"].append({"type": secret_name, "count": len(matches)})

        # 4. Hidden Endpoint & API Route Extraction
        links = re.findall(r'(?:href|src|action)=["\']([^"\']+)["\']', html_body, re.IGNORECASE)
        internal_endpoints = set()
        
        for link in links:
            if link.startswith("/") or "api" in link or "auth" in link or "admin" in link:
                internal_endpoints.add(link)

        if internal_endpoints:
            print(f"   \033[93m[+] Discovered {len(internal_endpoints)} internal routes/endpoints in DOM.\033[0m")
            for ep in list(internal_endpoints)[:10]:
                findings["hidden_endpoints"].append(ep)

        # 5. Insecure Form Inspection
        forms = re.findall(r'<form[^>]*>', html_body, re.IGNORECASE)
        for form in forms:
            if "method=\"get\"" in form.lower() or 'method=\'get\'' in form.lower():
                print(f"   \033[91m[VULN] Insecure HTTP GET Form Action detected -> {form}\033[0m")
                findings["insecure_forms"].append(form)

        print(f"\n\033[92m[*] DOM and Session Hijacking analysis completed successfully.\033[0m\n")
        return findings

    except Exception as e:
        print(f"\n\033[91m[!] Error parsing target source code: {e}\033[0m")
        return findings

