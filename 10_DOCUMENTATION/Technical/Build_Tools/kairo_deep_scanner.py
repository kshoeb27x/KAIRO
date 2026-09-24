from __future__ import annotations

import ast
import hashlib
import json
import os
import re
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path


# ============================================================
# KAIRO DEEP PROJECT SCANNER
# ============================================================
#
# PURPOSE:
#   Deep read-only inventory of the entire current KAIRO project.
#
# IMPORTANT:
#   This script DOES NOT DELETE, MOVE, MODIFY, OR RENAME files.
#
# OUTPUT:
#   99_DEEP_SCAN_REPORT/
#
# ============================================================


PROJECT_ROOT = Path(__file__).resolve().parents[1]
REPORT_ROOT = PROJECT_ROOT / "99_DEEP_SCAN_REPORT"

# ------------------------------------------------------------
# Protected areas
# ------------------------------------------------------------

PROTECTED_RELATIVE = {
    Path("00_FOUNDATION/Architecture/Old_Repositories"),
    Path("11_ARCHIVE/Original_Repositories"),
    Path("15_ROLLBACK_SNAPSHOTS"),
}

# ------------------------------------------------------------
# Directories that contain generated/dependency material.
#
# They are still detected and reported, but contents are not
# recursively parsed as source code.
# ------------------------------------------------------------

GENERATED_DIR_NAMES = {
    ".git",
    ".svn",
    ".hg",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    ".tox",
    ".venv",
    "venv",
    "env",
    "node_modules",
    "dist",
    "build",
    ".next",
    ".cache",
    "coverage",
    ".coverage",
    "htmlcov",
    "site-packages",
}

# ------------------------------------------------------------
# Junk / generated filename patterns
# ------------------------------------------------------------

JUNK_NAME_PATTERNS = [
    r"^\.DS_Store$",
    r"^Thumbs\.db$",
    r".*\.pyc$",
    r".*\.pyo$",
    r".*\.tmp$",
    r".*\.temp$",
    r".*\.bak$",
    r".*\.backup$",
    r".*\.old$",
    r".*\.orig$",
    r".*\.swp$",
    r".*~$",
]

# ------------------------------------------------------------
# Source/text extensions
# ------------------------------------------------------------

TEXT_EXTENSIONS = {
    ".py",
    ".pyi",
    ".js",
    ".jsx",
    ".ts",
    ".tsx",
    ".json",
    ".jsonl",
    ".yaml",
    ".yml",
    ".toml",
    ".ini",
    ".cfg",
    ".conf",
    ".md",
    ".txt",
    ".rst",
    ".html",
    ".htm",
    ".css",
    ".scss",
    ".less",
    ".xml",
    ".sql",
    ".sh",
    ".ps1",
    ".bat",
    ".cmd",
    ".env",
    ".example",
}

CODE_EXTENSIONS = {
    ".py",
    ".pyi",
    ".js",
    ".jsx",
    ".ts",
    ".tsx",
    ".java",
    ".go",
    ".rs",
    ".cpp",
    ".cc",
    ".c",
    ".h",
    ".hpp",
    ".cs",
    ".php",
    ".rb",
    ".swift",
    ".kt",
    ".kts",
    ".scala",
    ".sql",
    ".sh",
    ".ps1",
}

DEPENDENCY_FILENAMES = {
    "requirements.txt",
    "requirements-dev.txt",
    "requirements-prod.txt",
    "pyproject.toml",
    "poetry.lock",
    "pipfile",
    "pipfile.lock",
    "package.json",
    "package-lock.json",
    "pnpm-lock.yaml",
    "yarn.lock",
    "go.mod",
    "go.sum",
    "cargo.toml",
    "cargo.lock",
    "gemfile",
    "gemfile.lock",
}

CONFIG_FILENAMES = {
    ".env",
    ".env.example",
    ".env.local",
    "config.yaml",
    "config.yml",
    "config.json",
    "settings.py",
    "settings.json",
    "settings.yaml",
    "settings.yml",
}

MAX_AST_SIZE = 5 * 1024 * 1024
MAX_TEXT_NORMALIZE_SIZE = 20 * 1024 * 1024


# ============================================================
# DATA TYPES
# ============================================================

@dataclass
class FileRecord:
    path: str
    relative_path: str
    name: str
    extension: str
    size: int
    sha256: str
    is_text: bool
    is_code: bool
    is_binary: bool
    is_protected: bool
    is_generated_dir: bool
    is_junk_candidate: bool
    normalized_hash: str | None
    python_symbols: list[str]
    python_imports: list[str]


