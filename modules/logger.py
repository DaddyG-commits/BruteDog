import logging
import sys

def setup_logger(log_to_file=False, log_dir="logs"):
    """
    Zero-Lag Live Terminal Logger:
    - Eliminates persistent log files to maintain elite stealth and zero disk footprint.
    - Streams telemetry and audit events instantly in high-contrast plain text to stdout.
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

    return logger
