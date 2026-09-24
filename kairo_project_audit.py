from pathlib import Path
from collections import defaultdict
from datetime import datetime
import hashlib
import json
import os

PROJECT_ROOT = Path(__file__).resolve().parent

PROTECTED = {
    "00_FOUNDATION",
    "11_ARCHIVE",
    "15_ROLLBACK_SNAPSHOTS",
}

SKIP_DIRS = {
    ".git",
}

HASH_CHUNK = 1024 * 1024


def sha256_file(path):
    h = hashlib.sha256()

    try:
        with path.open("rb") as f:
            while True:
                chunk = f.read(HASH_CHUNK)
                if not chunk:
                    break
                h.update(chunk)

        return h.hexdigest()

    except Exception:
        return None


def format_size(size):
    if size >= 1024 ** 3:
        return f"{size / (1024 ** 3):.2f} GB"

    if size >= 1024 ** 2:
        return f"{size / (1024 ** 2):.2f} MB"

    if size >= 1024:
        return f"{size / 1024:.2f} KB"

    return f"{size} B"


def is_skipped(path):
    return any(part in SKIP_DIRS for part in path.parts)


def classify(path):
    name = path.name.lower()

    if "__pycache__" in path.parts:
        return "GENERATED_CACHE"

    if name.endswith(".pyc"):
        return "GENERATED_CACHE"

    if "rollback" in str(path).lower():
        return "ROLLBACK"

    if "snapshot" in str(path).lower():
        return "ROLLBACK"

    if "archive" in str(path).lower():
        return "ARCHIVE"

    if "report" in str(path).lower():
        return "REPORT"

    if "validation" in str(path).lower():
        return "VALIDATION"

    if "build" in name:
        return "BUILD_TOOL"

    if "live_check" in name:
        return "LIVE_CHECK"

    return "PROJECT"


def top_level(path):
    try:
        relative = path.relative_to(PROJECT_ROOT)

        if len(relative.parts) == 0:
            return PROJECT_ROOT.name

        return relative.parts[0]

    except Exception:
        return "UNKNOWN"


