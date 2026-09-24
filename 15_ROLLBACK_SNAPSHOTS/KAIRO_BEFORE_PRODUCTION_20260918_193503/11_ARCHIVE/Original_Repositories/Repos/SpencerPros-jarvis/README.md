# Jarvis — AI Voice Assistant

A locally-run personal AI voice assistant inspired by Jarvis from Iron Man. Speak to it, and it speaks back. Built with Python using a fully local AI model, no subscriptions, no cloud AI, no data leaving your machine.

---

## What It Does

- **Voice input** — listens for your voice using your microphone
- **AI responses** — powered by llama3.2 running locally via Ollama
- **Voice output** — responds using a British male neural voice (Microsoft Edge TTS)
- **Animated orb UI** — a glowing blue sphere that changes color based on state (listening, thinking, speaking)
- **Browser control** — open any website by just asking ("open YouTube", "go to ESPN")
- **App launching** — open Notepad, Calculator, File Explorer, and more
- **Persistent memory** — remembers things you tell it across sessions

---

## Demo

| State | Orb Color | Meaning |
|-------|-----------|---------|
| Idle | Blue (slow pulse) | Waiting for your voice |
| Listening | Green (pulse) | Hearing your command |
| Thinking | Red (pulse) | Processing with AI |
| Speaking | Blue (faster pulse) | Responding to you |

---

## What I Learned

- **Voice I/O in Python** — using `speech_recognition` for microphone input and `edge_tts` for neural text-to-speech
- **Threading** — running the AI loop and the visual UI simultaneously without blocking each other
- **Pygame** — building a real-time animated UI with layered drawing, alpha blending, and a 60fps render loop
- **Prompt engineering** — giving the AI a consistent personality and injecting persistent memory into the system prompt
- **Local AI** — running a large language model entirely on-device with Ollama, keeping all data private
- **Building a .exe** — packaging a Python app into a standalone Windows executable with PyInstaller

---

## How It Works

```
Microphone input
      ↓
Google Speech Recognition (voice → text)
      ↓
Command check (open apps/websites? memory?)
      ↓
If no match → sent to llama3.2 via Ollama
      ↓
AI response text
      ↓
Edge TTS (text → speech, British neural voice)
      ↓
Pygame plays audio + animates orb
```

---

## Voice Commands

| What you say | What happens |
|---|---|
| Any question | Jarvis answers |
| "Open YouTube" | Opens youtube.com in browser |
| "Go to ESPN" | AI resolves URL and opens it |
| "Open Notepad" | Launches Notepad |
| "Remember my name is Spencer" | Saves to persistent memory |
| "What do you remember?" | Recalls all saved memory |
| "Forget everything" | Clears all memory |
| "Goodbye" / "Shut down" | Closes Jarvis |

---

## Setup

**Requirements:**
- Python 3.10+
- [Ollama](https://ollama.com) installed and running
- A microphone
- Internet connection (for speech recognition and TTS voice generation)

**Install dependencies:**
```bash
pip install speechrecognition pyttsx3 pyaudio edge-tts pygame requests
```

**Pull the AI model:**
```bash
ollama pull llama3.2
```

**Run Jarvis:**
```bash
python jarvis.py
```

**Build as a standalone .exe:**
```bash
pip install pyinstaller
python -m PyInstaller --onefile --noconsole --name "Jarvis" --icon="jarvis.ico" jarvis.py
```
The executable will be in the `dist/` folder.

---

## Privacy

- The AI model runs **fully locally** via Ollama — no conversation data leaves your machine
- Speech recognition uses Google's API — your voice is briefly processed by Google to convert to text
- TTS uses Microsoft Edge's neural voice API — response text is sent to Microsoft to generate audio
- Persistent memory is stored locally in `memory.json`
