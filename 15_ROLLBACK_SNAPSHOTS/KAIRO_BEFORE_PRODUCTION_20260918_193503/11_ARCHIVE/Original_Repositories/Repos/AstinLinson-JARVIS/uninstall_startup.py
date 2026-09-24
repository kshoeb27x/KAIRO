"""Remove the JARVIS startup shortcut from the Windows Startup folder.

Usage:
    python uninstall_startup.py

This script is idempotent — safe to run even if no shortcut exists.
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
logger = logging.getLogger("jarvis.uninstaller")


def get_startup_folder() -> Path:
    """Return the current user's Windows Startup folder."""
    appdata = Path.home() / "AppData" / "Roaming"
    startup = appdata / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Startup"
    return startup


def main() -> int:
    if platform.system() != "Windows":
        logger.error("This uninstaller only supports Windows.")
        return 1

    startup = get_startup_folder()

    removed_any = False
    for name in ("JARVIS.lnk", "JARVIS.vbs"):
        target = startup / name
        if target.exists():
            target.unlink()
            logger.info("Removed: %s", target)
            removed_any = True

    if removed_any:
        logger.info("JARVIS startup entry removed. It will no longer start on login.")
    else:
        logger.info("No JARVIS startup entry found. Nothing to remove.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
