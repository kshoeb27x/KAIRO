from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[2]
CORE_ROOT = PROJECT_ROOT / "01_CORE"
AGENTS_ROOT = PROJECT_ROOT / "02_AGENTS"

if str(AGENTS_ROOT) not in sys.path:
    sys.path.insert(0, str(AGENTS_ROOT))

if str(CORE_ROOT) not in sys.path:
    sys.path.insert(0, str(CORE_ROOT))

from Orchestration.orchestrator import KairoOrchestrator

__all__ = ["KairoOrchestrator"]
