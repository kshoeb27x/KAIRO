# Jarvis

Jarvis is an open-source, local-first AI voice assistant built to run on your own machine.

It combines wake word detection, speech-to-text, text-to-speech, a local LLM through Ollama, a React/Vite interface, and optional integrations such as Gmail, Google Calendar, weather, research, and local memory.

Jarvis is designed to be useful, private, customizable, and extensible. 


---

## Features

Jarvis currently supports:

* Wake word activation
* Speech-to-text
* Text-to-speech
* Local LLM chat through Ollama
* React/Vite desktop-style web interface
* Weather lookup
* Gmail integration
* Google Calendar integration
* Google Contacts support
* Research Agent
* Local memory
* Standard CPU-friendly mode
* Optional NVIDIA/CUDA accelerated Beast Mode

---

## Installation Modes

Jarvis supports two installation modes.

### Standard Mode

Standard Mode is the default setup.

Use this mode if you want the simplest and most compatible installation.

Standard Mode uses:

* CPU speech-to-text
* Edge-TTS cloud voice fallback
* Standard local Ollama model
* No CUDA-specific Python packages

Recommended for:

* Laptops
* CPU-only desktops
* New users
* Compatibility testing

---

### Beast Mode

Beast Mode is optional.

Use Beast Mode only if your computer has a supported NVIDIA GPU and you want local GPU acceleration.

Beast Mode may use:

* NVIDIA CUDA
* GPU speech-to-text
* Kokoro local neural TTS
* Larger local research models
* CUDA-enabled PyTorch

Recommended for:

* NVIDIA desktop systems
* RTX-class GPUs
* Users who want faster local transcription
* Users who want local neural text-to-speech

Do not install Beast Mode packages unless you specifically want GPU acceleration.

---

## Prerequisites

Install these before setting up Jarvis:

* Python 3.12
* Git
* FFmpeg
* Node.js
* npm
* Ollama
* Microphone
* Modern web browser

For Beast Mode, you also need:

* Supported NVIDIA GPU
* Current NVIDIA driver
* CUDA-compatible PyTorch setup
* CUDA runtime libraries as required by your system

---

## Local LLM Setup

Jarvis uses Ollama for local LLM support.

Install Ollama, then pull at least one model.

Example:

```bash
ollama pull gemma4:e4b
```

For heavier research use, you may also pull a larger research model:

```bash
ollama pull qwen3.6:27b
```

The models you use are configurable in your `.env` file.

---

## Project Setup

Clone the repository:

```bash
git clone https://github.com/luccientertainment/Jarvis.git
cd Jarvis
```

Create a Python virtual environment.

Windows PowerShell:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Windows CMD:

```cmd
python -m venv .venv
.venv\Scripts\activate.bat
```

macOS / Linux:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

Upgrade pip:

```bash
pip install --upgrade pip
```

---

## Python Installation

### Standard Mode

Install the standard dependencies:

```bash
pip install -r requirements.txt
```

Example Standard Mode packages include:

```bash
pip install fastapi uvicorn[standard] requests httpx python-dotenv
pip install numpy sounddevice pygame soundfile
pip install faster-whisper edge-tts openwakeword onnxruntime
pip install google-api-python-client google-auth google-auth-oauthlib google-auth-httplib2
pip install ddgs
```

---

### Beast Mode

Install Standard Mode first.

Then install Beast Mode dependencies only if you have supported NVIDIA/CUDA hardware:

```bash
pip install -r requirements-beast.txt
```

Example Beast Mode packages:

```bash
pip install kokoro
pip install torch
```

Depending on your GPU and CUDA version, PyTorch may need to be installed using the official CUDA-specific command from PyTorch.

Example pattern:

```bash
pip install torch --index-url https://download.pytorch.org/whl/cu121
```

Use the PyTorch command that matches your installed CUDA/NVIDIA setup.

---


## wakeword Installation
Run setup_jarvis_wakeword.py


## Frontend Installation

Go to the frontend folder:

```bash
cd frontend
npm install
```

Run the UI:

```bash
npm run dev
```

Default frontend URL:

```text
http://localhost:5173
```

---

## Environment Configuration

Create a `.env` file in the project root.

Example:

```env
#######################################
# User
#######################################

USER_TITLE=sir
WAKE_RESPONSE=Hello sir, how can I help you?

USER_CITY=New York
USER_STATE=NY

#######################################
# AI
#######################################

OLLAMA_URL=http://localhost:11434/api/chat
CHAT_MODEL=gemma4:e4b
RESEARCH_MODEL=qwen3.6:27b

#######################################
# Gmail
#######################################

KEEP_GMAIL_DAYS=7

#######################################
# Performance
#######################################

BEAST_MODE=false

#######################################
# Future RAG
#######################################

RAG_TOP_K=3
RAG_SCORE_THRESHOLD=0.72
```

For Standard Mode:

```env
BEAST_MODE=false
```

For Beast Mode:

```env
BEAST_MODE=true
```

Only enable Beast Mode after installing the correct GPU dependencies.

---

## Google API Setup

Google features are optional.

To use Gmail, Calendar, or Contacts, you need:

* Google Cloud project
* Gmail API enabled
* Google Calendar API enabled
* Google People API enabled
* OAuth credentials downloaded as `google_credentials.json`

Place your credentials here:

```text
backend/config/google_credentials.json
```

After OAuth login, Jarvis will create:

