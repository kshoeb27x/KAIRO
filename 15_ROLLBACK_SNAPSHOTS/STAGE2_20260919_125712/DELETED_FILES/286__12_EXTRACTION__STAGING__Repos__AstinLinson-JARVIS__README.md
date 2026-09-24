# JARVIS

JARVIS is a modular, offline-first AI desktop assistant designed with a production-oriented architecture. It combines local speech recognition, local large language models, long-term memory, desktop automation, and a skill-based execution framework into a unified voice-controlled assistant.

The project emphasizes modularity, extensibility, and privacy by performing inference locally whenever possible.

---

## Features

### Voice Interaction

- Wake word detection
- Continuous microphone streaming
- Faster-Whisper speech recognition
- Automatic CUDA to CPU fallback
- Text-to-speech response generation
- Voice activity detection

### Artificial Intelligence

- Local LLM inference through Ollama
- Qwen3 language model integration
- Modular language model abstraction
- Conversation planning pipeline
- Personality system
- Intent detection
- Context-aware responses

### Memory

- Persistent long-term memory
- Identity memory
- Preference memory
- Conversation history
- Automatic memory extraction
- Explicit memory management commands

### Desktop Automation

- Launch desktop applications
- Locate folders recursively
- Structured desktop command execution
- Safety confirmation for destructive operations
- Extensible desktop action framework

### Architecture

- Skill-based routing
- Modular BrainRouter
- Planner abstraction
- Memory manager
- Language model abstraction
- Configurable providers
- YAML-based configuration

---

## Architecture

```
                    ┌────────────────────────┐
                    │     Microphone Input   │
                    └────────────┬───────────┘
                                 │
                                 ▼
                    Voice Activity Detection
                                 │
                                 ▼
                     Faster-Whisper Speech
                                 │
                                 ▼
                      Wake Word Detection
                                 │
                                 ▼
                          BrainRouter
                                 │
            ┌────────────────────┴────────────────────┐
            │                                         │
            ▼                                         ▼
      Skill Registry                         Planner + Memory
            │                                         │
            └────────────────────┬────────────────────┘
                                 ▼
                     OpenAI-Compatible LLM
                          (Ollama/Qwen3)
                                 │
                                 ▼
                        Response Generation
                                 │
                                 ▼
                          Text-to-Speech
```

---

## Technology Stack

| Component | Technology |
|----------|------------|
| Programming Language | Python |
| Speech Recognition | Faster-Whisper |
| Voice Activity Detection | WebRTC VAD |
| Local LLM | Ollama |
| Language Model | Qwen3 |
| Text-to-Speech | pyttsx3 |
| Configuration | YAML |
| Testing | pytest |

---

## Project Structure

```
JARVIS/
├── brain/
├── config/
├── memory/
├── models/
├── skills/
├── voice/
├── tests/
└── main.py
```

---

## Installation

Clone the repository.

```bash
git clone https://github.com/<username>/JARVIS.git
cd JARVIS
```

Install dependencies.

```bash
pip install -r requirements.txt
```

Install Ollama.

```bash
ollama pull qwen3
```

Configure the environment.

```
JARVIS_LLM_API_KEY=ollama
```

Run the assistant.

```bash
python -m JARVIS.main
```

---

## Current Capabilities

- Wake-word activation
- Continuous voice interaction
- Offline speech recognition
- Local language model inference
- Persistent long-term memory
- Desktop application launching
- Folder search
- Skill routing
- Personality management
- Conversation history
- Automatic hardware fallback
- Configurable architecture

---

## Design Goals

- Offline-first operation
- Privacy-focused execution
- Modular architecture
- Extensible skill framework
- Maintainable codebase
- Production-oriented engineering practices

---

## Testing

Run the complete test suite.

```bash
pytest
```

All core modules include automated regression tests.

---

## Roadmap

### Version 1.1

- Window management
- Clipboard automation
- OCR integration
- Screenshot understanding
- Browser automation
- Expanded desktop skills

### Version 2.0

- Vision-language models
- Multi-agent orchestration
- Plugin ecosystem
- Workflow automation
- Cross-platform support
- Distributed memory

---

## License

This project is released under the MIT License.
