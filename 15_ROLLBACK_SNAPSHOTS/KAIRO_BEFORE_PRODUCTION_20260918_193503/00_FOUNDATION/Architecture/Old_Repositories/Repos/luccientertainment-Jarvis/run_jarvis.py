import subprocess
import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent

BACKEND_DIR = PROJECT_ROOT / "backend"
FRONTEND_DIR = PROJECT_ROOT / "frontend"

FRONTEND_URL = "http://localhost:5173"
BACKEND_URL = "http://localhost:8000"


def start_process(name: str, command: str, cwd: Path):
    print(f"Starting {name}...")
    print(f"Command: {command}")
    print(f"Directory: {cwd}")

    return subprocess.Popen(
        command,
        cwd=str(cwd),
        shell=True,
        #creationflags=subprocess.CREATE_NEW_CONSOLE,
    )


def main():
    processes = []

    try:
        processes.append(start_process(
            "FastAPI backend",
            f'"{sys.executable}" -m uvicorn main:app --reload',
            BACKEND_DIR,
        ))

        time.sleep(6)

        processes.append(start_process(
            "React frontend",
            "npm run dev",
            FRONTEND_DIR,
        ))

        time.sleep(6)

        processes.append(start_process(
            "Wake word listener",
            f'"{sys.executable}" modules/wakeword/listener.py',
            BACKEND_DIR,
        ))

        time.sleep(45)
        subprocess.Popen(
            'start "" chrome --app=http://localhost:5173 --window-size=1000,700',
            shell=True
        )

        print(f"""
====================================
          JARVIS RUNNING
====================================
Frontend : {FRONTEND_URL}
Backend  : {BACKEND_URL}
Swagger  : {BACKEND_URL}/docs

Expected windows:
1. FastAPI backend
2. React frontend
3. Wake word listener

The listener window should say:
Listening for wake word... Press Ctrl+C to stop.
====================================
""")

        while True:
            time.sleep(1)

    except KeyboardInterrupt:
        print("\nStopping Jarvis...")

        for process in processes:
            try:
                process.terminate()
            except Exception:
                pass

        print("Jarvis stopped.")


if __name__ == "__main__":
    main()