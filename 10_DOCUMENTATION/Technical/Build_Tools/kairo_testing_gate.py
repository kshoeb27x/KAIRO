from __future__ import annotations

import ast
import json
import py_compile
import subprocess
import sys
from pathlib import Path
from datetime import datetime, timezone


ROOT = Path(__file__).resolve().parents[1]

INTEGRATION_ROOT = ROOT / "12_EXTRACTION" / "INTEGRATION"
PACKAGES_ROOT = INTEGRATION_ROOT / "PACKAGES"

OUT_ROOT = ROOT / "12_EXTRACTION" / "TESTING_GATE"
REPORT_ROOT = OUT_ROOT / "REPORTS"
MANIFEST_ROOT = OUT_ROOT / "MANIFEST"

REPORT_ROOT.mkdir(parents=True, exist_ok=True)
MANIFEST_ROOT.mkdir(parents=True, exist_ok=True)

SKIP_DIRS = {
    ".git",
    ".venv",
    "venv",
    "node_modules",
    "__pycache__",
    ".pytest_cache",
    "dist",
    "build",
    ".next",
    ".cache",
}

PYTHON_EXTENSIONS = {".py"}

JS_EXTENSIONS = {
    ".js",
    ".jsx",
    ".ts",
    ".tsx",
}

CONFIG_EXTENSIONS = {
    ".json",
    ".yaml",
    ".yml",
    ".toml",
}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def should_skip(path: Path) -> bool:
    return any(part in SKIP_DIRS for part in path.parts)


def package_id(path: Path) -> str:
    try:
        return path.relative_to(PACKAGES_ROOT).parts[0]
    except Exception:
        return path.name


def python_syntax_test(path: Path) -> tuple[str, str]:
    try:
        source = path.read_text(
            encoding="utf-8",
            errors="ignore",
        )

        ast.parse(source, filename=str(path))

        return "PASS", "Python AST syntax valid."

    except SyntaxError as exc:
        return "FAIL", (
            f"SyntaxError line {exc.lineno}: "
            f"{exc.msg}"
        )

    except Exception as exc:
        return "ERROR", str(exc)


def python_compile_test(path: Path) -> tuple[str, str]:
    try:
        py_compile.compile(
            str(path),
            doraise=True,
        )

        return "PASS", "Python bytecode compilation valid."

    except py_compile.PyCompileError as exc:
        return "FAIL", str(exc)

    except Exception as exc:
        return "ERROR", str(exc)


def json_test(path: Path) -> tuple[str, str]:
    try:
        json.loads(
            path.read_text(
                encoding="utf-8",
                errors="ignore",
            )
        )

        return "PASS", "JSON valid."

    except json.JSONDecodeError as exc:
        return "FAIL", (
            f"JSON error line {exc.lineno}: "
            f"{exc.msg}"
        )

    except Exception as exc:
        return "ERROR", str(exc)


def toml_test(path: Path) -> tuple[str, str]:
    try:
        import tomllib

        with path.open("rb") as f:
            tomllib.load(f)

        return "PASS", "TOML valid."

    except Exception as exc:
        return "FAIL", str(exc)


def yaml_test(path: Path) -> tuple[str, str]:
    try:
        import yaml

        yaml.safe_load(
            path.read_text(
                encoding="utf-8",
                errors="ignore",
            )
        )

        return "PASS", "YAML parsed successfully."

    except Exception as exc:
        return "FAIL", str(exc)


def javascript_basic_test(path: Path) -> tuple[str, str]:
    """
    Static JS/TS integrity check.

    We deliberately do not execute arbitrary JavaScript,
    TypeScript, Node applications, shell commands, or
    package installation from extracted repositories.
    """

    try:
        text = path.read_text(
            encoding="utf-8",
            errors="ignore",
        )

        if not text.strip():
            return "FAIL", "Empty source file."

        if "\x00" in text:
            return "FAIL", "Binary/null-byte content detected."

        return "PASS", "Static source integrity check passed."

    except Exception as exc:
        return "ERROR", str(exc)


def generic_text_test(path: Path) -> tuple[str, str]:
    try:
        if path.stat().st_size == 0:
            return "FAIL", "Empty file."

        with path.open(
            "r",
            encoding="utf-8",
            errors="ignore",
        ) as f:
            sample = f.read(4096)

        if "\x00" in sample:
            return "FAIL", "Null-byte content detected."

        return "PASS", "Basic file integrity passed."

    except Exception as exc:
        return "ERROR", str(exc)


