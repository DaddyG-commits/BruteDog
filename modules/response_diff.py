#!/usr/bin/env python3
"""
RESPONSE_DIFF.PY v8.8 — Differential Analysis & False-Positive Filter Engine
"""
import hashlib
import json
import logging
import threading
from typing import Any, Dict, Tuple

from bs4 import BeautifulSoup

logger = logging.getLogger("BruteDog.ResponseDiff")

CHALLENGE_MARKERS = (
    "just a moment...",
    "checking your browser before accessing",
    "attention required! | cloudflare",
    "cf-browser-verification",
    "ddos-guard",
    "__cf_chl_opt",
    "enable cookies to continue",
    "access denied | cloudflare",
)

SPA_SHELL_MARKERS = (
    "loading...",
    "please wait",
    "javascript is required",
    "enable javascript",
    "you need to enable javascript to run this app",
)


class ResponseFingerprinter:
    """Compares responses against baselines and filters challenge/SPA/soft-404 noise."""

    def __init__(self, similarity_threshold: float = 0.85):
        self.similarity_threshold = float(similarity_threshold)
        self.baselines: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.Lock()

    @staticmethod
    def _normalize_headers(headers: Any) -> Dict[str, str]:
        if not isinstance(headers, dict):
            return {}
        return {str(k).lower(): str(v) for k, v in headers.items()}

    def capture_baseline(self, label: str, status_code: int, text_content: str, headers: dict) -> None:
        """Stores a baseline response fingerprint under a given label."""
        fingerprint = self._generate_fingerprint(status_code, text_content, headers)
        with self._lock:
            self.baselines[str(label)] = fingerprint

    def _generate_fingerprint(self, status_code: int, text_content: str, headers: dict) -> Dict[str, Any]:
        body_text = text_content if isinstance(text_content, str) else str(text_content or "")
        norm_headers = self._normalize_headers(headers)
        content_type = norm_headers.get("content-type", "").lower()

        content_length = len(body_text)
        body_hash = hashlib.sha256(body_text.encode("utf-8", errors="ignore")).hexdigest()

        structure_keys = []
        is_spa_shell = False
        is_challenge_page = False
        text_density_tokens = set()

        lower_raw = body_text.lower()
        if "cf-mitigated" in norm_headers or any(marker in lower_raw for marker in CHALLENGE_MARKERS):
            is_challenge_page = True

        try:
            if "application/json" in content_type or body_text.lstrip().startswith(("{", "[")):
                data = json.loads(body_text or "{}")
                structure_keys = self._extract_json_keys(data)
            else:
                soup = BeautifulSoup(body_text, "html.parser")
                structure_keys = [tag.name for tag in soup.find_all(True)[:150]]

                root_nodes = soup.find_all(
                    id=lambda x: x and str(x) in ("root", "app", "__next", "__nuxt", "viewport")
                )
                visible_text = soup.get_text(" ", strip=True)
                lower_visible = visible_text.lower()

                if (root_nodes and len(visible_text) < 450) or any(
                    term in lower_visible for term in SPA_SHELL_MARKERS
                ):
                    is_spa_shell = True

                text_density_tokens = {
                    word.strip(".,:;!?()[]{}\"'").lower()
                    for word in visible_text.split()
                    if len(word.strip(".,:;!?()[]{}\"'")) > 3
                }
        except Exception:
            pass

        return {
            "status_code": int(status_code or 0),
            "content_length": content_length,
            "body_hash": body_hash,
            "structure_keys": structure_keys,
            "is_spa_shell": is_spa_shell,
            "is_challenge_page": is_challenge_page,
            "text_density_tokens": text_density_tokens,
        }

    def _extract_json_keys(self, data: Any, prefix: str = "") -> list:
        keys = []
        try:
            if isinstance(data, dict):
                for k, v in data.items():
                    full_key = f"{prefix}.{k}" if prefix else str(k)
                    keys.append(full_key)
                    if isinstance(v, (dict, list)):
                        keys.extend(self._extract_json_keys(v, full_key))
            elif isinstance(data, list) and data and isinstance(data[0], dict):
                keys.extend(self._extract_json_keys(data[0], f"{prefix}[]"))
        except Exception:
            pass
        return keys

    @staticmethod
    def _calculate_jaccard_similarity(set1: set, set2: set) -> float:
        if not set1 or not set2:
            return 0.0
        intersection = len(set1.intersection(set2))
        union = len(set1.union(set2))
        return intersection / union if union > 0 else 0.0

    def is_false_positive(self, status_code: int, text_content: str, headers: dict) -> Tuple[bool, str]:
        """
        Evaluates whether a response is a challenge page, SPA shell, soft/empty response,
        or matches an established baseline fingerprint. Returns (is_fp, reason).
        """
        try:
            code = int(status_code or 0)
            if code == 0:
                return True, "Zero/transport error response"

            current_fp = self._generate_fingerprint(code, text_content, headers)

            if current_fp["is_challenge_page"]:
                return True, f"Detected WAF/bot challenge response (Status: {code})"

            if current_fp["is_spa_shell"]:
                return True, f"Detected generic SPA shell or placeholder (Status: {code})"

            if code in (404, 410) or (code == 200 and current_fp["content_length"] == 0):
                return True, f"Non-actionable or empty response (Status: {code})"

            with self._lock:
                baselines_snapshot = list(self.baselines.items())

            for label, baseline in baselines_snapshot:
                if current_fp["status_code"] == baseline["status_code"]:
                    if current_fp["body_hash"] == baseline["body_hash"]:
                        return True, f"Exact match with baseline [{label}]"

                    common_tags = len(
                        set(current_fp["structure_keys"]).intersection(set(baseline["structure_keys"]))
                    )
                    max_tags = max(len(current_fp["structure_keys"]), len(baseline["structure_keys"]), 1)
                    tag_similarity = common_tags / max_tags

                    token_similarity = self._calculate_jaccard_similarity(
                        current_fp["text_density_tokens"],
                        baseline["text_density_tokens"],
                    )

                    if tag_similarity >= self.similarity_threshold or token_similarity >= self.similarity_threshold:
                        return (
                            True,
                            f"Similarity match with baseline [{label}] "
                            f"(tag={tag_similarity:.2f}, token={token_similarity:.2f})",
                        )
        except Exception as exc:
            logger.debug(f"False-positive check fallback: {exc}")

        return False, "Response represents unique logical variance"
