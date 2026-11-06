import http.client
import ssl
import urllib.parse
import re
import sys
import time
import json
import os

_ssl_context = ssl.create_default_context()
_ssl_context.check_hostname = False
_ssl_context.verify_mode = ssl.CERT_NONE

class LivePlaintextIntelligenceParser:
    """
    Zero-Lag, Live Terminal Intelligence & Credential Extractor:
    - Instantly outputs raw plain-text credentials, API keys, and tokens straight to the screen.
    - Eliminates hidden file dumps and external email dependencies.
    """
    def __init__(self, watch_directory="reports/"):
        self.watch_directory = watch_directory
        self.regex_patterns = {
            "Plaintext Credential / Password": r"(?:pass|password|pwd|secret|auth|token)['\"]?\s*[:=]\s*['\"]([^'\"]{4,64})['\"]",
            "API Key / Token": r"(?:api[_-]?key|access[_-]?token|bearer)['\"]?\s*[:=]\s*['\"]([a-zA-Z0-9_\-]{16,64})['\"]",
            "Crypto Seed / Mnemonic": r"\b(?:[a-z]{4,8}\s){11,23}[a-z]{4,8}\b",
            "Email Address": r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+",
            "AWS / Cloud Key": r"AKIA[0-9A-Z]{16}",
            "Google API Key": r"AIza[0-9A-Za-z-_]{35}"
        }

    def scan_and_display_live(self, text, source_identifier):
        """Scans text and aggressively dumps live plain-text findings to the terminal screen."""
        found_count = 0
        for category, pattern in self.regex_patterns.items():
            matches = re.findall(pattern, text, re.IGNORECASE)
            if matches:
                for match in set(matches):
                    found_count += 1
                    # Immediate, high-contrast red-team plain text terminal exposure
                    sys.stdout.write(f"\n\033[1m\033[91m[***] LIVE INTEL EXPOSED [{category.upper()}] [***]\033[0m\n")
                    sys.stdout.write(f"  ├── Source   : {source_identifier}\n")
                    sys.stdout.write(f"  └── Payload  : \033[92m{match}\033[0m\n")
                    sys.stdout.flush()
        return found_count

    def process_live_stream(self):
        print(f"\n\033[95m[***] ENGAGING LIVE TERMINAL INTELLIGENCE STREAM [{self.watch_directory}] [***]\033[0m")
        total_exposed = 0
        
        if not os.path.exists(self.watch_directory):
            print(f" \033[90m[-] Watch directory {self.watch_directory} is clear.\033[0m")
            return 0

        for root, dirs, files in os.walk(self.watch_directory):
            for file in files:
                file_path = os.path.join(root, file)
                try:
                    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                        content = f.read()
                    total_exposed += self.scan_and_display_live(content, file_path)
                except Exception:
                    pass

        print(f"\n\033[92m[+] Live intelligence inspection complete. Total exposed secrets streamed: {total_exposed}\033[0m")
        return total_exposed

async def parse_target_source(host):
    """
    Performs live DOM scraping, security header inspection, and 
    instantaneous plain-text credential dumping directly to the terminal.
    """
    print(f"\n\033[95m[***] DEPLOYING LIVE DOM & PLAIN-TEXT CREDENTIAL EXTRACTOR [***]\033[0m")
    print(f"\033[90m[TARGET] Stripping DOM headers and pulling raw intelligence from https://{host}...\033[0m\n")

    try:
        conn = http.client.HTTPSConnection(host, 443, context=_ssl_context, timeout=5.0)
        conn.request("GET", "/", headers={"User-Agent": "Mozilla/5.0 (BruteDog Elite Operator)"})
        resp = conn.getresponse()
        html_body = resp.read().decode(errors="ignore")
        headers = dict(resp.getheaders())
        resp_raw_headers = resp.msg._headers
        conn.close()

        print(f" \033[92m[+] Pulled {len(html_body)} bytes of raw DOM source code.\033[0m")

        # Live extraction of JWTs and cookies straight to screen
        raw_cookies = [val for key, val in resp_raw_headers if key.lower() == 'set-cookie']
        jwt_pattern = r'eyJ[A-Za-z0-9-_=]+\.[A-Za-z0-9-_=]+\.?[A-Za-z0-9-_.+/=]*'
        jwts = re.findall(jwt_pattern, html_body, re.IGNORECASE)

        if raw_cookies or jwts:
            print(f"\n\033[1m\033[91m[+++] LIVE SESSION ARTIFACTS INTERCEPTED [+++]\033[0m")
            for cookie in raw_cookies:
                print(f"  └── Cookie : \033[92m{cookie}\033[0m")
            for jwt in jwts:
                print(f"  └── JWT    : \033[92m{jwt}\033[0m")

        # Execute live file and artifact stream
        parser_engine = LivePlaintextIntelligenceParser()
        parser_engine.process_live_stream()

        print(f"\n\033[92m[*] Live terminal intelligence stream finished successfully.\033[0m\n")
        return {"status": "success"}

    except Exception as e:
        print(f"\n\033[91m[!] Error during live target parsing: {e}\033[0m")
        return {"status": "error", "message": str(e)}
