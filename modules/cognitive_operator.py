import asyncio
import json
import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger("CognitiveOperator")

class CognitiveOperator:
    def __init__(self, target_url: str = "", max_budget: int = 150):
        self.attack_memory = {
            "target": target_url,
            "observations": [],          # Unusual behaviors / HTTP anomalies
            "hypotheses": [],            # Formulated vulnerability theories
            "confirmed_findings": [],    # Verified security failures / loopholes found
            "failed_tests": [],          # Exhausted, blocked, or error paths
            "available_modules": ["api_fuzzer", "db_assault", "live_login_verifier", "session_hijack"],
            "attack_chains": [],
            "risk_level": "Evaluating"
        }
        self.max_budget = max_budget
        self.requests_spent = 0

    def evaluate_and_execute(self, endpoint: str, status: int, headers: dict, body: str, transport=None, target_url=None) -> dict:
        """
        Primary hook called by engine.py during response classification.
        Evaluates real-time telemetry, spots loopholes, handles errors, and pivots tactics.
      ```python
        observation = {
            "endpoint": endpoint,
            "status": status,
            "category": self._categorize_response(status, body, headers),
            "body_snippet": body[:150] if body else ""
        }
        
        # 1. Log observation into state memory
        self.attack_memory["observations"].append(observation)

        # 2. Check for Loophole / Vulnerability Discovery
        if self._is_loophole_found(status, endpoint, body, headers):
            finding = {
                "endpoint": endpoint,
                "status": status,
                "evidence": f"Successfully triggered responsive state on {endpoint} (HTTP {status})",
                "action_taken": "Logged to confirmed_findings & escalated risk level."
            }
            self.attack_memory["confirmed_findings"].append(finding)
            self.attack_memory["risk_level"] = "HIGH - Exploitable Vector Identified"
            logger.info(f"[+] COGNITIVE INTELLIGENCE: Loophole confirmed at {endpoint}! Pivoting exploitation chain.")
            
            return {
                "success": True,
                "reasoning": f"Loophole capitalized at {endpoint}. Tactical pivot executed."
            }

        # 3. Check for Error / Block / Rate Limit (Adaptive Error Recovery)
        if status in [403, 429, 500, 502, 503] or not body:
            failure_record = {
                "endpoint": endpoint,
                "status": status,
                "reason": "Blocked, rate-limited, or server error encountered."
            }
            self.attack_memory["failed_tests"].append(failure_record)
            logger.warning(f"[!] COGNITIVE ERROR RECOVERY: Path {endpoint} returned status {status}. Pruning vector and shifting strategy.")
            
            # Quick strategize: Drop failed endpoint and select alternative module
            return {
                "success": False,
                "reasoning": f"Encountered defensive block/error ({status}) at {endpoint}. Vector isolated and bypassed."
            }

        return {"success": False, "reasoning": "Standard telemetry ingested."}

    def _categorize_response(self, status: int, body: str, headers: dict) -> str:
        body_lower = (body or "").lower()
        if status in [200, 201, 302] and any(k in body_lower for k in ["token", "session", "admin", "auth"]):
            return "auth_anomaly"
        elif "sql" in body_lower or "syntax" in body_lower:
            return "sql_error"
        elif status == 403:
            return "waf_or_forbidden"
        return "standard_http"

    def _is_loophole_found(self, status: int, endpoint: str, body: str, headers: dict) -> bool:
        body_lower = (body or "").lower()
        # Detect successful auth bypass, token leakage, or unauthenticated privileged access
        if status in [200, 201, 302]:
            if any(indicator in body_lower for l in ["access_token", "auth_token", "session_id", "\"role\":\"admin\""] for indicator in [l]):
                return True
            if "admin" in endpoint and "login" not in body_lower and len(body) > 50:
                return True
        return False

    async def analyze_observations(self, findings: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Distinguishes raw observations from actionable vulnerability hypotheses."""
        hypotheses = []
        for finding in findings:
            category = finding.get("category", "")
            endpoint = finding.get("endpoint", "")
            
            if "sql_error" in category or "database" in category:
                hypotheses.append({
                    "hypothesis": "Possible SQL injection or database information disclosure",
                    "target_endpoint": endpoint,
                    "recommended_module": "db_assault",
                    "confidence": "medium"
                })
            elif "auth_anomaly" in category or "token" in category:
                hypotheses.append({
                    "hypothesis": "Potential broken object-level authorization or missing auth guard",
                    "target_endpoint": endpoint,
                    "recommended_module": "api_fuzzer",
                    "confidence": "high"
                })
        return hypotheses

    async def rank_modules(self, hypotheses: List[Dict[str, Any]], available_modules: List[str]) -> List[Any]:
        """Ranks candidate testing actions based on hypothesis confidence and module relevance."""
        candidates = []
        for hyp in hypotheses:
            mod = hyp.get("recommended_module")
            if mod in available_modules:
                candidates.append({
                    "module": mod,
                    "target": hyp.get("target_endpoint"),
                    "hypothesis": hyp.get("hypothesis"),
                    "within_test_scope": True,
                    "within_resource_budget": self.requests_spent < self.max_budget,
                    "requires_irreversible_action": False
                })
        return candidates

    async def decide_next_action(self) -> Optional[Dict[str, Any]]:
        """Evaluates attack memory state to select and gate the next tactical module execution."""
        observations = self.attack_memory.get("observations", [])
        if not observations:
            return None

        hypotheses = await self.analyze_observations(observations)
        self.attack_memory["hypotheses"] = hypotheses

        candidates = await self.rank_modules(hypotheses, self.attack_memory["available_modules"])

        for candidate in candidates:
            if not candidate.get("within_test_scope", False):
                continue
            if not candidate.get("within_resource_budget", False):
                logger.warning("Resource budget exhausted. Halting automated chaining.")
                return None
            if candidate.get("requires_irreversible_action", False):
                continue

            return candidate

        return None
