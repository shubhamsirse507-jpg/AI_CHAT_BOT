"""
modules/text_to_speech.py
--------------------------
Converts AI response text to spoken audio output.
Uses pyttsx3 (offline, no API key required).
"""

import pyttsx3
from config.settings import settings
from utils.logger import get_logger

logger = get_logger(__name__)


class TextToSpeech:
    """Converts text responses to spoken voice output using pyttsx3."""

    def __init__(self):
        if not settings.TTS_ENABLED:
            logger.info("Text-to-Speech is DISABLED in settings.")
            self.engine = None
            return

        self.engine = pyttsx3.init()
        self._configure_engine()
        logger.info("TextToSpeech module initialized.")

    def _configure_engine(self):
        """Apply TTS settings from config."""
        self.engine.setProperty("rate", settings.TTS_RATE)
        self.engine.setProperty("volume", settings.TTS_VOLUME)

        # Select a preferred voice (female/male)
        voices = self.engine.getProperty("voices")
        if voices:
            # Default: first available voice
            self.engine.setProperty("voice", voices[0].id)

    def speak(self, text: str) -> None:
        """
        Convert text to speech and play it.

        Args:
            text (str): The text to be spoken aloud.
        """
        if not settings.TTS_ENABLED or self.engine is None:
            logger.info("TTS skipped (disabled).")
            return

        if not text or not text.strip():
            logger.warning("Empty text passed to TTS, skipping.")
            return

        print(f"\n🔊 Speaking: {text[:60]}{'...' if len(text) > 60 else ''}")
        logger.info(f"Speaking: {text[:80]}")

        try:
            self.engine.say(text)
            self.engine.runAndWait()
        except RuntimeError as e:
            logger.error(f"TTS RuntimeError: {e}")
        except Exception as e:
            logger.error(f"TTS unexpected error: {e}")

    def list_voices(self) -> list:
        """Return a list of available voice names."""
        if self.engine is None:
            return []
        voices = self.engine.getProperty("voices")
        return [v.name for v in voices]
