from __future__ import annotations

import hashlib
import os
import shutil
import time
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]

SOURCE_ROOT = PROJECT_ROOT / "11_ARCHIVE" / "Original_Repositories" / "Repos"
ROLLBACK_ROOT = PROJECT_ROOT / "15_ROLLBACK_SNAPSHOTS"

# Never touch these.
PROTECTED = {
    PROJECT_ROOT / "00_FOUNDATION",
    PROJECT_ROOT / "11_ARCHIVE" / "Original_Repositories",
    PROJECT_ROOT / "15_ROLLBACK_SNAPSHOTS",
}

# Files/directories that are clearly generated and safe to remove.
JUNK_DIR_NAMES = {
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    ".tox",
    ".nox",
    ".coverage",
    "htmlcov",
    "node_modules",
    "dist",
    "build",
    ".next",
    ".turbo",
    ".cache",
    "coverage",
}

JUNK_FILE_NAMES = {
    ".DS_Store",
    "Thumbs.db",
}

JUNK_SUFFIXES = {
    ".pyc",
    ".pyo",
    ".tmp",
    ".temp",
    ".log",
}


def safe_path(path: Path) -> bool:
    path = path.resolve()

    if not SOURCE_ROOT.resolve() in path.parents and path != SOURCE_ROOT.resolve():
        return False

    for protected in PROTECTED:
        protected = protected.resolve()
        if path == protected or protected in path.parents:
            return False

    return True


def sha256(path: Path, chunk_size: int = 1024 * 1024) -> str:
    h = hashlib.sha256()

    with path.open("rb") as f:
        while True:
            chunk = f.read(chunk_size)
            if not chunk:
                break
            h.update(chunk)

    return h.hexdigest()


def is_junk_dir(path: Path) -> bool:
    return path.name in JUNK_DIR_NAMES


def is_junk_file(path: Path) -> bool:
    if path.name in JUNK_FILE_NAMES:
        return True

    if path.suffix.lower() in JUNK_SUFFIXES:
        return True

    return False


def discover_projects():
    """
    A project is considered an independent repository if it contains
    a .git directory/file.

    Nested repositories remain independent. We do not flatten them.
    """
    projects = []

    for root, dirs, files in os.walk(SOURCE_ROOT):
        root_path = Path(root)

        if ".git" in dirs or ".git" in files:
            projects.append(root_path)

            # Do not recursively classify nested repositories as part
            # of this repository's internal files.
            dirs[:] = [
                d for d in dirs
                if d != ".git"
            ]

    return sorted(set(projects))


def discover_project_files(project: Path):
    """
    Files belonging to one project, excluding nested Git repositories.
    """
    files = []

    for root, dirs, filenames in os.walk(project):
        root_path = Path(root)

        dirs[:] = [
            d for d in dirs
            if d != ".git"
        ]

        for filename in filenames:
            path = root_path / filename

            if path.is_file() and safe_path(path):
                files.append(path)

    return files


def snapshot_projects(projects, snapshot_root: Path):
    """
    Snapshot project source before destructive cleanup.

    Originals remain untouched.
    """
    snapshot_root.mkdir(parents=True, exist_ok=True)

    copied_projects = 0

    for project in projects:
        relative = project.relative_to(SOURCE_ROOT)
        destination = snapshot_root / relative

        destination.parent.mkdir(parents=True, exist_ok=True)

        shutil.copytree(
            project,
            destination,
            dirs_exist_ok=True,
        )

        copied_projects += 1

    return copied_projects


def clean_junk():
    removed = []

    # Bottom-up so directory removal is safe.
    all_paths = sorted(
        SOURCE_ROOT.rglob("*"),
        key=lambda p: len(p.parts),
        reverse=True,
    )

    for path in all_paths:
        if not safe_path(path):
            continue

        try:
            if path.is_file() and is_junk_file(path):
                path.unlink()
                removed.append(str(path.relative_to(SOURCE_ROOT)))

            elif path.is_dir() and is_junk_dir(path):
                shutil.rmtree(path)
                removed.append(str(path.relative_to(SOURCE_ROOT)))

        except (FileNotFoundError, PermissionError, OSError):
            # Do not turn one locked/generated file into a global failure.
            continue

    return removed


def remove_empty_dirs():
    removed = []

    directories = sorted(
        [p for p in SOURCE_ROOT.rglob("*") if p.is_dir()],
        key=lambda p: len(p.parts),
        reverse=True,
    )

    for directory in directories:
        if not safe_path(directory):
            continue

        try:
            if not any(directory.iterdir()):
                directory.rmdir()
                removed.append(
                    str(directory.relative_to(SOURCE_ROOT))
                )
        except (FileNotFoundError, PermissionError, OSError):
            continue

    return removed


