#!/usr/bin/env python3
"""
LOGGER.PY v8.6 — Zero-Lag Live Terminal & Audit Event Logger
"""
import logging
import os
from pathlib import Path
import sys
import threading

LOOT_DIR = "loot_output"
_LOGGER_LOCK = threading.Lock()


class CyberFormatter(logging.Formatter):
    MATRIX_GREEN = "\033[38;5;46m"
    RED = "\033[91m"
    YELLOW = "\033[93m"
    RESET = "\033[0m"

    def format(self, record):
        color = self.MATRIX_GREEN
        if record.levelno >= logging.ERROR:
            color = self.RED
        elif record.levelno >= logging.WARNING:
            color = self.YELLOW

        timestamp = self.formatTime(record, self.datefmt)
        return f"{color}[{timestamp}] [{record.levelname}] {record.getMessage()}{self.RESET}"


def _resolve_log_level() -> int:
    raw = os.environ.get("BRUTEDOG_LOG_LEVEL", "INFO").strip().upper()
    return getattr(logging, raw, logging.INFO)


def setup_logger(log_to_file=False, log_dir=LOOT_DIR):
    """
    Zero-Lag Live Terminal & Audit Logger:
    - Streams structured output to stdout without persistent log files by default.
    - Optionally persists structured audit trails to loot_output/ when requested.
    """
    level = _resolve_log_level()

    with _LOGGER_LOCK:
        logger = logging.getLogger("AsyncReconEngine")
        logger.setLevel(level)
        logger.propagate = False

        if logger.handlers:
            for h in logger.handlers:
                h.setLevel(level)
            return logger

        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(level)
        console_handler.setFormatter(CyberFormatter(datefmt="%H:%M:%S"))
        logger.addHandler(console_handler)

        if log_to_file:
            target_dir = Path(log_dir)
            target_dir.mkdir(parents=True, exist_ok=True)
            file_path = target_dir / "recon_audit_trail.log"
            file_handler = logging.FileHandler(file_path, encoding="utf-8")
            file_handler.setLevel(level)
            file_formatter = logging.Formatter(
                "[%(asctime)s] [%(levelname)s] %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S",
            )
            file_handler.setFormatter(file_formatter)
            logger.addHandler(file_handler)

    return logger