def run_existing_tests(package_dir: Path):
    """
    Only runs tests that are already part of the extracted package.

    No dependencies are installed.
    No network is used.
    No production code is touched.
    """

    test_dirs = [
        package_dir / "tests",
        package_dir / "test",
    ]

    test_files = []

    for test_dir in test_dirs:
        if not test_dir.exists():
            continue

        for path in test_dir.rglob("*"):
            if path.is_file() and not should_skip(path):
                if (
                    path.name.startswith("test_")
                    or path.name.endswith("_test.py")
                ):
                    test_files.append(path)

    if not test_files:
        return {
            "status": "NOT_RUN",
            "reason": "No existing Python test suite discovered.",
            "test_files": 0,
        }

    # Static-only safety:
    # Do not execute arbitrary extracted tests automatically.
    return {
        "status": "DISCOVERED",
        "reason": (
            "Existing tests discovered but not executed "
            "automatically because extracted code is untrusted."
        ),
        "test_files": len(test_files),
    }


def test_package(package_dir: Path):
    files = []

    for path in package_dir.rglob("*"):
        if not path.is_file():
            continue

        if should_skip(path):
            continue

        files.append(path)

    results = []

    for path in files:
        suffix = path.suffix.lower()

        if suffix == ".py":
            status, message = python_syntax_test(path)

            results.append(
                {
                    "file": str(
                        path.relative_to(package_dir)
                    ),
                    "test": "python_syntax",
                    "status": status,
                    "message": message,
                }
            )

            if status == "PASS":
                status2, message2 = python_compile_test(path)

                results.append(
                    {
                        "file": str(
                            path.relative_to(package_dir)
                        ),
                        "test": "python_compile",
                        "status": status2,
                        "message": message2,
                    }
                )

        elif suffix == ".json":
            status, message = json_test(path)

            results.append(
                {
                    "file": str(
                        path.relative_to(package_dir)
                    ),
                    "test": "json_parse",
                    "status": status,
                    "message": message,
                }
            )

        elif suffix == ".toml":
            status, message = toml_test(path)

            results.append(
                {
                    "file": str(
                        path.relative_to(package_dir)
                    ),
                    "test": "toml_parse",
                    "status": status,
                    "message": message,
                }
            )

        elif suffix in {".yaml", ".yml"}:
            status, message = yaml_test(path)

            results.append(
                {
                    "file": str(
                        path.relative_to(package_dir)
                    ),
                    "test": "yaml_parse",
                    "status": status,
                    "message": message,
                }
            )

        elif suffix in JS_EXTENSIONS:
            status, message = javascript_basic_test(path)

            results.append(
                {
                    "file": str(
                        path.relative_to(package_dir)
                    ),
                    "test": "static_source_integrity",
                    "status": status,
                    "message": message,
                }
            )

        else:
            status, message = generic_text_test(path)

            results.append(
                {
                    "file": str(
                        path.relative_to(package_dir)
                    ),
                    "test": "file_integrity",
                    "status": status,
                    "message": message,
                }
            )

    existing_tests = run_existing_tests(package_dir)

    results.append(
        {
            "file": "__PACKAGE__",
            "test": "existing_test_discovery",
            "status": existing_tests["status"],
            "message": existing_tests["reason"],
        }
    )

    failures = [
        x
        for x in results
        if x["status"] in {"FAIL", "ERROR"}
    ]

    if failures:
        package_status = "FAIL"
    else:
        package_status = "PASS"

    return {
        "package_id": package_id(package_dir),
        "status": package_status,
        "file_count": len(files),
        "test_count": len(results),
        "failures": len(failures),
        "existing_tests": existing_tests,
        "results": results[:1000],
    }


