#!/usr/bin/env python3
"""
RESPONSE_DIFF.PY v8.7 — Advanced Differential Analysis & False-Positive Elimination Engine (Elite Red Team Adversarial Edition)
Features:
- Robust structural tag hierarchy parsing and JSON key extraction
- Advanced Single Page Application (SPA) shell & soft-404 heuristic detection
- Fuzzy Jaccard token vocabulary overlap and structural similarity delta calculation
- High-concurrency safe baseline caching and comparative fingerprinting with clean error boundaries
"""
import hashlib
import json
import logging
from bs4 import BeautifulSoup
from typing import Dict, Any, Tuple

logger = logging.getLogger("BruteDog.ResponseDiff")

class ResponseFingerprinter:
    """
    Performs structural, cryptographic, and fuzzy-delta differential analysis on HTTP responses 
    to filter out false positives (soft 404s, generic SPA login shells, and custom catch-alls).
    """
    def __init__(self, similarity_threshold: float = 0.85):
        self.similarity_threshold = similarity_threshold
        # Store baseline fingerprints keyed by error/status type (e.g., 'soft_404', 'spa_shell_403')
        self.baselines: Dict[str, Dict[str, Any]] = {}
        logger.info("[+] Initialized ResponseFingerprinter engine with advanced fuzzy delta capability (v8.7).")

    def capture_baseline(self, label: str, status_code: int, text_content: str, headers: dict) -> None:
        """Capture a known baseline response (e.g., a deliberate 403 SPA redirect or unauthenticated shell)."""
        fingerprint = self._generate_fingerprint(status_code, text_content, headers)
        self.baselines[label] = fingerprint
        logger.debug(f"[+] Captured baseline for [{label}] -> Hash: {fingerprint['body_hash'][:8]} (Len: {fingerprint['content_length']})")

    def _generate_fingerprint(self, status_code: int, text_content: str, headers: dict) -> Dict[str, Any]:
        """Extract structural features, semantic token density, and layout signatures from body and headers."""
        content_length = len(text_content) if text_content else 0
        
        # Hash full body content safely
        body_hash = hashlib.sha256((text_content or "").encode('utf-8', errors='ignore')).hexdigest()

        structure_keys = []
        is_spa_shell = False
        text_density_tokens = set()

        try:
            content_type = headers.get("content-type", "").lower() if headers else ""
            if "application/json" in content_type:
                data = json.loads(text_content or "{}")
                structure_keys = self._extract_json_keys(data)
            else:
                soup = BeautifulSoup(text_content or "", 'html.parser')
                # Collect tag hierarchy signature (up to 150 elements for deep SPA layouts)
                structure_keys = [tag.name for tag in soup.find_all(True)[:150]]
                
                # Heuristic: Detect generic Single Page Application (SPA) empty wrappers / root nodes
                root_divs = soup.find_all(id=lambda x: x and x in ['root', 'app', '__next', '__nuxt', 'viewport'])
                body_text = soup.get_text(strip=True)
                
                lower_text = body_text.lower()
                if (root_divs and len(body_text) < 450) or any(term in lower_text for term in ["loading...", "please wait", "javascript is required", "enable javascript"]):
                    is_spa_shell = True

                # Extract token vocabulary for fuzzy Jaccard comparison (filtering out short words)
                text_density_tokens = {word.lower() for word in body_text.split() if len(word) > 3}
        except Exception as e:
            logger.debug(f"[-] Error parsing response structure: {e}")

        return {
            "status_code": status_code,
            "content_length": content_length,
            "body_hash": body_hash,
            "structure_keys": structure_keys,
            "is_spa_shell": is_spa_shell,
            "text_density_tokens": text_density_tokens
        }

    def _extract_json_keys(self, data: Any, prefix: str = "") -> list:
        """Recursively extract JSON keys to fingerprint payload structure."""
        keys = []
        try:
            if isinstance(data, dict):
                for k, v in data.items():
                    full_key = f"{prefix}.{k}" if prefix else k
                    keys.append(full_key)
                    if isinstance(v, (dict, list)):
                        keys.extend(self._extract_json_keys(v, full_key))
            elif isinstance(data, list) and data and isinstance(data[0], dict):
                keys.extend(self._extract_json_keys(data[0], f"{prefix}[]"))
        except Exception:
            pass
        return keys

    def _calculate_jaccard_similarity(self, set1: set, set2: set) -> float:
        """Calculate token vocabulary overlap to catch near-identical SPA error pages."""
        if not set1 or not set2:
            return 0.0
        intersection = len(set1.intersection(set2))
        union = len(set1.union(set2))
        return intersection / union if union > 0 else 0.0

    def is_false_positive(self, status_code: int, text_content: str, headers: dict) -> Tuple[bool, str]:
        """
        Compare an incoming response against stored baselines and known SPA soft-error fingerprints.
        Returns (is_fp: bool, reason: str).
        """
        try:
            current_fp = self._generate_fingerprint(status_code, text_content, headers)

            # Rule 1: Catch generic client-side SPA shells served with HTTP 200/403/404
            if current_fp["is_spa_shell"]:
                return True, f"Detected generic SPA shell wrapper or placeholder (Status: {status_code})"

            # Rule 2: Compare against captured baselines with fuzzy structural & token delta
            for label, baseline in self.baselines.items():
                if current_fp["status_code"] == baseline["status_code"]:
                    if current_fp["body_hash"] == baseline["body_hash"]:
                        return True, f"Exact match with baseline fingerprint [{label}]"
                    
                    # Calculate structural tag match ratio
                    common_tags = len(set(current_fp["structure_keys"]).intersection(set(baseline["structure_keys"])))
                    max_tags = max(len(current_fp["structure_keys"]), len(baseline["structure_keys"]), 1)
                    tag_similarity = common_tags / max_tags

                    # Calculate text token Jaccard similarity
                    token_similarity = self._calculate_jaccard_similarity(
                        current_fp["text_density_tokens"], 
                        baseline["text_density_tokens"]
                    )

                    if tag_similarity >= self.similarity_threshold or token_similarity >= self.similarity_threshold:
                        return True, f"Fuzzy similarity match with baseline [{label}] (Tag Similarity: {tag_similarity:.2f}, Token Similarity: {token_similarity:.2f})"
        except Exception as exc:
            logger.debug(f"[-] Error in is_false_positive evaluation: {exc}")

        return False, "Response represents unique logical variance"
