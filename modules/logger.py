import logging
import os
from datetime import datetime

def setup_logger(log_to_file=True, log_dir="logs"):
    """
    Configures and returns a structured logger for telemetry and audit trails.
    """
    logger = logging.getLogger("AsyncReconEngine")
    logger.setLevel(logging.INFO)

    # Prevent duplicate handlers if called multiple times
    if logger.handlers:
        return logger

    # Console Handler with custom format
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_format = logging.Formatter("[%(asctime)s] [%(levelname)s] %(message)s", datefmt="%H:%M:%S")
    console_handler.setFormatter(console_format)
    logger.addHandler(console_handler)

    # Optional File Handler for persistent session logs
    if log_to_file:
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_filename = os.path.join(log_dir, f"session_{timestamp}.log")
        
        file_handler = logging.FileHandler(log_filename, encoding="utf-8")
        file_handler.setLevel(logging.INFO)
        file_format = logging.Formatter("[%(asctime)s] [%(levelname)s] %(filename)s:%(lineno)d - %(message)s")
        file_handler.setFormatter(file_format)
        logger.addHandler(file_handler)

    return logger
