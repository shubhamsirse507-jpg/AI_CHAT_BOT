"""
modules/ai_client.py
---------------------
Sends user queries to the configured AI provider (OpenAI or Gemini)
and returns the AI-generated response as a string.
"""

import time
from config.settings import settings
from utils.logger import get_logger

logger = get_logger(__name__)

# Retry configuration for rate-limited API calls
_MAX_RETRIES = 3
_RETRY_DELAYS = [2, 5, 10]  # seconds between attempts


class AIClient:
    """Unified AI client supporting OpenAI and Google Gemini."""

    def __init__(self):
        self.provider = settings.AI_PROVIDER
        self.conversation_history = []
        self._init_client()
        logger.info(f"AIClient initialized with provider: {self.provider}")

    def _init_client(self):
        """Initialize the appropriate AI SDK client."""
        if self.provider == "openai":
            import openai
            self.client = openai.OpenAI(api_key=settings.OPENAI_API_KEY)

        elif self.provider == "gemini":
            import google.generativeai as genai
            genai.configure(api_key=settings.GEMINI_API_KEY)
            
            # Log available models to help identify valid ones
            try:
                models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
                logger.info(f"Available Gemini models: {models}")
            except Exception as e:
                logger.error(f"Could not list Gemini models: {e}")

            self.client = genai.GenerativeModel(settings.GEMINI_MODEL)
            self.chat_session = self.client.start_chat(history=[])

        else:
            raise ValueError(f"Unsupported AI provider: '{self.provider}'. Use 'openai' or 'gemini'.")

    def get_response(self, user_input: str) -> str:
        """
        Send user input to the AI and return its response.
        Automatically retries up to 3 times with exponential backoff
        when the API returns a rate-limit (429) error.

        Args:
            user_input (str): The user's message/query.

        Returns:
            str: The AI-generated response text.
        """
        logger.info(f"Sending to {self.provider}: {user_input}")
        last_error = None

        for attempt in range(_MAX_RETRIES):
            try:
                if self.provider == "openai":
                    return self._openai_response(user_input)
                elif self.provider == "gemini":
                    return self._gemini_response(user_input)

            except Exception as e:
                classified = self._classify_error(e)
                raw = str(e)
                is_rate_limit = (
                    "429" in raw
                    or "quota" in raw.lower()
                    or "rate limit" in raw.lower()
                    or "resource exhausted" in raw.lower()
                )

                if is_rate_limit and attempt < _MAX_RETRIES - 1:
                    delay = _RETRY_DELAYS[attempt]
                    logger.warning(
                        f"Rate limit hit (attempt {attempt + 1}/{_MAX_RETRIES}). "
                        f"Retrying in {delay}s..."
                    )
                    time.sleep(delay)
                    last_error = classified
                    continue

                # Non-retryable error, or final attempt exhausted
                logger.error(f"AI API error (attempt {attempt + 1}): {e}")
                raise classified

        # All retries exhausted — raise the last classified error
        raise last_error

    def _classify_error(self, error: Exception) -> Exception:
        """
        Parse the raw API exception and return a descriptive RuntimeError
        with a clear user-facing message based on HTTP status / error type.
        """
        raw = str(error)

        # Model not found / deprecated
        if "404" in raw or "not found" in raw.lower() or "no longer available" in raw.lower():
            model = settings.GEMINI_MODEL if self.provider == "gemini" else settings.OPENAI_MODEL
            return RuntimeError(
                f"🚫 Model '{model}' is unavailable or has been retired. "
                f"Update GEMINI_MODEL in your .env file to a supported model (e.g. gemini-pro)."
            )

        # Rate limit / quota
        if "429" in raw or "quota" in raw.lower() or "rate limit" in raw.lower() or "resource exhausted" in raw.lower():
            return RuntimeError(
                f"⏳ {self.provider.capitalize()} rate limit hit. "
                f"You've exceeded your free quota. Wait a moment or upgrade your plan."
            )

        # Auth / API key issues
        if "403" in raw or "401" in raw or "api key" in raw.lower() or "permission denied" in raw.lower() or "invalid" in raw.lower():
            return RuntimeError(
                f"🔑 Invalid or missing API key for {self.provider.capitalize()}. "
                f"Check GEMINI_API_KEY / OPENAI_API_KEY in your .env file."
            )

        # Network / connection issues
        if "connection" in raw.lower() or "timeout" in raw.lower() or "network" in raw.lower() or "503" in raw or "502" in raw:
            return RuntimeError(
                f"🌐 Cannot reach the {self.provider.capitalize()} API. "
                f"Check your internet connection and try again."
            )

        # Fallback: surface the real error message directly
        return RuntimeError(f"❌ {self.provider.capitalize()} API error: {raw}")

    def _openai_response(self, user_input: str) -> str:
        """Handle OpenAI API call with conversation history."""
        self.conversation_history.append({"role": "user", "content": user_input})

        response = self.client.chat.completions.create(
            model=settings.OPENAI_MODEL,
            messages=[
                {"role": "system", "content": "You are a helpful, friendly, and concise voice assistant."},
                *self.conversation_history,
            ],
        )

        reply = response.choices[0].message.content.strip()
        self.conversation_history.append({"role": "assistant", "content": reply})
        logger.info(f"OpenAI response: {reply}")
        return reply

    def _gemini_response(self, user_input: str) -> str:
        """Handle Gemini API call using chat session."""
        response = self.chat_session.send_message(user_input)
        reply = response.text.strip()
        logger.info(f"Gemini response: {reply}")
        return reply

    def reset_history(self):
        """Clear conversation history to start a fresh session."""
        self.conversation_history = []
        if self.provider == "gemini":
            self.chat_session = self.client.start_chat(history=[])
        logger.info("Conversation history cleared.")