# ============================================================
# HELPERS
# ============================================================

def relative(path: Path) -> Path:
    try:
        return path.relative_to(PROJECT_ROOT)
    except ValueError:
        return path


def is_protected(path: Path) -> bool:
    rel = relative(path)

    for protected in PROTECTED_RELATIVE:
        try:
            rel.relative_to(protected)
            return True
        except ValueError:
            pass

    return False


def contains_generated_dir(path: Path) -> bool:
    parts = relative(path).parts
    return any(part in GENERATED_DIR_NAMES for part in parts)


def is_junk_name(name: str) -> bool:
    return any(re.match(pattern, name, re.IGNORECASE)
               for pattern in JUNK_NAME_PATTERNS)


def is_text_file(path: Path) -> bool:
    return path.suffix.lower() in TEXT_EXTENSIONS or path.name in {
        ".env",
        "Dockerfile",
        "Makefile",
    }


def is_code_file(path: Path) -> bool:
    return path.suffix.lower() in CODE_EXTENSIONS


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()

    with path.open("rb") as handle:
        while True:
            chunk = handle.read(1024 * 1024)

            if not chunk:
                break

            digest.update(chunk)

    return digest.hexdigest()


def read_text_safely(path: Path) -> str | None:
    try:
        return path.read_text(
            encoding="utf-8",
            errors="replace",
        )
    except Exception:
        return None


def normalized_source(text: str) -> str:
    """
    Conservative normalization.

    Purpose:
        Detect likely copied source while avoiding aggressive
        transformations that could produce false positives.
    """

    text = text.replace("\ufeff", "")

    # Remove comments.
    text = re.sub(r"#.*?$", "", text, flags=re.MULTILINE)

    # Remove block comments in common languages.
    text = re.sub(
        r"/\*.*?\*/",
        "",
        text,
        flags=re.DOTALL,
    )

    # Remove whitespace.
    text = re.sub(r"\s+", "", text)

    return text


def normalized_hash(path: Path) -> str | None:
    if not is_text_file(path):
        return None

    try:
        if path.stat().st_size > MAX_TEXT_NORMALIZE_SIZE:
            return None

        text = read_text_safely(path)

        if text is None:
            return None

        normalized = normalized_source(text)

        if not normalized:
            return None

        return hashlib.sha256(
            normalized.encode("utf-8")
        ).hexdigest()

    except Exception:
        return None


# ============================================================
# PYTHON ANALYSIS
# ============================================================

def analyze_python(path: Path) -> tuple[list[str], list[str]]:
    symbols: list[str] = []
    imports: list[str] = []

    if path.stat().st_size > MAX_AST_SIZE:
        return symbols, imports

    try:
        source = read_text_safely(path)

        if source is None:
            return symbols, imports

        tree = ast.parse(source, filename=str(path))

        for node in ast.walk(tree):

            if isinstance(node, (
                ast.FunctionDef,
                ast.AsyncFunctionDef,
                ast.ClassDef,
            )):
                symbols.append(
                    f"{type(node).__name__}:{node.name}"
                )

            elif isinstance(node, ast.Import):
                for alias in node.names:
                    imports.append(alias.name)

            elif isinstance(node, ast.ImportFrom):
                module = node.module or ""

                imports.append(
                    module
                )

    except Exception:
        pass

    return sorted(set(symbols)), sorted(set(imports))


# ============================================================
# SCANNER
# ============================================================

