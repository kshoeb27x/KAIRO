from pathlib import Path
from datetime import datetime
import shutil
import hashlib
import json

ROOT = Path(__file__).resolve().parents[1]

SNAPSHOT_ROOT = ROOT / "15_ROLLBACK_SNAPSHOTS"
SNAPSHOT = SNAPSHOT_ROOT / (
    "KAIRO_PRODUCTION_"
    + datetime.now().strftime("%Y%m%d_%H%M%S")
)

LAYERS = [
    "00_FOUNDATION",
    "01_CORE",
    "02_AGENTS",
    "03_DATA",
    "04_TOOLS",
    "05_UI",
    "06_SECURITY",
    "07_RUNTIME",
    "08_BUSINESS",
    "09_INFRASTRUCTURE",
    "10_DOCUMENTATION",
    "src",
    "config",
    "scripts",
]

ROOT_FILES = [
    "README.md",
    "requirements.txt",
    "requirements-dev.txt",
    "pyproject.toml",
    "pytest.ini",
    ".gitignore",
    ".env.example",
]

EXCLUDED_DIRS = {
    ".git",
    ".venv",
    "venv",
    "env",
    "node_modules",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    ".tox",
    ".cache",
    "dist",
    "build",
    "coverage",
}

EXCLUDED_TOP_LEVEL = {
    "11_ARCHIVE",
    "12_EXTRACTION",
    "13_FINAL_KAIRO",
    "14_KAIRO_PRODUCTION_CANDIDATE",
    "15_ROLLBACK_SNAPSHOTS",
}

records = []
copied = 0
skipped = 0

def sha256(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

def copy_file(src, dst):
    global copied, skipped

    try:
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)

        records.append({
            "path": str(src.relative_to(ROOT)),
            "status": "COPIED",
            "size": dst.stat().st_size,
            "sha256": sha256(dst),
        })

        copied += 1

        if copied % 500 == 0:
            print(f"  Snapshot files: {copied:,}")

    except (OSError, PermissionError, FileNotFoundError) as e:
        skipped += 1
        records.append({
            "path": str(src.relative_to(ROOT)),
            "status": "SKIPPED",
            "error": str(e),
        })

def copy_tree(source):
    if not source.exists():
        return

    for path in source.rglob("*"):

        if not path.is_file():
            continue

        try:
            rel = path.relative_to(source)
        except ValueError:
            continue

        parts = set(rel.parts)

        if parts.intersection(EXCLUDED_DIRS):
            continue

        # NEVER snapshot the original repository collection.
        full_rel = path.relative_to(ROOT)
        full_parts = set(full_rel.parts)

        if "11_ARCHIVE" in full_parts:
            continue

        if "12_EXTRACTION" in full_parts:
            continue

        if "13_FINAL_KAIRO" in full_parts:
            continue

        if "14_KAIRO_PRODUCTION_CANDIDATE" in full_parts:
            continue

        if "15_ROLLBACK_SNAPSHOTS" in full_parts:
            continue

        text = str(full_rel).replace("\\", "/").lower()

        if text.startswith(
            "00_foundation/architecture/old_repositories/"
        ):
            continue

        destination = SNAPSHOT / full_rel

        copy_file(path, destination)

print("=" * 70)
print("KAIRO TARGETED PRODUCTION ROLLBACK SNAPSHOT V2")
print("=" * 70)

print()
print("SAFETY")
print("Current production modified : NO")
print("Deletion                    : NO")
print("Source repositories         : PROTECTED")
print("Frozen archive              : PROTECTED")
print("Code execution              : NO")
print("Network                     : NO")
print()

SNAPSHOT.mkdir(parents=True, exist_ok=True)

for layer in LAYERS:
    source = ROOT / layer

    if not source.exists():
        continue

    print(f"Snapshotting: {layer}")

    copy_tree(source)

for filename in ROOT_FILES:
    source = ROOT / filename

    if source.exists():
        copy_file(
            source,
            SNAPSHOT / filename
        )

manifest = {
    "type": "KAIRO_TARGETED_PRODUCTION_ROLLBACK",
    "created_at": datetime.now().isoformat(timespec="seconds"),
    "snapshot": str(SNAPSHOT),
    "files_copied": copied,
    "files_skipped": skipped,
    "source_repositories_included": False,
    "frozen_archive_included": False,
    "extraction_workspace_included": False,
    "production_modified": False,
    "deletion_performed": False,
    "code_executed": False,
    "network_used": False,
    "records": records,
}

manifest_path = SNAPSHOT / "SNAPSHOT_MANIFEST.json"

manifest_path.write_text(
    json.dumps(
        manifest,
        indent=2,
        ensure_ascii=False
    ),
    encoding="utf-8"
)

print()
print("=" * 70)
print("TARGETED ROLLBACK SNAPSHOT COMPLETE")
print("=" * 70)

print(f"Files copied  : {copied:,}")
print(f"Files skipped : {skipped:,}")
print(f"Snapshot      : {SNAPSHOT}")

print()
print("Source repositories : NOT INCLUDED")
print("Frozen archive      : NOT INCLUDED")
print("Production modified : NO")
print("Deletion            : NO")

if copied > 0 and skipped == 0:
    print()
    print("STATUS: PASS")
    print("NEXT: CONTROLLED PRODUCTION MERGE")
elif copied > 0:
    print()
    print("STATUS: REVIEW_REQUIRED")
    print("NEXT: REVIEW ONLY THE SKIPPED PRODUCTION FILES")
else:
    print()
    print("STATUS: FAIL")
