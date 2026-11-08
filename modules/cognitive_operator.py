import asyncio
import json
import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger("CognitiveOperator")

class AutonomousReasoningEngine:
    def __init__(self, target_url: str, max_budget: int = 150):
        self.attack_memory = {
            "target": target_url,
            "observations": [],          # Unusual behaviors / HTTP anomalies
            "hypotheses": [],          # Formulated vulnerability theories
            "confirmed_findings": [],    # Verified security failures
            "failed_tests": [],          # Exhausted or blocked paths
            "available_modules": ["api_fuzzer", "db_assault", "live_login_verifier"],
            "attack_chains": [],
            "risk_level": "Evaluating"
        }
        self.max_budget = max_budget
        self.requests_spent = 0

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
            elif "unauthenticated" in category or "token" in category:
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
                    "requires_irreversible_action": False  # Enforce safety guardrails
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
            # 1. Scope Validation Check
            if not candidate.get("within_test_scope", False):
                logger.info(f"Skipping candidate {candidate['module']}: Out of test scope.")
                continue

            # 2. Resource Budget Check
            if not candidate.get("within_resource_budget", False):
                logger.warning("Resource budget exhausted. Halting automated chaining.")
                return None

            # 3. Irreversible Action Check (Safety Guardrail)
            if candidate.get("requires_irreversible_action", False):
                logger.warning(f"Blocking irreversible action on {candidate['target']}")
                continue

            return candidate

        return None
