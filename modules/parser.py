import http.client
import ssl
import urllib.parse
import re
import sys
import time

# Global SSL context
_ssl_context = ssl.create_default_context()
_ssl_context.check_hostname = False
_ssl_context.verify_mode = ssl.CERT_NONE

async def parse_target_source(host):
    """
    Performs real-time source code scraping, security header analysis,
    and regex-based secret/vulnerability extraction.
    """
    print(f"\n\033[95m[***] DEPLOYING DOM & SOURCE-CODE PARSER V1.0 [***]\033[0m")
    print(f"\033[90m[TARGET] Fetching raw HTML, headers, and assets from https://{host}...\033[0m\n")
    
    findings = {
        "headers_missing": [],
        "exposed_secrets": [],
        "hidden_endpoints": [],
        "insecure_forms": []
    }

    try:
        # Fetch root HTML and headers over HTTPS
        conn = http.client.HTTPSConnection(host, 443, context=_ssl_context, timeout=5.0)
        conn.request("GET", "/", headers={"User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15"})
        resp = conn.getresponse()
        html_body = resp.read().decode(errors="ignore")
        headers = dict(resp.getheaders())
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
            if header in headers:
                print(f"   \033[92m[SECURE] {header}: {headers[header][:50]}\033[0m")
            else:
                print(f"   \033[91m[VULN] Missing Security Header -> {header}\033[0m")
                findings["headers_missing"].append(header)

        # 2. Regex-Based Secret & API Key Extraction from Source Code
        print(f"\n\033[36m[*] Scanning source code and JavaScript payloads for exposed secrets...\033[0m")
        
        secret_patterns = {
            "JWT Token": r"eyJ[A-Za-z0-9-_=]+\.[A-Za-z0-9-_=]+\.?[A-Za-z0-9-_.+/=]*",
            "Google API Key": r"AIza[0-9A-Za-z-_]{35}",
            "AWS Access Key": r"AKIA[0-9A-Z]{16}",
            "Firebase URL": r"https://[a-z0-9-]+\.firebaseio\.com",
            "Private Key Block": r"-----BEGIN PRIVATE KEY-----",
            "Generic Bearer Token": r"bearer\s+[a-zA-Z0-9_\-\.]+"
        }

        for secret_name, pattern in secret_patterns.items():
            matches = re.findall(pattern, html_body, re.IGNORECASE)
            if matches:
                print(f"   \033[91m[!] CRITICAL: Exposed {secret_name} detected in source! Matches: {len(matches)}\033[0m")
                findings["exposed_secrets"].append({"type": secret_name, "count": len(matches)})
            else:
                sys.stdout.write(f"\r\033[K\033[90m[-] Checked pattern: {secret_name} -> Clean\033[0m")
                sys.stdout.flush()
        print()

        # 3. Hidden Endpoint & API Route Extraction
        print(f"\n\033[36m[*] Extracting embedded links, API routes, and comment flags...\033[0m")
        
        # Extract href attributes, form actions, and script sources
        links = re.findall(r'(?:href|src|action)=["\']([^"\']+)["\']', html_body, re.IGNORECASE)
        internal_endpoints = set()
        
        for link in links:
            if link.startswith("/") or "api" in link or "auth" in link or "admin" in link:
                internal_endpoints.add(link)

        if internal_endpoints:
            print(f"   \033[93m[+] Discovered {len(internal_endpoints)} internal routes/endpoints in DOM:\033[0m")
            for ep in list(internal_endpoints)[:10]: # Print top 10
                print(f"       -> {ep}")
                findings["hidden_endpoints"].append(ep)
        else:
            print("   \033[90m[-] No anomalous hidden endpoints found in DOM tags.\033[0m")

        # 4. Insecure Form Inspection
        forms = re.findall(r'<form[^>]*>', html_body, re.IGNORECASE)
        for form in forms:
            if "method=\"get\"" in form.lower() or 'method=\'get\'' in form.lower():
                print(f"   \033[91m[VULN] Insecure HTTP GET Form Action detected (Credentials may leak in URL history)! -> {form}\033[0m")
                findings["insecure_forms"].append(form)

        print(f"\n\033[92m[*] DOM and Source-Code analysis completed successfully.\033[0m\n")
        return findings

    except Exception as e:
        print(f"\n\033[91m[!] Error parsing target source code: {e}\033[0m")
        return findings
