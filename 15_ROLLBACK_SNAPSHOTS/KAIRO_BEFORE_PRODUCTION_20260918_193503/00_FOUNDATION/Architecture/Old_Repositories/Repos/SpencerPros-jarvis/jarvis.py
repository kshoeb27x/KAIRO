import speech_recognition as sr
import requests
import edge_tts
import asyncio
import pygame
import tempfile
import os
import math
import threading
import webbrowser
import subprocess

# ── States ────────────────────────────────────────────────────────────────────
STATE_IDLE      = "idle"
STATE_LISTENING = "listening"
STATE_THINKING  = "thinking"
STATE_SPEAKING  = "speaking"

state = STATE_IDLE

# ── Display ───────────────────────────────────────────────────────────────────
WIDTH, HEIGHT = 500, 500
CENTER = (WIDTH // 2, HEIGHT // 2)
FPS = 60

pygame.init()
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Jarvis")
clock = pygame.time.Clock()
font_large = pygame.font.SysFont("Segoe UI", 22)
font_small  = pygame.font.SysFont("Segoe UI", 16)

# Colors
BG         = (5, 8, 20)
BLUE_CORE  = (50, 150, 255)
BLUE_GLOW  = (20, 80, 180)
GREEN_CORE = (50, 220, 120)
GREEN_GLOW = (10, 100, 60)
RED_CORE   = (255, 80, 80)
RED_GLOW   = (120, 20, 20)
WHITE      = (220, 230, 255)
DIM        = (80, 100, 140)

status_text = "Jarvis Online"

def get_colors():
    if state == STATE_LISTENING:
        return GREEN_CORE, GREEN_GLOW
    elif state == STATE_THINKING:
        return RED_CORE, RED_GLOW
    elif state == STATE_SPEAKING:
        return BLUE_CORE, BLUE_GLOW
    else:
        return BLUE_CORE, BLUE_GLOW

def draw_orb(tick):
    screen.fill(BG)

    core_color, glow_color = get_colors()
    t = tick / FPS

    pulse = 0.03 * math.sin(2 * math.pi * 0.6 * t)

    base_radius = 100
    radius = int(base_radius * (1 + pulse))

    # Outer glow rings
    for i in range(5, 0, -1):
        alpha_surf = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        glow_r = radius + i * 18
        alpha = int(30 - i * 4)
        pygame.draw.circle(alpha_surf, (*glow_color, alpha), CENTER, glow_r)
        screen.blit(alpha_surf, (0, 0))

    # Inner glow
    glow_surf = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    pygame.draw.circle(glow_surf, (*glow_color, 80), CENTER, radius + 30)
    screen.blit(glow_surf, (0, 0))

    # Core sphere gradient (layered circles)
    for i in range(radius, 0, -2):
        ratio = i / radius
        r = int(glow_color[0] + (core_color[0] - glow_color[0]) * ratio)
        g = int(glow_color[1] + (core_color[1] - glow_color[1]) * ratio)
        b = int(glow_color[2] + (core_color[2] - glow_color[2]) * ratio)
        pygame.draw.circle(screen, (r, g, b), CENTER, i)

    # Highlight
    highlight_pos = (CENTER[0] - radius // 3, CENTER[1] - radius // 3)
    highlight_surf = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    pygame.draw.circle(highlight_surf, (255, 255, 255, 40), highlight_pos, radius // 3)
    screen.blit(highlight_surf, (0, 0))

    # Orbit ring
    ring_radius = radius + 45
    ring_surf = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    angle_offset = (t * 60) % 360
    for i in range(360):
        angle = math.radians(i + angle_offset)
        x = int(CENTER[0] + ring_radius * math.cos(angle))
        y = int(CENTER[1] + ring_radius * math.sin(angle) * 0.3)
        alpha = int(120 * abs(math.sin(math.radians(i))))
        pygame.draw.circle(ring_surf, (*core_color, alpha), (x, y), 1)
    screen.blit(ring_surf, (0, 0))

    # Status label
    state_label = {"idle": "IDLE", "listening": "LISTENING", "thinking": "THINKING", "speaking": "SPEAKING"}
    label = font_small.render(state_label.get(state, ""), True, DIM)
    screen.blit(label, (WIDTH // 2 - label.get_width() // 2, HEIGHT - 80))

    # Status text
    msg = font_large.render(status_text, True, WHITE)
    screen.blit(msg, (WIDTH // 2 - msg.get_width() // 2, HEIGHT - 55))

    pygame.display.flip()

# ── Voice ─────────────────────────────────────────────────────────────────────
VOICE = "en-GB-RyanNeural"

async def _generate_speech(text, filename):
    communicate = edge_tts.Communicate(text, VOICE, rate="+5%", pitch="-5Hz")
    await communicate.save(filename)

def speak(text):
    global state, status_text
    print(f"Jarvis: {text}")
    status_text = text[:50] + ("..." if len(text) > 50 else "")
    state = STATE_SPEAKING
    with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as f:
        tmpfile = f.name
    asyncio.run(_generate_speech(text, tmpfile))
    pygame.mixer.init()
    pygame.mixer.music.load(tmpfile)
    pygame.mixer.music.play()
    while pygame.mixer.music.get_busy():
        clock.tick(FPS)
        draw_orb(pygame.time.get_ticks() // (1000 // FPS))
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                os._exit(0)
    pygame.mixer.quit()
    os.unlink(tmpfile)
    state = STATE_IDLE
    status_text = "Jarvis Online"

# ── Speech recognition ────────────────────────────────────────────────────────
recognizer = sr.Recognizer()

def listen():
    global state, status_text
    state = STATE_LISTENING
    status_text = "Listening..."
    with sr.Microphone() as source:
        recognizer.adjust_for_ambient_noise(source, duration=0.5)
        try:
            audio = recognizer.listen(source, timeout=8, phrase_time_limit=15)
            text = recognizer.recognize_google(audio)
            print(f"You: {text}")
            state = STATE_THINKING
            status_text = "Thinking..."
            return text.lower()
        except sr.WaitTimeoutError:
            state = STATE_IDLE
            status_text = "Jarvis Online"
            return None
        except sr.UnknownValueError:
            state = STATE_IDLE
            status_text = "Jarvis Online"
            return None
        except sr.RequestError:
            speak("I'm having trouble with speech recognition right now.")
            return None

# ── AI brain ──────────────────────────────────────────────────────────────────
conversation_history = []

BASE_PROMPT = """You are Jarvis, a highly intelligent personal AI assistant.
You are helpful, concise, and slightly formal — like the AI from Iron Man.
Keep responses brief and conversational since they will be spoken aloud.
Never use bullet points, markdown, or lists in your responses — speak in natural sentences."""

def ask_jarvis(user_input):
    conversation_history.append({"role": "user", "content": user_input})
    memory_context = ""
    if memory:
        memory_context = f"\n\nThings you remember about the user: {'. '.join(memory.values())}"
    SYSTEM_PROMPT = BASE_PROMPT + memory_context
    messages = [{"role": "system", "content": SYSTEM_PROMPT}] + conversation_history
    response = requests.post(
        "http://localhost:11434/api/chat",
        json={"model": "llama3.2", "messages": messages, "stream": False}
    )
    reply = response.json()["message"]["content"]
    conversation_history.append({"role": "assistant", "content": reply})
    if len(conversation_history) > 20:
        conversation_history.pop(0)
        conversation_history.pop(0)
    return reply

# ── Computer control ─────────────────────────────────────────────────────────
APPS = {
    "notepad": "notepad.exe",
    "calculator": "calc.exe",
    "file explorer": "explorer.exe",
    "explorer": "explorer.exe",
    "paint": "mspaint.exe",
    "task manager": "taskmgr.exe",
}

def get_url_from_ai(user_input):
    response = requests.post(
        "http://localhost:11434/api/chat",
        json={
            "model": "llama3.2",
            "messages": [
                {"role": "system", "content": "You are a URL resolver. The user wants to open a website. Reply with ONLY the full URL including https://. Nothing else. No explanation."},
                {"role": "user", "content": user_input}
            ],
            "stream": False
        }
    )
    url = response.json()["message"]["content"].strip()
    if url.startswith("http"):
        return url
    return None

def handle_computer_control(user_input):
    if any(word in user_input for word in ["open", "go to", "navigate to", "launch", "take me to"]):
        # Open apps first
        for name, exe in APPS.items():
            if name in user_input:
                subprocess.Popen(exe)
                speak(f"Opening {name}.")
                return True

        # Let AI figure out the URL
        url = get_url_from_ai(user_input)
        if url:
            webbrowser.open(url)
            site = url.replace("https://", "").replace("www.", "").split("/")[0]
            speak(f"Opening {site} now.")
            return True

    return False

# ── Memory ────────────────────────────────────────────────────────────────────
MEMORY_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "memory.json")

def load_memory():
    if os.path.exists(MEMORY_FILE):
        with open(MEMORY_FILE, "r") as f:
            import json
            return json.load(f)
    return {}

def save_memory(memory):
    with open(MEMORY_FILE, "w") as f:
        import json
        json.dump(memory, f, indent=2)

memory = load_memory()

def handle_memory(user_input):
    if "remember" in user_input:
        fact = user_input.replace("remember", "").strip()
        key = f"fact_{len(memory) + 1}"
        memory[key] = fact
        save_memory(memory)
        speak("Got it, I'll remember that.")
        return True
    if "forget everything" in user_input:
        memory.clear()
        save_memory(memory)
        speak("Memory cleared.")
        return True
    if "what do you remember" in user_input or "what did i tell you" in user_input:
        if memory:
            speak(f"Here's what I remember: {'. '.join(memory.values())}")
        else:
            speak("I don't have anything stored in memory yet.")
        return True
    return False

# ── Main loop ─────────────────────────────────────────────────────────────────
def jarvis_loop():
    speak("Jarvis online. How can I assist you?")
    while True:
        user_input = listen()
        if not user_input:
            continue
        if any(word in user_input for word in ["goodbye", "shut down", "exit", "quit", "bye"]):
            speak("Goodbye. Jarvis signing off.")
            pygame.quit()
            os._exit(0)
        if handle_memory(user_input):
            continue
        if handle_computer_control(user_input):
            continue
        try:
            reply = ask_jarvis(user_input)
            speak(reply)
        except Exception as e:
            speak("I encountered an error. Please make sure Ollama is running.")
            print(f"Error: {e}")

def main():
    thread = threading.Thread(target=jarvis_loop, daemon=True)
    thread.start()

    tick = 0
    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                os._exit(0)

        draw_orb(tick)
        clock.tick(FPS)
        tick += 1

if __name__ == "__main__":
    main()
