#!/usr/bin/env python3
"""
LOGGER.PY v8.6 — Zero-Lag Live Terminal & Audit Event Logger (Elite Red Team Adversarial Edition)
Features:
- High-contrast Cyberpunk ANSI structured console streaming (`stdout`)
- Optional immutable file persistence (`loot_output/`) for competition submission reports
- Singleton handler duplication prevention and zero-lag asynchronous safety
"""
import logging
import sys
import os
from pathlib import Path

LOOT_DIR = "loot_output"

def setup_logger(log_to_file=False, log_dir=LOOT_DIR):
    """
    Zero-Lag Live Terminal & Audit Logger:
    - Eliminates persistent log files by default to maintain elite stealth and zero disk footprint.
    - Optionally persists structured audit trails to loot_output/ when explicit file logging is requested.
    """
    logger = logging.getLogger("AsyncReconEngine")
    logger.setLevel(logging.INFO)

    # Prevent duplicate handlers if called multiple times
    if logger.handlers:
        return logger

    # High-Contrast Terminal Console Handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    
    # Cyberpunk structured color formatter
    class CyberFormatter(logging.Formatter):
        MATRIX_GREEN = "\033[38;5;46m"
        RED = "\033[91m"
        YELLOW = "\033[93m"
        RESET = "\033[0m"

        def format(self, record):
            color = self.MATRIX_GREEN
            if record.levelname == "WARNING":
                color = self.YELLOW
            elif record.levelname in ["ERROR", "CRITICAL"]:
                color = self.RED
            
            timestamp = self.formatTime(record, self.datefmt)
            return f"{color}[{timestamp}] [{record.levelname}] {record.getMessage()}{self.RESET}"

    console_format = CyberFormatter(datefmt="%H:%M:%S")
    console_handler.setFormatter(console_format)
    logger.addHandler(console_handler)

    # Optional File Logging Handler for Competition Reports / Immutable Loot
    if log_to_file:
        os.makedirs(log_dir, exist_ok=True)
        file_path = Path(log_dir) / "recon_audit_trail.log"
        file_handler = logging.FileHandler(file_path, encoding="utf-8")
        file_handler.setLevel(logging.INFO)
        file_formatter = logging.Formatter("[%(asctime)s] [%(levelname)s] %(message)s", datefmt="%Y-%m-%d %H:%M:%S")
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)

    return logger
