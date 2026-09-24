from pathlib import Path
from datetime import datetime
import shutil
import json
import hashlib

ROOT = Path(__file__).resolve().parents[1]

SOURCE = ROOT
SNAPSHOT_ROOT = ROOT / "15_ROLLBACK_SNAPSHOTS"
SNAPSHOT = SNAPSHOT_ROOT / (
    "KAIRO_BEFORE_PRODUCTION_"
    + datetime.now().strftime("%Y%m%d_%H%M%S")
)

EXCLUDE = {
    ".git",
    ".venv",
    "venv",
    "node_modules",
    "__pycache__",
    ".pytest_cache",
    "12_EXTRACTION",
    "13_FINAL_KAIRO",
    "14_KAIRO_PRODUCTION_CANDIDATE",
    "15_ROLLBACK_SNAPSHOTS",
}

print("=" * 70)
print("KAIRO ROLLBACK SNAPSHOT V1")
print("=" * 70)

print()
print("SAFETY")
print("Production modification : NO")
print("Deletion                : NO")
print("Source repositories     : PROTECTED")
print("Frozen archive          : PROTECTED")
print("Code execution          : NO")
print("Network                 : NO")
print()

SNAPSHOT.mkdir(parents=True, exist_ok=True)

records = []
files_copied = 0
files_skipped = 0

for path in ROOT.rglob("*"):

    if not path.is_file():
        continue

    try:
        rel = path.relative_to(ROOT)
    except ValueError:
        continue

    parts = set(rel.parts)

    if parts.intersection(EXCLUDE):
        continue

    target = SNAPSHOT / rel

    try:
        target.parent.mkdir(
            parents=True,
            exist_ok=True
        )

        shutil.copy2(path, target)

        h = hashlib.sha256()

        with target.open("rb") as f:
            for chunk in iter(
                lambda: f.read(1024 * 1024),
                b""
            ):
                h.update(chunk)

        records.append({
            "path": str(rel),
            "size": target.stat().st_size,
            "sha256": h.hexdigest(),
        })

        files_copied += 1

        if files_copied % 1000 == 0:
            print(
                f"  Snapshot files: {files_copied:,}"
            )

    except (
        FileNotFoundError,
        PermissionError,
        OSError
    ) as exc:

        files_skipped += 1

        records.append({
            "path": str(rel),
            "status": "SKIPPED",
            "error": str(exc),
        })

manifest = {
    "snapshot_type":
        "KAIRO_PRE_PRODUCTION_ROLLBACK",

    "created_at":
        datetime.now().isoformat(
            timespec="seconds"
        ),

    "snapshot":
        str(SNAPSHOT),

    "files_copied":
        files_copied,

    "files_skipped":
        files_skipped,

    "production_modified":
        False,

    "deletion_performed":
        False,

    "source_protected":
        True,

    "archive_protected":
        True,

    "records":
        records,
}

(SNAPSHOT / "SNAPSHOT_MANIFEST.json").write_text(
    json.dumps(
        manifest,
        indent=2,
        ensure_ascii=False
    ),
    encoding="utf-8"
)

print()
print("=" * 70)
print("ROLLBACK SNAPSHOT COMPLETE")
print("=" * 70)

print(
    f"Files copied  : {files_copied:,}"
)

print(
    f"Files skipped : {files_skipped:,}"
)

print(
    f"Snapshot      : {SNAPSHOT}"
)

print()
print("Production modified : NO")
print("Deletion            : NO")
print("Source protected    : YES")
print("Archive protected   : YES")

if files_skipped == 0:
    print()
    print("STATUS: PASS")
    print(
        "NEXT: CONTROLLED PRODUCTION MERGE"
    )
else:
    print()
    print("STATUS: REVIEW_REQUIRED")
    print(
        "NEXT: REVIEW SKIPPED SNAPSHOT FILES"
    )
