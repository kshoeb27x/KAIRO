from pathlib import Path
from datetime import datetime
import shutil
import json
import hashlib

ROOT = Path(__file__).resolve().parents[1]

FINAL = ROOT / "13_FINAL_KAIRO"
CANDIDATE = ROOT / "14_KAIRO_PRODUCTION_CANDIDATE"

EXCLUDED = {
    ".git",
    ".venv",
    "venv",
    "node_modules",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    "dist",
    "build",
    "coverage",
}

print("=" * 70)
print("KAIRO CONTROLLED PRODUCTION MERGE V1")
print("=" * 70)

print()
print("SAFETY")
print("Current KAIRO          : PROTECTED")
print("Frozen archive         : PROTECTED")
print("Source repositories    : PROTECTED")
print("Production overwrite   : DISABLED")
print("Deletion               : DISABLED")
print("Code execution         : DISABLED")
print("Dependency installation: DISABLED")
print("Network                : NOT USED")
print()

if not FINAL.exists():
    print("STATUS: FAIL")
    print("13_FINAL_KAIRO does not exist.")
    raise SystemExit(1)

if CANDIDATE.exists():
    print("Existing production candidate detected.")
    print("Refreshing candidate...")
    shutil.rmtree(CANDIDATE)

CANDIDATE.mkdir(parents=True, exist_ok=True)

records = []
copied = 0
skipped = 0

for source in FINAL.rglob("*"):

    if not source.is_file():
        continue

    rel = source.relative_to(FINAL)

    if any(part in EXCLUDED for part in rel.parts):
        continue

    # Never bring manifests/reports into application layers.
    if rel.parts and rel.parts[0] in {
        "MANIFEST",
        "REPORTS"
    }:
        continue

    target = CANDIDATE / rel

    try:
        target.parent.mkdir(
            parents=True,
            exist_ok=True
        )

        shutil.copy2(source, target)

        h = hashlib.sha256()

        with target.open("rb") as f:
            for chunk in iter(
                lambda: f.read(1024 * 1024),
                b""
            ):
                h.update(chunk)

        records.append({
            "source": str(rel),
            "target": str(rel),
            "status": "COPIED",
            "size": target.stat().st_size,
            "sha256": h.hexdigest(),
        })

        copied += 1

        if copied % 100 == 0:
            print(
                f"[{copied:5d}] COPIED"
            )

    except Exception as exc:
        skipped += 1

        records.append({
            "source": str(rel),
            "status": "SKIPPED",
            "error": str(exc),
        })

print()
print("=" * 70)
print("CONTROLLED MERGE COMPLETE")
print("=" * 70)

manifest = {
    "type":
        "KAIRO_CONTROLLED_PRODUCTION_CANDIDATE",

    "created_at":
        datetime.now().isoformat(
            timespec="seconds"
        ),

    "source":
        str(FINAL),

    "candidate":
        str(CANDIDATE),

    "files_copied":
        copied,

    "files_skipped":
        skipped,

    "current_production_modified":
        False,

    "source_repositories_modified":
        False,

    "frozen_archive_modified":
        False,

    "deletion_performed":
        False,

    "code_executed":
        False,

    "dependencies_installed":
        False,

    "network_used":
        False,

    "records":
        records,
}

manifest_dir = CANDIDATE / "MANIFEST"
manifest_dir.mkdir(exist_ok=True)

(manifest_dir / "CONTROLLED_MERGE_MANIFEST.json").write_text(
    json.dumps(
        manifest,
        indent=2,
        ensure_ascii=False
    ),
    encoding="utf-8"
)

print(
    f"Final KAIRO files : {copied:,}"
)

print(
    f"Skipped           : {skipped:,}"
)

print(
    f"Candidate         : {CANDIDATE}"
)

print()
print("Current KAIRO      : UNTOUCHED")
print("Source repositories: PROTECTED")
print("Frozen archive     : PROTECTED")
print("Deletion          : NONE")

if copied > 0 and skipped == 0:
    print()
    print("STATUS: PASS")
    print(
        "NEXT: PRODUCTION CANDIDATE VALIDATION"
    )
else:
    print()
    print("STATUS: REVIEW_REQUIRED")
    print(
        "NEXT: REVIEW MERGE SKIPS"
    )