def main():
    started = datetime.now()

    files = []
    directories = []

    total_bytes = 0
    errors = []

    extension_stats = defaultdict(lambda: {
        "files": 0,
        "bytes": 0,
    })

    top_level_stats = defaultdict(lambda: {
        "files": 0,
        "bytes": 0,
    })

    category_stats = defaultdict(lambda: {
        "files": 0,
        "bytes": 0,
    })

    size_groups = defaultdict(list)

    print("=" * 80)
    print("KAIRO PROJECT-WIDE AUDIT")
    print("=" * 80)
    print(f"Project: {PROJECT_ROOT}")
    print()
    print("Scanning entire project...")
    print("No files will be deleted or modified.")
    print()

    for root, dirnames, filenames in os.walk(PROJECT_ROOT):

        root_path = Path(root)

        # Remove directories we intentionally don't traverse.
        dirnames[:] = [
            d for d in dirnames
            if d not in SKIP_DIRS
        ]

        directories.append(root_path)

        for filename in filenames:

            path = root_path / filename

            try:
                if not path.is_file():
                    continue

                size = path.stat().st_size

                files.append(path)
                total_bytes += size

                ext = path.suffix.lower() or "[no extension]"
                top = top_level(path)
                category = classify(path)

                extension_stats[ext]["files"] += 1
                extension_stats[ext]["bytes"] += size

                top_level_stats[top]["files"] += 1
                top_level_stats[top]["bytes"] += size

                category_stats[category]["files"] += 1
                category_stats[category]["bytes"] += size

                size_groups[size].append(path)

            except Exception as exc:
                errors.append({
                    "path": str(path),
                    "error": repr(exc),
                })

    print(f"Files:       {len(files):,}")
    print(f"Directories: {len(directories):,}")
    print(f"Storage:     {format_size(total_bytes)}")
    print(f"Errors:      {len(errors):,}")
    print()

    # ------------------------------------------------------------------
    # TOP LEVEL STORAGE
    # ------------------------------------------------------------------

    print("-" * 80)
    print("TOP-LEVEL STORAGE")
    print("-" * 80)

    for name, data in sorted(
        top_level_stats.items(),
        key=lambda x: x[1]["bytes"],
        reverse=True
    ):
        print(
            f"{name:<35}"
            f"{data['files']:>10,} files   "
            f"{format_size(data['bytes']):>12}"
        )

    # ------------------------------------------------------------------
    # CATEGORY STORAGE
    # ------------------------------------------------------------------

    print()
    print("-" * 80)
    print("CATEGORY ANALYSIS")
    print("-" * 80)

    for name, data in sorted(
        category_stats.items(),
        key=lambda x: x[1]["bytes"],
        reverse=True
    ):
        print(
            f"{name:<25}"
            f"{data['files']:>10,} files   "
            f"{format_size(data['bytes']):>12}"
        )

    # ------------------------------------------------------------------
    # EXTENSIONS
    # ------------------------------------------------------------------

    print()
    print("-" * 80)
    print("FILE TYPES")
    print("-" * 80)

    for ext, data in sorted(
        extension_stats.items(),
        key=lambda x: x[1]["bytes"],
        reverse=True
    )[:40]:

        print(
            f"{ext:<20}"
            f"{data['files']:>10,} files   "
            f"{format_size(data['bytes']):>12}"
        )

    # ------------------------------------------------------------------
    # LARGEST FILES
    # ------------------------------------------------------------------

    print()
    print("-" * 80)
    print("LARGEST FILES")
    print("-" * 80)

    largest = []

    for path in files:
        try:
            largest.append((path.stat().st_size, path))
        except Exception:
            pass

    largest.sort(reverse=True)

    for size, path in largest[:100]:

        relative = path.relative_to(PROJECT_ROOT)

        print(
            f"{format_size(size):>12}  {relative}"
        )

    # ------------------------------------------------------------------
    # DUPLICATE CANDIDATES
    # ------------------------------------------------------------------

    duplicate_size_groups = {
        size: paths
        for size, paths in size_groups.items()
        if len(paths) > 1
    }

    print()
    print("-" * 80)
    print("DUPLICATE CANDIDATES")
    print("-" * 80)

    print(
        f"Same-size groups: "
        f"{len(duplicate_size_groups):,}"
    )

    candidate_files = sum(
        len(paths)
        for paths in duplicate_size_groups.values()
    )

    print(
        f"Candidate files:  "
        f"{candidate_files:,}"
    )

    # ------------------------------------------------------------------
    # EXACT DUPLICATES
    # ------------------------------------------------------------------

    print()
    print("-" * 80)
    print("EXACT DUPLICATE HASH SCAN")
    print("-" * 80)

    exact_duplicates = []
    hashed_files = 0

    for size, paths in sorted(
        duplicate_size_groups.items(),
        key=lambda x: x[0],
        reverse=True
    ):

        hashes = defaultdict(list)

        for path in paths:

            digest = sha256_file(path)
            hashed_files += 1

            if digest:
                hashes[digest].append(path)

        for digest, matching_paths in hashes.items():

            if len(matching_paths) > 1:

                exact_duplicates.append({
                    "sha256": digest,
                    "size": size,
                    "files": [
                        str(p.relative_to(PROJECT_ROOT))
                        for p in matching_paths
                    ],
                })

    duplicate_bytes = 0

    for group in exact_duplicates:
        duplicate_bytes += group["size"] * (len(group["files"]) - 1)

    print(
        f"Files hashed:          {hashed_files:,}"
    )

    print(
        f"Exact duplicate groups: {len(exact_duplicates):,}"
    )

    print(
        f"Potential reclaimable:  {format_size(duplicate_bytes)}"
    )

    # ------------------------------------------------------------------
    # EMPTY DIRECTORIES
    # ------------------------------------------------------------------

    empty_directories = []

    for directory in directories:

        try:
            if not any(directory.iterdir()):
                empty_directories.append(
                    str(directory.relative_to(PROJECT_ROOT))
                )
        except Exception:
            pass

    print()
    print("-" * 80)
    print("EMPTY DIRECTORIES")
    print("-" * 80)

    print(
        f"Empty directories: {len(empty_directories):,}"
    )

    # ------------------------------------------------------------------
    # REPORT
    # ------------------------------------------------------------------

    report = {
        "audit": "KAIRO PROJECT-WIDE AUDIT",
        "started_at": started.isoformat(),
        "completed_at": datetime.now().isoformat(),
        "project_root": str(PROJECT_ROOT),

        "summary": {
            "files": len(files),
            "directories": len(directories),
            "total_bytes": total_bytes,
            "total_size": format_size(total_bytes),
            "errors": len(errors),
        },

        "top_level": {
            name: {
                "files": data["files"],
                "bytes": data["bytes"],
                "size": format_size(data["bytes"]),
            }
            for name, data in top_level_stats.items()
        },

        "categories": {
            name: {
                "files": data["files"],
                "bytes": data["bytes"],
                "size": format_size(data["bytes"]),
            }
            for name, data in category_stats.items()
        },

        "extensions": {
            ext: {
                "files": data["files"],
                "bytes": data["bytes"],
                "size": format_size(data["bytes"]),
            }
            for ext, data in extension_stats.items()
        },

        "exact_duplicates": exact_duplicates,

        "duplicate_summary": {
            "same_size_groups": len(duplicate_size_groups),
            "candidate_files": candidate_files,
            "exact_duplicate_groups": len(exact_duplicates),
            "potential_reclaimable_bytes": duplicate_bytes,
            "potential_reclaimable": format_size(duplicate_bytes),
        },

        "empty_directories": empty_directories,

        "errors": errors,
    }

    output = PROJECT_ROOT / "kairo_project_audit.json"

    output.write_text(
        json.dumps(report, indent=2),
        encoding="utf-8"
    )

    print()
    print("=" * 80)
    print("AUDIT COMPLETE")
    print("=" * 80)
    print(f"Report: {output}")
    print()
    print("IMPORTANT:")
    print("This audit DID NOT delete, move, copy, or modify project files.")
    print("=" * 80)


if __name__ == "__main__":
    main()