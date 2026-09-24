"""Standalone pyttsx3 subprocess worker. Run via subprocess.run([sys.executable, __file__, text, voice_hint, rate])."""
import sys
import pyttsx3
import logging

logging.basicConfig(level=logging.WARNING)

def main():
    if len(sys.argv) < 4:
        print("Usage: tts_worker.py <text> <voice_hint> <rate>", file=sys.stderr)
        sys.exit(1)

    text = sys.argv[1]
    voice_hint = sys.argv[2].strip().lower()
    rate = int(sys.argv[3])

    engine = pyttsx3.init()
    engine.setProperty("rate", rate)

    # Select voice: try hint first, then fall back to any available voice
    voices = engine.getProperty("voices") or []
    selected_voice_id = None

    # Pass 1: match hint against id, name, languages
    for voice in voices:
        voice_id = str(getattr(voice, "id", "")).lower()
        name = str(getattr(voice, "name", "")).lower()
        languages = " ".join(str(x) for x in getattr(voice, "languages", []) or []).lower()
        searchable = f"{voice_id} {name} {languages}"
        if voice_hint and voice_hint in searchable:
            selected_voice_id = getattr(voice, "id")
            print(f"[TTS_WORKER] Matched voice hint '{voice_hint}': {voice.name}", file=sys.stderr)
            break

    # Pass 2: try "female" if hint didn't match
    if not selected_voice_id and voice_hint != "female":
        for voice in voices:
            voice_id = str(getattr(voice, "id", "")).lower()
            name = str(getattr(voice, "name", "")).lower()
            if "female" in voice_id or "female" in name:
                selected_voice_id = getattr(voice, "id")
                print(f"[TTS_WORKER] Fallback to female voice: {voice.name}", file=sys.stderr)
                break

    # Pass 3: pick last voice in the list (usually Zira on en-US Windows)
    if not selected_voice_id and len(voices) > 1:
        selected_voice_id = voices[-1].id
        print(f"[TTS_WORKER] Fallback to last voice: {voices[-1].name}", file=sys.stderr)

    if selected_voice_id:
        engine.setProperty("voice", selected_voice_id)
    else:
        print("[TTS_WORKER] Using system default voice.", file=sys.stderr)

    print(f"[TTS_WORKER] Speaking ({len(text)} chars): {text[:80]}{'...' if len(text) > 80 else ''}", file=sys.stderr)
    engine.say(text)
    engine.runAndWait()
    print("[TTS_WORKER] Done.", file=sys.stderr)


if __name__ == "__main__":
    main()
