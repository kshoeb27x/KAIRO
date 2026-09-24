"""Install JARVIS into the Windows Startup folder.

Creates a shortcut in the current user's Startup folder that points to
Start_JARVIS.vbs, causing JARVIS to launch silently on every login.

Usage:
    python install_startup.py

This script is idempotent — safe to run multiple times.
"""

from __future__ import annotations

import logging
import platform
import sys
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
)
logger = logging.getLogger("jarvis.installer")


def get_startup_folder() -> Path:
    """Return the current user's Windows Startup folder."""
    appdata = Path.home() / "AppData" / "Roaming"
    startup = appdata / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Startup"
    if not startup.exists():
        raise FileNotFoundError(f"Startup folder not found: {startup}")
    return startup


def get_vbs_path() -> Path:
    """Return the absolute path to Start_JARVIS.vbs next to this script."""
    vbs = Path(__file__).resolve().parent / "Start_JARVIS.vbs"
    if not vbs.exists():
        raise FileNotFoundError(f"Start_JARVIS.vbs not found: {vbs}")
    return vbs


def create_shortcut(startup_folder: Path, target_vbs: Path) -> Path:
    """Create a .lnk shortcut in the Startup folder pointing to the VBS."""
    try:
        import win32com.client  # type: ignore[import-untyped]
    except ImportError:
        # Fallback: copy the VBS directly into Startup
        logger.warning("pywin32 not installed — copying VBS directly to Startup folder.")
        dest = startup_folder / "JARVIS.vbs"
        import shutil
        shutil.copy2(str(target_vbs), str(dest))
        logger.info("Copied %s -> %s", target_vbs, dest)
        return dest

    shortcut_path = startup_folder / "JARVIS.lnk"
    shell = win32com.client.Dispatch("WScript.Shell")
    shortcut = shell.CreateShortcut(str(shortcut_path))
    shortcut.TargetPath = str(target_vbs)
    shortcut.WorkingDirectory = str(target_vbs.parent)
    shortcut.Description = "JARVIS AI Assistant — Silent Startup"
    shortcut.Save()
    return shortcut_path


def main() -> int:
    if platform.system() != "Windows":
        logger.error("This installer only supports Windows.")
        return 1

    try:
        startup_folder = get_startup_folder()
        logger.info("Startup folder: %s", startup_folder)

        vbs_path = get_vbs_path()
        logger.info("VBS launcher: %s", vbs_path)

        shortcut_path = create_shortcut(startup_folder, vbs_path)
        logger.info("Startup shortcut installed: %s", shortcut_path)
        logger.info("JARVIS will now start automatically on Windows login.")
        return 0
    except Exception:
        logger.exception("Installation failed.")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
