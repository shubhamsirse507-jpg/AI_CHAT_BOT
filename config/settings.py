"""
config/settings.py
------------------
Loads and validates all configuration from the .env file.
Provides a central settings object used across all modules.
"""

import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class Settings:
    """Central configuration class for the AI Chatbot Voice app."""

    # --- AI Provider ---
    AI_PROVIDER: str = os.getenv("AI_PROVIDER", "openai").lower()

    # --- OpenAI ---
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    OPENAI_MODEL: str = os.getenv("OPENAI_MODEL", "gpt-3.5-turbo")

    # --- Google Gemini ---
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")

    # --- Speech Recognition ---
    RECOGNITION_LANGUAGE: str = os.getenv("RECOGNITION_LANGUAGE", "en-US")
    MIC_TIMEOUT: int = int(os.getenv("MIC_TIMEOUT", 5))
    MIC_PHRASE_LIMIT: int = int(os.getenv("MIC_PHRASE_LIMIT", 10))

    # --- Text to Speech ---
    TTS_ENABLED: bool = os.getenv("TTS_ENABLED", "true").lower() == "true"
    TTS_RATE: int = int(os.getenv("TTS_RATE", 175))
    TTS_VOLUME: float = float(os.getenv("TTS_VOLUME", 1.0))

    # --- Logging ---
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    LOG_TO_FILE: bool = os.getenv("LOG_TO_FILE", "true").lower() == "true"

    @classmethod
    def validate(cls) -> bool:
        """Validate that required API keys are set."""
        if cls.AI_PROVIDER == "openai" and not cls.OPENAI_API_KEY:
            raise ValueError("❌ OPENAI_API_KEY is not set in your .env file.")
        if cls.AI_PROVIDER == "gemini" and not cls.GEMINI_API_KEY:
            raise ValueError("❌ GEMINI_API_KEY is not set in your .env file.")
        return True


# Singleton instance
settings = Settings()
