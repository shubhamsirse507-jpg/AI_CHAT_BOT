"""
main.py
--------
Entry point for the AI Chatbot Voice application.
Runs the main chatbot loop: listen → think → speak → repeat.

Usage:
    python main.py

Exit:
    Say "exit", "quit", or "bye" to stop the chatbot.
    Or press Ctrl+C at any time.
"""

import sys
import speech_recognition as sr
from colorama import Fore, Style, init

from config.settings import settings
from modules.speech_to_text import SpeechToText
from modules.ai_client import AIClient
from modules.text_to_speech import TextToSpeech
from modules.error_handler import ErrorHandler
from utils.logger import get_logger

# Initialize colorama for Windows color support
init(autoreset=True)

logger = get_logger(__name__)

# Keywords to gracefully exit the chatbot
EXIT_COMMANDS = {"exit", "quit", "bye", "goodbye", "stop"}


def print_banner():
    """Display a welcome banner at startup."""
    print(Fore.CYAN + Style.BRIGHT + """
╔══════════════════════════════════════════════╗
║       🤖  AI Voice Chatbot  🎤               ║
║  Say something to start | Say 'exit' to quit ║
╚══════════════════════════════════════════════╝
""" + Style.RESET_ALL)


def run():
    """Main chatbot loop."""
    print_banner()

    # Validate API keys before starting
    try:
        settings.validate()
    except ValueError as e:
        ErrorHandler.handle_missing_api_key(settings.AI_PROVIDER)
        logger.critical(str(e))
        sys.exit(1)

    # Initialize modules
    stt = SpeechToText()
    ai = AIClient()
    tts = TextToSpeech()

    print(Fore.GREEN + f"✅ Using AI Provider: {settings.AI_PROVIDER.upper()}")
    print(Fore.GREEN + f"✅ TTS Enabled: {settings.TTS_ENABLED}")
    print(Fore.YELLOW + "\n📢 Chatbot is ready! Start speaking...\n")

    logger.info("Chatbot session started.")

    while True:
        try:
            # ── Step 1: Listen ──────────────────────────────────────
            try:
                user_text = stt.listen()
            except sr.WaitTimeoutError:
                ErrorHandler.handle_mic_timeout()
                continue
            except sr.UnknownValueError:
                ErrorHandler.handle_unknown_speech()
                continue
            except sr.RequestError as e:
                ErrorHandler.handle_mic_error(e)
                continue

            if user_text is None:
                ErrorHandler.handle_mic_timeout()
                continue

            user_text = user_text.strip()

            if not user_text:
                ErrorHandler.handle_empty_input()
                continue

            # ── Step 2: Check for exit commands ─────────────────────
            if user_text.lower() in EXIT_COMMANDS:
                farewell = "Goodbye! Have a great day! 👋"
                print(Fore.CYAN + f"\n🤖 {farewell}")
                tts.speak(farewell)
                logger.info("User requested exit. Shutting down.")
                break

            # ── Step 3: Get AI Response ──────────────────────────────
            print(Fore.BLUE + "\n⏳ Thinking...")
            try:
                response = ai.get_response(user_text)
            except Exception as e:
                ErrorHandler.handle_api_error(e, settings.AI_PROVIDER)
                continue

            if not response:
                print(Fore.RED + "⚠️ AI returned an empty response.")
                continue

            print(Fore.MAGENTA + f"\n🤖 AI: {response}\n")

            # ── Step 4: Speak Response ───────────────────────────────
            tts.speak(response)

        except KeyboardInterrupt:
            print(Fore.YELLOW + "\n\n⚠️ Interrupted by user. Exiting...")
            logger.info("KeyboardInterrupt — chatbot stopped.")
            break

        except Exception as e:
            ErrorHandler.handle_unexpected(e)
            continue

    print(Fore.CYAN + "\n👋 Session ended. Check logs/ for conversation history.\n")
    logger.info("Chatbot session ended.")


if __name__ == "__main__":
    run()
