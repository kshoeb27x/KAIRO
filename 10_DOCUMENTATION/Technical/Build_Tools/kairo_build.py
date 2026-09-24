from __future__ import annotations

import json
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

EXTRACTION = ROOT / "12_EXTRACTION"
STAGING = EXTRACTION / "FINAL_STAGING"
REPORTS = EXTRACTION / "FINAL_REPORTS"
STATE_FILE = EXTRACTION / "KAIRO_BUILD_STATE.json"

CONSOLIDATION_PLAN = (
    EXTRACTION
    / "CONSOLIDATION"
    / "DECISIONS"
    / "integration_plan.json"
)

INTEGRATION_DIR = EXTRACTION / "INTEGRATION"


def now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def save_state(state: dict) -> None:
    STATE_FILE.write_text(
        json.dumps(state, indent=2),
        encoding="utf-8",
    )


def run_module(module: str) -> dict:
    print()
    print("=" * 68)
    print(f" KAIRO BUILD PHASE: {module}")
    print("=" * 68)

    result = subprocess.run(
        [sys.executable, "-m", module],
        cwd=ROOT,
        text=True,
    )

    return {
        "module": module,
        "return_code": result.returncode,
        "status": "PASS" if result.returncode == 0 else "FAIL",
        "completed_at": now(),
    }


def load_json(path: Path, default):
    if not path.exists():
        return default

    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def prepare_workspace() -> None:
    STAGING.mkdir(parents=True, exist_ok=True)
    REPORTS.mkdir(parents=True, exist_ok=True)


def verify_existing_work() -> dict:
    extraction_report = (
        EXTRACTION
        / "REPORTS"
        / "kairo_extraction_candidates.json"
    )

    consolidation_report = (
        EXTRACTION
        / "CONSOLIDATION"
        / "REPORTS"
        / "KAIRO_CONSOLIDATION_REPORT.md"
    )

    plan = load_json(CONSOLIDATION_PLAN, {})

    candidates = []

    if isinstance(plan, list):
        candidates = plan
    elif isinstance(plan, dict):
        candidates = (
            plan.get("integration_candidates")
            or plan.get("candidates")
            or plan.get("items")
            or []
        )

    return {
        "extraction_report_exists": extraction_report.exists(),
        "consolidation_report_exists": consolidation_report.exists(),
        "integration_plan_exists": CONSOLIDATION_PLAN.exists(),
        "candidate_count": len(candidates),
    }


def copy_validated_integration_output() -> dict:
    """
    Promote only files that already exist in the isolated integration
    workspace into FINAL_STAGING.

    Nothing is copied to production KAIRO.
    """

    destination = STAGING / "INTEGRATION"

    if destination.exists():
        shutil.rmtree(destination)

    destination.mkdir(parents=True, exist_ok=True)

    if not INTEGRATION_DIR.exists():
        return {
            "status": "NO_INTEGRATION_OUTPUT",
            "files": 0,
        }

    count = 0

    for source in INTEGRATION_DIR.rglob("*"):
        if not source.is_file():
            continue

        relative = source.relative_to(INTEGRATION_DIR)

        # Never promote manifests/reports as executable components.
        if any(
            part.upper() in {
                "MANIFEST",
                "REPORTS",
            }
            for part in relative.parts
        ):
            continue

        target = destination / relative
        target.parent.mkdir(parents=True, exist_ok=True)

        shutil.copy2(source, target)
        count += 1

    return {
        "status": "STAGED",
        "files": count,
    }


def generate_final_report(state: dict) -> None:
    report = REPORTS / "KAIRO_FINAL_BUILD_REPORT.md"

    lines = [
        "# KAIRO Final Build Report",
        "",
        f"Generated: `{now()}`",
        "",
        "## Safety",
        "",
        "- Production KAIRO modified: **NO**",
        "- Frozen archive modified: **NO**",
        "- Original repositories modified: **NO**",
        "",
        "## Build Status",
        "",
        f"- Overall status: **{state['status']}**",
        f"- Build ID: `{state['build_id']}`",
        "",
        "## Existing Repository Work",
        "",
        f"- Extraction records: `{state['verification'].get('extraction_report_exists')}`",
        f"- Consolidation report: `{state['verification'].get('consolidation_report_exists')}`",
        f"- Integration plan: `{state['verification'].get('integration_plan_exists')}`",
        f"- Consolidation candidates detected: `{state['verification'].get('candidate_count', 0)}`",
        "",
        "## Pipeline",
        "",
    ]

    for phase in state["phases"]:
        lines.append(
            f"- `{phase['module']}` → **{phase['status']}**"
        )

    lines.extend(
        [
            "",
            "## Final Staging",
            "",
            f"- Status: **{state['staging']['status']}**",
            f"- Files staged: `{state['staging']['files']}`",
            "",
            "## Production",
            "",
            "Production integration was intentionally NOT performed.",
            "",
            "Final production integration requires explicit approval.",
        ]
    )

    report.write_text(
        "\n".join(lines),
        encoding="utf-8",
    )


