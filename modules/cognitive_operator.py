#!/usr/bin/env python3
"""
COGNITIVE_OPERATOR.PY — Autonomous Red-Team Reasoning & Tactical Decision Engine
Features:
- Framework stack trace & exception semantic analysis (Laravel/Symfony, Express, Django)
- Automated tactical pivoting (HTTP Method Override, Path Traversal calculation, Method Bypasses)
- Real-time decision output for autonomous engine feedback loops
"""
import json
import re

class CognitiveOperator:
    def __init__(self):
        self.memory_context = []

    def analyze_response(self, endpoint, status, headers, body):
        """
        Analyzes raw response telemetry and determines the exact tactical vulnerability 
        or framework misconfiguration exposed.
        """
        tactical_decision = {
            "endpoint": endpoint,
            "status": status,
            "framework_detected": None,
            "suggested_action": "CONTINUE_STANDARD_CRAWL",
            "adjusted_payload": None,
            "reasoning": ""
        }

        body_str = str(body) if body else ""
        lower_body = body_str.lower()

        # 1. Detect Laravel / Symfony Full Path Disclosures & Method Not Allowed Exceptions
        if "methodnotallowedhttpexception" in lower_body or status == 405:
            tactical_decision["framework_detected"] = "Laravel/Symfony"
            
            # Extract allowed methods from the exception message if available
            supported_match = re.search(r"Supported methods: ([A-Z, ]+)", body_str)
            allowed_methods = supported_match.group(1) if supported_match else "GET, HEAD"
            
            tactical_decision["suggested_action"] = "HTTP_METHOD_OVERRIDE"
            tactical_decision["reasoning"] = (
                f"Server threw MethodNotAllowedHttpException. Route exists but verb restricted. "
                f"Supported methods advertised: {allowed_methods}. Pivot to method override headers."
            )
            tactical_decision["adjusted_payload"] = {
                "override_headers": {"X-HTTP-Method-Override": "GET"},
                "target_method": "GET"
            }

        # 2. Detect Full Path Disclosures (FPD)
        elif "/www/wwwroot/" in body_str or "/var/www/" in body_str:
            tactical_decision["framework_detected"] = "Production Web Server / PHP"
            path_match = re.search(r"(/[a-zA-Z0-9_\-/]+/[a-zA-Z0-9_\-\.]+\b)", body_str)
            leaked_path = path_match.group(1) if path_match else "Unknown absolute path"
            
            tactical_decision["suggested_action"] = "LFI_ABSOLUTE_TARGETING"
            tactical_decision["reasoning"] = (
                f"Full Path Disclosure detected: {leaked_path}. "
                f"Use absolute path traversal vectors or target adjacent configuration files (.env)."
            )
            tactical_decision["adjusted_payload"] = {
                "leaked_base_path": leaked_path,
                "target_files": [".env", "config/database.php"]
            }

        # 3. Detect Database / NoSQL Exception Leaks
        elif any(err in lower_body for err in ["sql syntax", "pg_query", "mongoerror", "bsonerror"]):
            tactical_decision["suggested_action"] = "MUTATE_SQLI_NOSQLI"
            tactical_decision["reasoning"] = "Database exception signature matched in body. Server is vulnerable to injection parsing errors."
            tactical_decision["adjusted_payload"] = {
                "injection_vector": "Boolean/Error-based payload mutation required"
            }

        self.memory_context.append(tactical_decision)
        return tactical_decision