```text
backend/config/token.json

---

## Gmail

The Gmail Agent can monitor unread emails, summarize messages, and store local inbox summaries.

Local Gmail-related files may include:

```text
backend/assets/inbox.json
backend/assets/google_contacts.json
```

These files may contain private information and should not be committed.

---

## Calendar

The Calendar integration can be used to:

* View schedules
* Announce upcoming events
* Add events
* Modify events
* Delete events

Calendar access requires Google OAuth setup.

---

## Contacts

Contacts support requires the Google People API.

Jarvis can use synced contacts so users can refer to people by name instead of typing full email addresses.

---

## Weather

Weather support requires an internet connection.

The default location comes from your `.env` file:

```env
USER_CITY=New York
USER_STATE=NY
```

---

## Research Agent

The Research Agent uses internet search and a local LLM to gather information and summarize results.

The Research Agent may use:

```text
ddgs
```

Research files may be stored locally:

```text
backend/assets/completed_research.json
backend/assets/active_research.json
```

These files may contain private research history and should not be committed.

---

## Running Jarvis

Jarvis usually needs three running processes:

1. Backend API
2. Frontend UI
3. Wake word listener

You can run "run_jarvis.py" to launch them all at once. The UI will automatically pop up after about 1 min once everything is iniitalized. 

---

###  Start Ollama

Make sure Ollama is running.

Test:

```bash
ollama list
```

---


### Wake Word Listener

Then say:

```text
Hey Jarvis
```

---

## Verification Checklist

### Standard Mode

Confirm:

* `.env` has `BEAST_MODE=false`
* Ollama is running
* Your selected Ollama model is installed
* Frontend loads
* Backend responds on port `8000`
* Wake word listener starts
* Microphone is detected
* Jarvis can answer a basic question
* Jarvis can speak using the Standard Mode voice path

---

### Beast Mode

Confirm:

* `.env` has `BEAST_MODE=true`
* NVIDIA driver is installed
* PyTorch detects CUDA
* Kokoro imports successfully
* Faster Whisper loads on CUDA
* Jarvis speaks locally

Quick CUDA test:

```bash
python -c "import torch; print(torch.cuda.is_available())"
```

Expected:

```text
True
```

---

## Troubleshooting

### Ollama Is Not Responding

Check that Ollama is running:

```bash
ollama list
```

Make sure the model in your `.env` file exists locally.

Example:

```bash
ollama pull gemma4:e4b
```

---

### Wake Word Does Not Start

Check:

* Microphone permissions
* `sounddevice` installation
* `openwakeword` installation
* `onnxruntime` installation

---

### No Audio Output

Check:

* Speakers or headphones
* `pygame`
* Edge-TTS setup for Standard Mode
* Kokoro and `soundfile` setup for Beast Mode

---

### Gmail or Calendar Fails

Check that these files exist:

```text
backend/config/google_credentials.json
backend/config/token.json
```

Also confirm the required Google APIs are enabled in your Google Cloud project.

---

### Beast Mode Fails

Set:

```env
BEAST_MODE=false
```

Then restart Jarvis.

If Standard Mode works, the issue is likely related to CUDA, PyTorch, Kokoro, or GPU configuration.

---

## Security and Privacy

Jarvis is local-first, but some optional features require third-party services.

Depending on your configuration, Jarvis may interact with:

* Ollama
* Google APIs
* Weather services
* Search services
* Text-to-speech services
* Local files
* Local models
* External models or APIs you choose to add

You are responsible for protecting your own private data.

Do not commit or publish:

```text
.env
backend/config/google_credentials.json
backend/config/token.json
backend/assets/inbox.json
backend/assets/google_contacts.json
backend/assets/completed_research.json
backend/assets/active_research.json
```

You should also avoid publishing:

* API keys
* OAuth tokens
* Email data
* Calendar data
* Contact data
* Local memory files
* Research history
* Personal configuration files
* Private logs

---

## Third-Party Components and License Responsibility

Jarvis may use, depend on, integrate with, or reference third-party software, libraries, frameworks, models, APIs, services, tools, and other components.

These third-party components are not owned by the Jarvis Project unless explicitly stated. Each third-party component remains subject to its own license, terms of use, model license, API terms, usage policies, restrictions, and compliance requirements.

By using, modifying, distributing, deploying, or building upon Jarvis, you acknowledge and agree that it is your responsibility to identify, review, and comply with all applicable third-party licenses and terms.

You are responsible for looking up and verifying the licenses, terms, and usage restrictions for all components you use with Jarvis, including but not limited to Python packages, JavaScript packages, React, Vite, Ollama, Whisper, Kokoro, Google APIs, Hugging Face models, AI models, APIs, cloud services, and any other external dependency or service.

The Jarvis Project does not guarantee that any third-party component is suitable for your intended use, including personal, commercial, research, educational, hosted, redistributed, or production use.

Before using, modifying, distributing, deploying, or monetizing Jarvis or any project based on Jarvis, you should independently review all applicable third-party licenses, notices, terms, and policies.

---

## License

Jarvis is open source under the MIT License.

See the `LICENSE` file for details.

The MIT License applies only to the original Jarvis code and materials created for the Jarvis Project.

Third-party dependencies, models, APIs, libraries, and services remain subject to their own licenses and terms.

---

## Disclaimer

Jarvis is provided as-is, without warranty of any kind.

The project may include experimental features, local AI models, third-party APIs, and integrations that can behave unpredictably or change over time.

Use Jarvis responsibly, review all third-party terms, and protect your private data.