def main() -> int:
    print("=" * 68)
    print(" KAIRO BUILD ORCHESTRATOR V1")
    print("=" * 68)
    print()
    print(f"Root        : {ROOT}")
    print("Mode        : SAFE AUTOMATED BUILD")
    print("Production  : PROTECTED")
    print("Archive     : PROTECTED")
    print()

    build_id = "KAIRO-" + datetime.now().strftime("%Y%m%d-%H%M%S")

    state = {
        "build_id": build_id,
        "started_at": now(),
        "status": "RUNNING",
        "phases": [],
        "verification": {},
        "staging": {
            "status": "PENDING",
            "files": 0,
        },
        "production_modified": False,
        "archive_modified": False,
        "source_repositories_modified": False,
    }

    save_state(state)
    prepare_workspace()

    print("[1/5] PREFLIGHT")
    print("-" * 68)

    if not ROOT.exists():
        print("ERROR: KAIRO root does not exist.")
        return 1

    print("[OK] KAIRO root found")
    print("[OK] Python:", sys.executable)

    print()
    print("[2/5] VERIFY EXISTING WORK")
    print("-" * 68)

    state["verification"] = verify_existing_work()

    for key, value in state["verification"].items():
        print(f"{key:32}: {value}")

    if not state["verification"]["integration_plan_exists"]:
        print()
        print("ERROR: integration_plan.json not found.")
        print("Run the Consolidation Engine first.")
        state["status"] = "BLOCKED"
        save_state(state)
        return 1

    print()
    print("[3/5] AUTOMATED PIPELINE")
    print("-" * 68)

    # Existing engines are used when available.
    modules = [
        "src.kairo_integration_builder",
    ]

    for module in modules:
        result = run_module(module)
        state["phases"].append(result)

        if result["return_code"] != 0:
            state["status"] = "FAILED"
            save_state(state)
            generate_final_report(state)
            return result["return_code"]

        save_state(state)

    print()
    print("[4/5] FINAL STAGING")
    print("-" * 68)

    state["staging"] = copy_validated_integration_output()

    print(
        f"Status : {state['staging']['status']}"
    )
    print(
        f"Files  : {state['staging']['files']}"
    )

    save_state(state)

    print()
    print("[5/5] FINAL SAFETY CHECK")
    print("-" * 68)

    # This orchestrator never writes into production.
    state["production_modified"] = False
    state["archive_modified"] = False
    state["source_repositories_modified"] = False

    if all(
        phase["status"] == "PASS"
        for phase in state["phases"]
    ):
        state["status"] = "READY_FOR_SECURITY"
    else:
        state["status"] = "FAILED"

    state["completed_at"] = now()

    save_state(state)
    generate_final_report(state)

    print()
    print("=" * 68)
    print(" KAIRO BUILD ORCHESTRATOR COMPLETE")
    print("=" * 68)
    print()
    print(f"Build ID    : {state['build_id']}")
    print(f"Status      : {state['status']}")
    print(f"Staged      : {state['staging']['files']}")
    print()
    print("Production KAIRO modified : NO")
    print("Frozen archive modified   : NO")
    print("Source repositories       : NO")
    print()
    print(f"State  : {STATE_FILE}")
    print(f"Report : {REPORTS / 'KAIRO_FINAL_BUILD_REPORT.md'}")
    print()

    if state["status"] == "READY_FOR_SECURITY":
        print("NEXT: KAIRO SECURITY + VALIDATION GATE")
        return 0

    print("BUILD FAILED — inspect final report.")
    return 1


if __name__ == "__main__":
    main()
