import hashlib
import json
import logging
from bs4 import BeautifulSoup
from typing import Dict, Any, Tuple

logger = logging.getLogger("BruteDog.ResponseDiff")

class ResponseFingerprinter:
    """
    Performs structural and cryptographic differential analysis on HTTP responses 
    to filter out false positives (soft 404s, generic error pages, custom catch-alls).
    """
    def __init__(self, similarity_threshold: float = 0.90):
        self.similarity_threshold = similarity_threshold
        # Store baseline fingerprints keyed by error/status type (e.g., 'soft_404', 'default_error')
        self.baselines: Dict[str, Dict[str, Any]] = {}
        logger.info("[+] Initialized ResponseFingerprinter engine.")

    def capture_baseline(self, label: str, status_code: int, text_content: str, headers: dict) -> None:
        """Capture a known baseline response (e.g., a deliberate 404 or unauthenticated landing page)."""
        fingerprint = self._generate_fingerprint(status_code, text_content, headers)
        self.baselines[label] = fingerprint
        logger.debug(f"[+] Captured baseline for [{label}] -> Hash: {fingerprint['body_hash'][:8]} (Len: {fingerprint['content_length']})")

    def _generate_fingerprint(self, status_code: int, text_content: str, headers: dict) -> Dict[str, Any]:
        """Extract structural features from a response body and headers."""
        content_length = len(text_content)
        
        # Strip dynamic tokens, timestamps, or script hashes if needed, then hash
        body_hash = hashlib.sha256(text_content.encode('utf-8', errors='ignore')).hexdigest()

        # Parse structure using BeautifulSoup for HTML or json for API responses
        structure_keys = []
        try:
            if headers.get("content-type", "").startswith("application/json"):
                data = json.loads(text_content)
                structure_keys = self._extract_json_keys(data)
            else:
                soup = BeautifulSoup(text_content, 'html.parser')
                # Collect tag hierarchy signature
                structure_keys = [tag.name for tag in soup.find_all(True)[:50]]
        except Exception as e:
            logger.debug(f"[-] Error parsing response structure: {e}")

        return {
            "status_code": status_code,
            "content_length": content_length,
            "body_hash": body_hash,
            "structure_keys": structure_keys
        }

    def _extract_json_keys(self, data: Any, prefix: str = "") -> list:
        """Recursively extract JSON keys to fingerprint payload structure."""
        keys = []
        if isinstance(data, dict):
            for k, v in data.items():
                full_key = f"{prefix}.{k}" if prefix else k
                keys.append(full_key)
                if isinstance(v, (dict, list)):
                    keys.extend(self._extract_json_keys(v, full_key))
        elif isinstance(data, list) and data and isinstance(data[0], dict):
            keys.extend(self._extract_json_keys(data[0], f"{prefix}[]"))
        return keys

    def is_false_positive(self, status_code: int, text_content: str, headers: dict) -> Tuple[bool, str]:
        """
        Compare an incoming response against stored baselines (like soft 404s).
        Returns (is_fp: bool, reason: str).
        """
        current_fp = self._generate_fingerprint(status_code, text_content, headers)

        # Rule 1: Standard negative status gates
        if status_code in [404, 403, 500, 502, 503]:
            return True, f"Standard error status code: {status_code}"

        # Rule 2: Compare against captured soft-404 or error baselines
        for label, baseline in self.baselines.items():
            if current_fp["status_code"] == baseline["status_code"]:
                if current_fp["body_hash"] == baseline["body_hash"]:
                    return True, f"Exact match with baseline fingerprint [{label}]"
                
                # Check for near-identical content length (within 2% variance on same status)
                len_diff = abs(current_fp["content_length"] - baseline["content_length"])
                if baseline["content_length"] > 0 and (len_diff / baseline["content_length"]) < 0.02:
                    if current_fp["structure_keys"] == baseline["structure_keys"]:
                        return True, f"Structural similarity match with baseline [{label}] (Soft 404)"

        return False, "Response represents unique logical variance"
