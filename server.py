"""
server.py
---------
Flask web server that connects the voice chatbot modules (SpeechToText, AIClient, TextToSpeech)
with a modern web browser user interface.
"""

import sys
import speech_recognition as sr
from flask import Flask, jsonify, request, render_template

from config.settings import settings
from modules.speech_to_text import SpeechToText
from modules.ai_client import AIClient
from modules.text_to_speech import TextToSpeech
from modules.error_handler import ErrorHandler
from utils.logger import get_logger

logger = get_logger(__name__)

app = Flask(
    __name__,
    template_folder="templates",
    static_folder="static"
)

# Initialize modules globally
stt = SpeechToText()
ai = AIClient()
tts = TextToSpeech()


@app.route("/")
def index():
    """Serve the chatbot web application UI."""
    return render_template("index.html")


@app.route("/api/chat", methods=["POST"])
def chat():
    """
    Process text messages from the client.
    Sends user message to AI and returns the text response.
    """
    data = request.json or {}
    user_text = data.get("message", "").strip()

    if not user_text:
        return jsonify({"error": "Message is empty."}), 400

    logger.info(f"Received web chat message: {user_text}")

    try:
        response = ai.get_response(user_text)
        if not response:
            return jsonify({"error": "AI returned an empty response."}), 500
        return jsonify({"response": response})
    except RuntimeError as e:
        error_str = str(e)
        logger.error(f"Chat endpoint error: {error_str}")
        # Tell the frontend if this was a rate limit so it shows a different status
        is_rate_limit = "rate limit" in error_str.lower() or "quota" in error_str.lower()
        return jsonify({
            "error": error_str,
            "error_type": "rate_limit" if is_rate_limit else "api_error"
        }), 500
    except Exception as e:
        logger.error(f"Chat endpoint unexpected error: {e}")
        return jsonify({
            "error": f"❌ Unexpected error: {type(e).__name__}: {e}",
            "error_type": "unexpected"
        }), 500


@app.route("/api/stt", methods=["POST"])
def trigger_stt():
    """
    Trigger host-side microphone recording.
    Captures user voice, translates to text, and returns the recognized text.
    """
    logger.info("Web client triggered host speech-to-text.")
    try:
        user_text = stt.listen()
        if user_text is None:
            # Fallback if somehow None returns without exception
            error_msg = ErrorHandler.handle_mic_timeout()
            return jsonify({"error": error_msg}), 408

        return jsonify({"text": user_text})

    except sr.WaitTimeoutError:
        error_msg = ErrorHandler.handle_mic_timeout()
        return jsonify({"error": error_msg, "error_type": "timeout"}), 408
    except sr.UnknownValueError:
        error_msg = ErrorHandler.handle_unknown_speech()
        return jsonify({"error": error_msg, "error_type": "unknown_speech"}), 422
    except sr.RequestError as e:
        error_msg = ErrorHandler.handle_mic_error(e)
        return jsonify({"error": error_msg, "error_type": "request_error"}), 502
    except Exception as e:
        error_msg = ErrorHandler.handle_unexpected(e)
        return jsonify({"error": error_msg, "error_type": "unexpected"}), 500


@app.route("/api/tts", methods=["POST"])
def trigger_tts():
    """
    Trigger host-side Text-To-Speech.
    Takes response text and reads it aloud on the server's speakers.
    """
    data = request.json or {}
    text = data.get("text", "").strip()

    if not text:
        return jsonify({"error": "No text provided for TTS."}), 400

    logger.info(f"Web client triggered host text-to-speech for: {text[:40]}...")

    try:
        tts.speak(text)
        return jsonify({"status": "success"})
    except Exception as e:
        logger.error(f"Host TTS failed: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/settings", methods=["GET", "POST"])
def get_or_update_settings():
    """Read or update configuration parameters dynamically."""
    if request.method == "POST":
        data = request.json or {}

        # Toggle Text-to-Speech
        if "tts_enabled" in data:
            settings.TTS_ENABLED = bool(data["tts_enabled"])
            logger.info(f"Dynamic setting updated - TTS Enabled: {settings.TTS_ENABLED}")

        # Update Provider
        if "ai_provider" in data:
            provider = data["ai_provider"].strip().lower()
            if provider in ["openai", "gemini"]:
                settings.AI_PROVIDER = provider
                ai.provider = provider
                ai._init_client()  # Re-initialize SDK client
                logger.info(f"Dynamic setting updated - AI Provider: {settings.AI_PROVIDER}")

        # Clear Chat Session
        if data.get("reset_history"):
            ai.reset_history()
            logger.info("Conversation history reset by client.")

    return jsonify({
        "ai_provider": settings.AI_PROVIDER,
        "gemini_model": settings.GEMINI_MODEL,
        "openai_model": settings.OPENAI_MODEL,
        "tts_enabled": settings.TTS_ENABLED,
        "recognition_language": settings.RECOGNITION_LANGUAGE
    })


if __name__ == "__main__":
    # Validate API key settings on startup
    try:
        settings.validate()
    except ValueError as e:
        ErrorHandler.handle_missing_api_key(settings.AI_PROVIDER)
        logger.critical(str(e))
        sys.exit(1)

    print("\n🚀 Chatbot Web Server starting on http://127.0.0.1:5000")
    app.run(host="127.0.0.1", port=5000, debug=False)
