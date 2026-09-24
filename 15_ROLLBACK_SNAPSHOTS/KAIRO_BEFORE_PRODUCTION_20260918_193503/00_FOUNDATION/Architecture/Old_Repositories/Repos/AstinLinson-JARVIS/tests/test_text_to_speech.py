import logging
import pytest
from JARVIS.voice.text_to_speech import Pyttsx3SpeechSynthesizer

def test_pyttsx3_speaks_multiple_times_without_deadlock():
    logger = logging.getLogger("test_tts")
    synthesizer = Pyttsx3SpeechSynthesizer(voice_hint="female", rate=200, logger=logger)
    
    # We'll just call it with short phrases.
    # In a CI environment this might try to use real audio, so we might want to mock,
    # but the instructions specifically ask to verify runAndWait() completes reliably.
    for i in range(10):
        synthesizer.speak(f"Number {i}")
        # Simulate recording from the microphone like the wake word loop does
        try:
            import sounddevice as sd
            import numpy as np
            # Record 100ms of audio
            rec = sd.rec(int(16000 * 0.1), samplerate=16000, channels=1, dtype=np.float32)
            sd.wait()
        except Exception:
            pass
