"""
utils/logger.py
----------------
Centralized logging setup for the AI Chatbot Voice project.
Logs to both console and a rotating file (logs/chatbot.log).
"""

import logging
import os
from logging.handlers import RotatingFileHandler
from config.settings import settings

# Ensure logs directory exists
LOG_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "logs")
os.makedirs(LOG_DIR, exist_ok=True)

LOG_FILE = os.path.join(LOG_DIR, "chatbot.log")

# Log format
LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


def get_logger(name: str) -> logging.Logger:
    """
    Returns a named logger with console and optional file handlers.

    Args:
        name (str): Logger name (typically __name__ of the calling module).

    Returns:
        logging.Logger: Configured logger instance.
    """
    logger = logging.getLogger(name)

    # Avoid adding duplicate handlers
    if logger.handlers:
        return logger

    level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)
    logger.setLevel(level)

    # Console handler (colorized output)
    console_handler = logging.StreamHandler()
    console_handler.setLevel(level)
    console_handler.setFormatter(_get_formatter(colored=True))

    logger.addHandler(console_handler)

    # File handler (rotating, max 5MB × 3 backups)
    if settings.LOG_TO_FILE:
        file_handler = RotatingFileHandler(
            LOG_FILE,
            maxBytes=5 * 1024 * 1024,  # 5 MB
            backupCount=3,
            encoding="utf-8",
        )
        file_handler.setLevel(level)
        file_handler.setFormatter(_get_formatter(colored=False))
        logger.addHandler(file_handler)

    logger.propagate = False
    return logger


def _get_formatter(colored: bool = False) -> logging.Formatter:
    """Return a formatter, optionally with ANSI color codes."""
    if not colored:
        return logging.Formatter(LOG_FORMAT, datefmt=DATE_FORMAT)

    class ColorFormatter(logging.Formatter):
        COLORS = {
            "DEBUG":    "\033[36m",   # Cyan
            "INFO":     "\033[32m",   # Green
            "WARNING":  "\033[33m",   # Yellow
            "ERROR":    "\033[31m",   # Red
            "CRITICAL": "\033[41m",   # Red background
        }
        RESET = "\033[0m"

        def format(self, record):
            color = self.COLORS.get(record.levelname, self.RESET)
            record.levelname = f"{color}{record.levelname}{self.RESET}"
            return super().format(record)

    return ColorFormatter(LOG_FORMAT, datefmt=DATE_FORMAT)