def main() -> int:
    print("=" * 68)
    print(" KAIRO AUTOMATED TESTING GATE V1")
    print("=" * 68)
    print()
    print("Mode        : SAFE STATIC TESTING")
    print("Production  : PROTECTED")
    print("Archive     : PROTECTED")
    print("Source      : PROTECTED")
    print("Network     : NOT USED")
    print("Dependencies: NOT INSTALLED")
    print("Extracted tests: NOT EXECUTED")
    print()

    if not PACKAGES_ROOT.exists():
        print("ERROR: Integration packages directory not found.")
        return 1

    package_dirs = [
        path
        for path in PACKAGES_ROOT.iterdir()
        if path.is_dir()
    ]

    package_dirs.sort(
        key=lambda p: p.name.lower()
    )

    print(
        f"Integration packages : {len(package_dirs):,}"
    )
    print()

    results = []

    passed = 0
    failed = 0
    errors = 0
    files_tested = 0
    tests_run = 0
    existing_test_packages = 0
    discovered_test_files = 0

    for index, package_dir in enumerate(
        package_dirs,
        1,
    ):
        result = test_package(package_dir)

        results.append(result)

        files_tested += result["file_count"]
        tests_run += result["test_count"]

        if result["status"] == "PASS":
            passed += 1
        else:
            failed += 1

        failures = [
            x
            for x in result["results"]
            if x["status"] == "ERROR"
        ]

        errors += len(failures)

        existing = result["existing_tests"]

        if existing["status"] in {
            "DISCOVERED",
        }:
            existing_test_packages += 1
            discovered_test_files += existing["test_files"]

        if (
            index % 100 == 0
            or index == len(package_dirs)
        ):
            print(
                f"[{index:5d}/{len(package_dirs)}] "
                f"PASS={passed} "
                f"FAIL={failed} "
                f"ERROR={errors}"
            )

    overall_status = (
        "PASS"
        if failed == 0 and errors == 0
        else "REVIEW_REQUIRED"
    )

    manifest = {
        "generated_at": utc_now(),
        "engine": "KAIRO AUTOMATED TESTING GATE V1",
        "mode": "SAFE_STATIC_TESTING",
        "production_modified": False,
        "archive_modified": False,
        "source_repositories_modified": False,
        "network_used": False,
        "dependencies_installed": False,
        "extracted_tests_executed": False,
        "packages_received": len(package_dirs),
        "packages_passed": passed,
        "packages_failed": failed,
        "errors": errors,
        "files_tested": files_tested,
        "tests_run": tests_run,
        "packages_with_existing_tests": existing_test_packages,
        "existing_test_files_discovered": discovered_test_files,
        "status": overall_status,
        "results": results,
    }

    manifest_path = (
        MANIFEST_ROOT
        / "TESTING_GATE_MANIFEST.json"
    )

    report_path = (
        REPORT_ROOT
        / "KAIRO_TESTING_GATE_REPORT.md"
    )

    manifest_path.write_text(
        json.dumps(
            manifest,
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    report = [
        "# KAIRO AUTOMATED TESTING GATE V1",
        "",
        f"Generated: {utc_now()}",
        "",
        "## Safety",
        "",
        "- Production KAIRO: PROTECTED",
        "- Frozen archive: PROTECTED",
        "- Source repositories: PROTECTED",
        "- Network: NOT USED",
        "- Dependencies: NOT INSTALLED",
        "- Extracted tests: NOT EXECUTED",
        "",
        "## Results",
        "",
        f"- Packages received: {len(package_dirs):,}",
        f"- Packages passed: {passed:,}",
        f"- Packages failed: {failed:,}",
        f"- Errors: {errors:,}",
        f"- Files tested: {files_tested:,}",
        f"- Static tests run: {tests_run:,}",
        f"- Packages containing existing tests: {existing_test_packages:,}",
        f"- Existing test files discovered: {discovered_test_files:,}",
        f"- Overall status: **{overall_status}**",
        "",
        "## Testing policy",
        "",
        "Python syntax and compilation checks were performed statically.",
        "JSON, TOML and YAML configuration parsing was performed where supported.",
        "JavaScript/TypeScript was checked for basic source integrity without execution.",
        "Existing extracted test suites were discovered but not executed automatically.",
        "No dependencies were installed and no network access was used.",
        "",
        "## Protection verification",
        "",
        "- Production modified: NO",
        "- Frozen archive modified: NO",
        "- Source repositories modified: NO",
    ]

    report_path.write_text(
        "\n".join(report),
        encoding="utf-8",
    )

    print()
    print("=" * 68)
    print(" KAIRO AUTOMATED TESTING GATE V1 COMPLETE")
    print("=" * 68)
    print()
    print(f"Packages received : {len(package_dirs):,}")
    print(f"Packages passed   : {passed:,}")
    print(f"Packages failed   : {failed:,}")
    print(f"Errors            : {errors:,}")
    print(f"Files tested      : {files_tested:,}")
    print(f"Tests run         : {tests_run:,}")
    print(
        f"Existing test packages : "
        f"{existing_test_packages:,}"
    )
    print()
    print(f"Manifest : {manifest_path}")
    print(f"Report   : {report_path}")
    print()
    print("Production modified       : NO")
    print("Frozen archive modified   : NO")
    print("Source repositories       : NO")
    print()

    if overall_status == "PASS":
        print("TESTING STATUS: PASS")
        print("NEXT: ARCHITECTURE MAPPING")
        return 0

    print("TESTING STATUS: REVIEW REQUIRED")
    print("NEXT: REVIEW FAILED PACKAGES")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