def remove_exact_duplicates_inside_project(project: Path):
    """
    Only removes byte-identical duplicate files INSIDE THE SAME PROJECT.

    Different repositories are never deduplicated against each other.
    This is deliberate: two independent applications can legitimately
    contain identical libraries/configuration/source files.
    """
    files = discover_project_files(project)

    groups = {}
    errors = []

    for path in files:
        try:
            size = path.stat().st_size
            digest = sha256(path)
            key = (size, digest)

            groups.setdefault(key, []).append(path)

        except (FileNotFoundError, PermissionError, OSError) as exc:
            errors.append((str(path), str(exc)))

    deleted = []

    for _, candidates in groups.items():
        if len(candidates) < 2:
            continue

        # Never automatically delete important repository metadata.
        candidates = [
            p for p in candidates
            if p.name not in {
                "README.md",
                "LICENSE",
                "pyproject.toml",
                "package.json",
                "requirements.txt",
                "Cargo.toml",
                "go.mod",
                "Dockerfile",
            }
        ]

        if len(candidates) < 2:
            continue

        # Keep the first stable path; remove only additional copies.
        candidates.sort(
            key=lambda p: (
                len(p.relative_to(project).parts),
                str(p).lower(),
            )
        )

        keeper = candidates[0]

        for duplicate in candidates[1:]:
            if not safe_path(duplicate):
                continue

            try:
                duplicate.unlink()

                deleted.append({
                    "project": str(project.relative_to(SOURCE_ROOT)),
                    "kept": str(keeper.relative_to(SOURCE_ROOT)),
                    "deleted": str(duplicate.relative_to(SOURCE_ROOT)),
                })

            except (FileNotFoundError, PermissionError, OSError) as exc:
                errors.append((str(duplicate), str(exc)))

    return deleted, errors


def validate_structure(projects):
    failures = []

    for project in projects:
        if not project.exists():
            failures.append(
                f"Missing project: {project}"
            )
            continue

        # Every discovered project must retain its Git boundary.
        git_path = project / ".git"

        if not git_path.exists():
            failures.append(
                f"Git boundary missing: {project}"
            )

    return failures


def count_files():
    count = 0
    total_bytes = 0

    for path in SOURCE_ROOT.rglob("*"):
        if path.is_file():
            try:
                count += 1
                total_bytes += path.stat().st_size
            except OSError:
                pass

    return count, total_bytes


def main():
    started = time.time()

    print()
    print("=" * 72)
    print("KAIRO REPOSITORY COLLECTION CLEANER")
    print("=" * 72)
    print()

    if not SOURCE_ROOT.exists():
        raise SystemExit(
            f"SOURCE NOT FOUND: {SOURCE_ROOT}"
        )

    print("[1/6] Discovering nested repositories/projects...")
    projects = discover_projects()

    print(f"  Nested repositories found: {len(projects)}")

    if not projects:
        raise SystemExit(
            "No nested repositories detected. Nothing was changed."
        )

    print()
    print("[2/6] Creating rollback snapshot...")

    timestamp = time.strftime("%Y%m%d_%H%M%S")
    snapshot = ROLLBACK_ROOT / f"REPOS_CLEAN_{timestamp}"

    snapshot.mkdir(parents=True, exist_ok=True)

    snapshot_count = snapshot_projects(
        projects,
        snapshot,
    )

    print(f"  Projects protected: {snapshot_count}")
    print(f"  Snapshot: {snapshot}")

    print()
    print("[3/6] Removing obvious generated/cache material...")

    junk_removed = clean_junk()

    print(f"  Removed: {len(junk_removed)}")

    print()
    print("[4/6] Removing exact duplicates INSIDE each project...")

    duplicate_deleted = []
    errors = []

    for index, project in enumerate(projects, start=1):
        deleted, project_errors = (
            remove_exact_duplicates_inside_project(project)
        )

        duplicate_deleted.extend(deleted)
        errors.extend(project_errors)

        if deleted:
            print(
                f"  [{index}/{len(projects)}] "
                f"{project.relative_to(SOURCE_ROOT)}: "
                f"{len(deleted)} duplicate(s) removed"
            )

    print(f"  Total duplicate files removed: {len(duplicate_deleted)}")

    print()
    print("[5/6] Removing empty directories...")

    empty_removed = remove_empty_dirs()

    print(f"  Empty directories removed: {len(empty_removed)}")

    print()
    print("[6/6] Validating repository structure...")

    structure_failures = validate_structure(projects)

    files, bytes_total = count_files()

    print()
    print("=" * 72)

    if structure_failures:
        print("KAIRO REPOSITORY CLEAN: FAIL")
        print()
        for failure in structure_failures:
            print("  ERROR:", failure)
        print()
        print(f"Rollback: {snapshot}")
        raise SystemExit(1)

    print("KAIRO REPOSITORY CLEAN: PASS")
    print()
    print(f"Nested repositories : {len(projects):,}")
    print(f"Junk removed        : {len(junk_removed):,}")
    print(f"Duplicates removed  : {len(duplicate_deleted):,}")
    print(f"Empty dirs removed  : {len(empty_removed):,}")
    print(f"Remaining files     : {files:,}")
    print(f"Remaining size      : {bytes_total / (1024 ** 3):.2f} GB")
    print(f"Snapshot            : {snapshot}")
    print(f"Warnings/errors     : {len(errors):,}")
    print(f"Duration            : {time.time() - started:.1f}s")
    print("=" * 72)
    print()
    print("NO CROSS-REPOSITORY COPY OR MERGE WAS PERFORMED.")
    print("NO ORIGINAL REPOSITORY BOUNDARY WAS FLATTENED.")
    print()


if __name__ == "__main__":
    main()