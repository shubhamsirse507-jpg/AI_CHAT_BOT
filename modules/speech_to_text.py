"""
modules/speech_to_text.py
--------------------------
Handles voice input from the microphone.
Converts spoken words into text using the SpeechRecognition library.
"""

import time
from collections import deque
import numpy as np
import sounddevice as sd
import speech_recognition as sr
from config.settings import settings
from utils.logger import get_logger

logger = get_logger(__name__)


class SpeechToText:
    """Captures microphone audio using sounddevice and converts it to text."""

    def __init__(self):
        self.recognizer = sr.Recognizer()
        self.recognizer.pause_threshold = 1.2
        self.recognizer.energy_threshold = 300
        logger.info("SpeechToText module initialized (using sounddevice backend).")

    def listen(self) -> str | None:
        """
        Listen from microphone using sounddevice and return recognized text.

        Returns:
            str: Recognized text, or None on failure.
        """
        fs = 16000
        block_size = 1024

        print("\n🎤 Adjusting for ambient noise... (Please stay quiet)")
        logger.info("Adjusting for ambient noise using sounddevice...")

        ambient_rms = []
        calibration_blocks = int(fs / block_size)  # ~1 second of calibration

        try:
            with sd.InputStream(samplerate=fs, channels=1, dtype='int16', blocksize=block_size) as stream:
                for _ in range(calibration_blocks):
                    block, overflowed = stream.read(block_size)
                    rms = np.sqrt(np.mean(block.flatten().astype(np.float64)**2))
                    ambient_rms.append(rms)

                mean_ambient = np.mean(ambient_rms) if ambient_rms else 100
                max_ambient = np.max(ambient_rms) if ambient_rms else 150
                # Auto threshold: slightly lower multipliers for enhanced sensitivity, minimum 200
                threshold = max(max_ambient * 1.25, mean_ambient + 100, 200)
                logger.info(f"Calibration done. Mean ambient RMS: {mean_ambient:.2f}, Threshold: {threshold:.2f}")

                print("🎤 Listening... (speak now)")
                logger.info("Listening for speech...")

                start_time = time.time()
                speech_started = False
                speech_blocks = []
                silence_start = None
                speech_start_time = None

                # Pre-roll window (~0.32 seconds of audio) to prevent front-clipping of words
                preroll = deque(maxlen=5)

                while True:
                    block, overflowed = stream.read(block_size)
                    block_flat = block.flatten()
                    rms = np.sqrt(np.mean(block_flat.astype(np.float64)**2))
                    now = time.time()

                    if not speech_started:
                        preroll.append(block_flat.tobytes())
                        # Check timeout if speech hasn't started yet
                        if now - start_time > settings.MIC_TIMEOUT:
                            logger.warning("Microphone timed out. No speech detected.")
                            raise sr.WaitTimeoutError("Microphone timed out. No speech detected.")

                        if rms > threshold:
                            speech_started = True
                            speech_start_time = now
                            # Prepend the pre-roll window
                            speech_blocks.extend(preroll)
                            preroll.clear()
                            logger.info("Speech started.")
                    else:
                        speech_blocks.append(block_flat.tobytes())

                        # Check phrase time limit
                        if now - speech_start_time > settings.MIC_PHRASE_LIMIT:
                            logger.info("Reached microphone phrase time limit.")
                            break

                        if rms < threshold:
                            if silence_start is None:
                                silence_start = now
                            elif now - silence_start > self.recognizer.pause_threshold:
                                logger.info("Detected silence/pause. Stopping recording.")
                                break
                        else:
                            silence_start = None

                if not speech_blocks:
                    raise sr.WaitTimeoutError("Microphone timed out. No speech detected.")

                logger.info("Audio captured. Recognizing...")
                frame_data = b"".join(speech_blocks)
                audio = sr.AudioData(frame_data, fs, 2)  # sample_width is 2 bytes for int16

                text = self.recognizer.recognize_google(
                    audio,
                    language=settings.RECOGNITION_LANGUAGE,
                )
                print(f"📝 You said: {text}")
                logger.info(f"Recognized: {text}")
                return text

        except sr.WaitTimeoutError as e:
            raise e
        except sr.UnknownValueError as e:
            logger.warning("Speech not understood.")
            raise e
        except sr.RequestError as e:
            logger.error(f"Google Speech API error: {e}")
            raise e
        except Exception as e:
            logger.error(f"Unexpected error in sounddevice recording: {e}")
            raise e
