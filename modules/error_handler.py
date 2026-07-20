"""
modules/error_handler.py
-------------------------
Centralized error handling for microphone issues,
API failures, invalid input, and unexpected exceptions.
"""

import speech_recognition as sr
from utils.logger import get_logger

logger = get_logger(__name__)


class ErrorHandler:
    """Handles and categorizes all chatbot errors with user-friendly messages."""

    # ── Microphone / Speech Errors ─────────────────────────────────────────

    @staticmethod
    def handle_mic_timeout() -> str:
        msg = "⏰ No speech detected. Please try speaking again."
        logger.warning("Mic timeout — no speech detected.")
        print(msg)
        return msg

    @staticmethod
    def handle_unknown_speech() -> str:
        msg = "❓ Sorry, I couldn't understand that. Could you repeat?"
        logger.warning("Speech not understood (UnknownValueError).")
        print(msg)
        return msg

    @staticmethod
    def handle_mic_error(error: Exception) -> str:
        msg = f"🎤 Microphone error: {error}"
        logger.error(f"Microphone error: {error}")
        print(msg)
        return msg

    # ── API Errors ─────────────────────────────────────────────────────────

    @staticmethod
    def handle_api_error(error: Exception, provider: str = "AI") -> str:
        msg = f"🌐 {provider} API error. Please check your API key or internet connection."
        logger.error(f"{provider} API error: {error}")
        print(msg)
        return msg

    @staticmethod
    def handle_rate_limit(provider: str = "AI") -> str:
        msg = f"⚠️ {provider} rate limit reached. Please wait a moment and try again."
        logger.warning(f"{provider} rate limit hit.")
        print(msg)
        return msg

    # ── Config / Input Errors ──────────────────────────────────────────────

    @staticmethod
    def handle_missing_api_key(provider: str) -> str:
        msg = f"🔑 Missing API key for {provider}. Check your .env file."
        logger.critical(f"Missing API key: {provider}")
        print(msg)
        return msg

    @staticmethod
    def handle_empty_input() -> str:
        msg = "💬 Input was empty. Please say something."
        logger.warning("Empty input received.")
        print(msg)
        return msg

    # ── Generic / Unexpected ───────────────────────────────────────────────

    @staticmethod
    def handle_unexpected(error: Exception) -> str:
        msg = f"❌ Unexpected error occurred: {type(error).__name__}: {error}"
        logger.exception(f"Unexpected error: {error}")
        print(msg)
        return msg