class KairoDeepScanner:

    def __init__(self) -> None:
        self.files: list[FileRecord] = []

        self.stats = Counter()

        self.sha_groups: defaultdict[str, list[str]] = defaultdict(list)
        self.normalized_groups: defaultdict[str, list[str]] = defaultdict(list)

        self.symbol_groups: defaultdict[str, list[str]] = defaultdict(list)
        self.import_groups: defaultdict[str, list[str]] = defaultdict(list)

        self.name_groups: defaultdict[str, list[str]] = defaultdict(list)
        self.extension_groups: Counter[str] = Counter()

        self.directory_stats: defaultdict[str, Counter] = defaultdict(Counter)

        self.large_files: list[dict] = []
        self.junk_candidates: list[str] = []
        self.generated_candidates: list[str] = []

        self.scan_errors: list[dict] = []

    # --------------------------------------------------------
    # Directory pruning
    # --------------------------------------------------------

    def should_skip_directory(self, path: Path) -> bool:
        return path.name in GENERATED_DIR_NAMES

    # --------------------------------------------------------
    # File scan
    # --------------------------------------------------------

    def scan_file(self, path: Path) -> None:

        try:
            stat = path.stat()

            size = stat.st_size
            ext = path.suffix.lower()

            digest = sha256_file(path)

            text = is_text_file(path)
            code = is_code_file(path)
            binary = not text

            protected = is_protected(path)
            generated = contains_generated_dir(path)
            junk = is_junk_name(path.name)

            norm_hash = normalized_hash(path)

            symbols: list[str] = []
            imports: list[str] = []

            if path.suffix.lower() == ".py":
                symbols, imports = analyze_python(path)

            rel = relative(path)

            record = FileRecord(
                path=str(path),
                relative_path=str(rel),
                name=path.name,
                extension=ext,
                size=size,
                sha256=digest,
                is_text=text,
                is_code=code,
                is_binary=binary,
                is_protected=protected,
                is_generated_dir=generated,
                is_junk_candidate=junk,
                normalized_hash=norm_hash,
                python_symbols=symbols,
                python_imports=imports,
            )

            self.files.append(record)

            self.stats["files"] += 1
            self.stats["bytes"] += size

            if text:
                self.stats["text_files"] += 1

            if code:
                self.stats["code_files"] += 1

            if binary:
                self.stats["binary_files"] += 1

            if protected:
                self.stats["protected_files"] += 1

            if generated:
                self.stats["generated_files"] += 1
                self.generated_candidates.append(str(rel))

            if junk:
                self.stats["junk_candidates"] += 1
                self.junk_candidates.append(str(rel))

            if size >= 50 * 1024 * 1024:
                self.large_files.append({
                    "path": str(rel),
                    "size": size,
                })

            self.sha_groups[digest].append(str(rel))

            if norm_hash:
                self.normalized_groups[norm_hash].append(
                    str(rel)
                )

            self.name_groups[path.name.lower()].append(
                str(rel)
            )

            self.extension_groups[ext or "[no extension]"] += 1

            for symbol in symbols:
                self.symbol_groups[symbol].append(
                    str(rel)
                )

            if imports:
                import_key = "|".join(imports)

                self.import_groups[import_key].append(
                    str(rel)
                )

        except Exception as exc:
            self.scan_errors.append({
                "path": str(path),
                "error": repr(exc),
            })

    # --------------------------------------------------------
    # Full scan
    # --------------------------------------------------------

    def scan(self) -> None:

        print()
        print("=" * 72)
        print("KAIRO DEEP FULL PROJECT SCAN")
        print("=" * 72)
        print()
        print(f"PROJECT: {PROJECT_ROOT}")
        print()
        print("READ ONLY: YES")
        print("DELETE: NO")
        print("MOVE: NO")
        print("RENAME: NO")
        print()

        for root, dirs, filenames in os.walk(
            PROJECT_ROOT,
            topdown=True,
            followlinks=False,
        ):

            root_path = Path(root)

            # Do not recursively enter generated/dependency dirs.
            original_dirs = list(dirs)

            dirs[:] = [
                directory
                for directory in dirs
                if directory not in GENERATED_DIR_NAMES
            ]

            skipped = set(original_dirs) - set(dirs)

            for directory in skipped:
                candidate = root_path / directory

                self.generated_candidates.append(
                    str(relative(candidate))
                )

            for filename in filenames:
                path = root_path / filename

                if path.is_symlink():
                    self.stats["symlinks"] += 1
                    continue

                self.scan_file(path)

                if self.stats["files"] % 500 == 0:
                    print(
                        f"Scanned {self.stats['files']:,} files..."
                    )

        print()
        print(
            f"SCAN COMPLETE: {self.stats['files']:,} files"
        )

    # ========================================================
    # REPORT BUILDING
    # ========================================================

    @staticmethod
    def duplicate_groups(
        groups: dict[str, list[str]]
    ) -> list[dict]:

        result = []

        for key, paths in groups.items():

            if len(paths) <= 1:
                continue

            result.append({
                "count": len(paths),
                "hash": key,
                "files": sorted(paths),
            })

        result.sort(
            key=lambda item: item["count"],
            reverse=True,
        )

        return result

    def build_report(self) -> dict:

        exact_duplicates = self.duplicate_groups(
            self.sha_groups
        )

        normalized_duplicates = self.duplicate_groups(
            self.normalized_groups
        )

        duplicate_symbols = {
            symbol: sorted(paths)
            for symbol, paths in self.symbol_groups.items()
            if len(paths) > 1
        }

        duplicate_names = {
            name: sorted(paths)
            for name, paths in self.name_groups.items()
            if len(paths) > 1
        }

        dependency_files = []

        config_files = []

        for record in self.files:

            if record.name.lower() in {
                name.lower()
                for name in DEPENDENCY_FILENAMES
            }:
                dependency_files.append(
                    record.relative_path
                )

            if record.name.lower() in {
                name.lower()
                for name in CONFIG_FILENAMES
            }:
                config_files.append(
                    record.relative_path
                )

        protected_files = [
            record.relative_path
            for record in self.files
            if record.is_protected
        ]

        return {
            "metadata": {
                "scanner": "KAIRO Deep Scanner",
                "version": "V1",
                "timestamp": datetime.now().isoformat(),
                "project_root": str(PROJECT_ROOT),
                "read_only": True,
                "deletion_performed": False,
            },

            "statistics": dict(self.stats),

            "extensions": dict(
                self.extension_groups.most_common()
            ),

            "exact_duplicate_groups": exact_duplicates,

            "normalized_duplicate_groups": (
                normalized_duplicates
            ),

            "duplicate_python_symbols": (
                duplicate_symbols
            ),

            "duplicate_filenames": duplicate_names,

            "dependency_files": sorted(
                dependency_files
            ),

            "config_files": sorted(
                config_files
            ),

            "junk_candidates": sorted(
                set(self.junk_candidates)
            ),

            "generated_candidates": sorted(
                set(self.generated_candidates)
            ),

            "large_files": sorted(
                self.large_files,
                key=lambda item: item["size"],
                reverse=True,
            ),

            "protected_files": sorted(
                protected_files
            ),

            "scan_errors": self.scan_errors,

            "files": [
                asdict(record)
                for record in self.files
            ],
        }

    # ========================================================
    # MARKDOWN SUMMARY
    # ========================================================

    def build_markdown(
        self,
        report: dict,
    ) -> str:

        stats = report["statistics"]

        exact = report["exact_duplicate_groups"]
        normalized = report[
            "normalized_duplicate_groups"
        ]

        symbols = report[
            "duplicate_python_symbols"
        ]

        names = report[
            "duplicate_filenames"
        ]

        lines = []

        lines.append("# KAIRO DEEP SCAN REPORT")
        lines.append("")
        lines.append(
            f"Generated: `{report['metadata']['timestamp']}`"
        )
        lines.append("")
        lines.append(
            "**IMPORTANT: This scan is READ-ONLY. "
            "No files were deleted or modified.**"
        )
        lines.append("")

        lines.append("## Project")
        lines.append("")
        lines.append(
            f"`{report['metadata']['project_root']}`"
        )
        lines.append("")

        lines.append("## Statistics")
        lines.append("")
        lines.append("| Metric | Count |")
        lines.append("|---|---:|")

        for key, value in stats.items():
            if isinstance(value, int):
                lines.append(
                    f"| {key} | {value:,} |"
                )

        lines.append("")

        lines.append("## Exact Duplicate Groups")
        lines.append("")
        lines.append(
            f"Duplicate groups: **{len(exact)}**"
        )
        lines.append("")

        for index, group in enumerate(
            exact[:500],
            start=1,
        ):

            lines.append(
                f"### Group {index} "
                f"({group['count']} files)"
            )

            for file_path in group["files"]:
                lines.append(
                    f"- `{file_path}`"
                )

            lines.append("")

        lines.append(
            "## Normalized Code/Text Duplicate Groups"
        )
        lines.append("")
        lines.append(
            f"Groups: **{len(normalized)}**"
        )
        lines.append("")

        for index, group in enumerate(
            normalized[:500],
            start=1,
        ):

            lines.append(
                f"### Group {index} "
                f"({group['count']} files)"
            )

            for file_path in group["files"]:
                lines.append(
                    f"- `{file_path}`"
                )

            lines.append("")

        lines.append(
            "## Duplicate Python Symbols"
        )
        lines.append("")
        lines.append(
            f"Duplicate symbols: **{len(symbols)}**"
        )
        lines.append("")

        for symbol, paths in list(
            symbols.items()
        )[:1000]:

            lines.append(
                f"### `{symbol}`"
            )

            for path in paths:
                lines.append(
                    f"- `{path}`"
                )

            lines.append("")

        lines.append(
            "## Duplicate Filenames"
        )
        lines.append("")
        lines.append(
            f"Duplicate filename groups: "
            f"**{len(names)}**"
        )
        lines.append("")

        for name, paths in list(
            names.items()
        )[:1000]:

            lines.append(
                f"### `{name}`"
            )

            for path in paths:
                lines.append(
                    f"- `{path}`"
                )

            lines.append("")

        lines.append("## Junk Candidates")
        lines.append("")

        for path in report[
            "junk_candidates"
        ]:
            lines.append(
                f"- `{path}`"
            )

        lines.append("")

        lines.append("## Generated/Dependency Directories")
        lines.append("")

        for path in report[
            "generated_candidates"
        ]:
            lines.append(
                f"- `{path}`"
            )

        lines.append("")

        lines.append("## Large Files")
        lines.append("")

        for item in report["large_files"]:
            size_mb = item["size"] / (
                1024 * 1024
            )

            lines.append(
                f"- `{item['path']}` — "
                f"{size_mb:.2f} MB"
            )

        lines.append("")

        lines.append("## Protected Files")
        lines.append("")
        lines.append(
            f"Protected files detected: "
            f"**{len(report['protected_files'])}**"
        )
        lines.append("")

        lines.append(
            "Protected areas were not modified."
        )

        lines.append("")

        lines.append("## Scan Errors")
        lines.append("")

        if report["scan_errors"]:
            for error in report["scan_errors"]:
                lines.append(
                    f"- `{error['path']}`: "
                    f"{error['error']}"
                )
        else:
            lines.append(
                "No scan errors."
            )

        lines.append("")

        lines.append("## Next Phase")
        lines.append("")
        lines.append(
            "This report is input for the KAIRO "
            "cleanup/consolidation phase."
        )
        lines.append("")
        lines.append(
            "**No deletion decisions are made "
            "automatically by this scanner.**"
        )

        return "\n".join(lines)

    # ========================================================
    # SAVE
    # ========================================================

    def save_reports(self) -> None:

        REPORT_ROOT.mkdir(
            parents=True,
            exist_ok=True,
        )

        report = self.build_report()

        json_path = (
            REPORT_ROOT /
            "KAIRO_DEEP_SCAN.json"
        )

        markdown_path = (
            REPORT_ROOT /
            "KAIRO_DEEP_SCAN.md"
        )

        stats_path = (
            REPORT_ROOT /
            "KAIRO_SCAN_STATS.json"
        )

        json_path.write_text(
            json.dumps(
                report,
                indent=2,
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )

        markdown_path.write_text(
            self.build_markdown(report),
            encoding="utf-8",
        )

        stats_path.write_text(
            json.dumps(
                {
                    "metadata": report["metadata"],
                    "statistics": report["statistics"],
                    "extensions": report["extensions"],
                    "exact_duplicate_groups": len(
                        report["exact_duplicate_groups"]
                    ),
                    "normalized_duplicate_groups": len(
                        report[
                            "normalized_duplicate_groups"
                        ]
                    ),
                    "duplicate_python_symbols": len(
                        report[
                            "duplicate_python_symbols"
                        ]
                    ),
                    "duplicate_filenames": len(
                        report[
                            "duplicate_filenames"
                        ]
                    ),
                    "junk_candidates": len(
                        report["junk_candidates"]
                    ),
                    "generated_candidates": len(
                        report["generated_candidates"]
                    ),
                    "large_files": len(
                        report["large_files"]
                    ),
                    "scan_errors": len(
                        report["scan_errors"]
                    ),
                },
                indent=2,
            ),
            encoding="utf-8",
        )

        print()
        print("=" * 72)
        print("REPORTS CREATED")
        print("=" * 72)
        print()
        print(json_path)
        print(markdown_path)
        print(stats_path)
        print()

        print(
            "Exact duplicate groups :",
            len(report["exact_duplicate_groups"]),
        )

        print(
            "Normalized duplicates  :",
            len(
                report[
                    "normalized_duplicate_groups"
                ]
            ),
        )

        print(
            "Duplicate Python symbols:",
            len(
                report[
                    "duplicate_python_symbols"
                ]
            ),
        )

        print(
            "Duplicate filenames    :",
            len(
                report[
                    "duplicate_filenames"
                ]
            ),
        )

        print(
            "Junk candidates        :",
            len(
                report[
                    "junk_candidates"
                ]
            ),
        )

        print(
            "Scan errors            :",
            len(
                report[
                    "scan_errors"
                ]
            ),
        )

        print()
        print("SCAN STATUS: COMPLETE")
        print("DELETION: NONE")
        print()


# ============================================================
# MAIN
# ============================================================

def main() -> int:

    scanner = KairoDeepScanner()

    scanner.scan()

    scanner.save_reports()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())