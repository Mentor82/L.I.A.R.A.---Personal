#!/usr/bin/env python3
"""
Architecture Guardrails & Monolith Prevention Tool (Issue #21)
=============================================================
Audits codebase line counts in `app/` and `frontend/src/` to prevent 'God Files'
and enforce modular architecture.

Features:
- Soft Limit (Warning): Files exceeding SOFT_LIMIT (default: 500 lines).
- Hard Limit (Error): New un-grandfathered files exceeding HARD_LIMIT (default: 800 lines).
- Anti-Ratchet Protection: Grandfathered legacy files cannot grow beyond their baseline.
- Summary reporting and CI exit codes.
"""

import os
import sys
import json
import argparse
from pathlib import Path
from typing import Dict, List, Tuple

# Cross-platform safe console output
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

DEFAULT_SOFT_LIMIT = 500
DEFAULT_HARD_LIMIT = 800
RATCHET_GROWTH_TOLERANCE = 25  # Max lines a legacy file can grow before triggering a failure

IGNORE_DIRS = {
    'node_modules', '.git', 'venv', '.venv', 'env', '.env', 'dist', '__pycache__',
    '.pytest_cache', 'build', '.idea', '.vscode', 'mlog', 'session_files',
    'site-packages', 'coverage', '.coverage'
}

BACKEND_EXTENSIONS = {'.py'}
FRONTEND_EXTENSIONS = {'.js', '.jsx', '.ts', '.tsx', '.css'}

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent
BASELINE_FILE = SCRIPT_DIR / 'architecture_baseline.json'


def count_file_lines(filepath: Path) -> int:
    """Counts non-empty lines in a file or total lines."""
    try:
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            return sum(1 for _ in f)
    except Exception:
        return 0


def scan_directory(base_dir: Path, extensions: set) -> Dict[str, int]:
    """Scans directory and returns mapping of relative_path -> line_count."""
    results = {}
    if not base_dir.exists():
        return results

    for root, dirs, files in os.walk(base_dir):
        dirs[:] = [d for d in dirs if d not in IGNORE_DIRS and not d.startswith('.')]
        if any(part in IGNORE_DIRS or part.startswith('.') for part in Path(root).parts):
            continue
        for file in files:
            ext = Path(file).suffix.lower()
            if ext in extensions:
                full_path = Path(root) / file
                rel_path = full_path.relative_to(REPO_ROOT).as_posix()
                results[rel_path] = count_file_lines(full_path)
    return results


def load_baseline() -> Dict[str, int]:
    """Loads grandfathered line-count baseline."""
    if BASELINE_FILE.exists():
        try:
            with open(BASELINE_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"⚠️ Failed to read baseline file: {e}", file=sys.stderr)
    return {}


def save_baseline(data: Dict[str, int]) -> None:
    """Saves current scan as new grandfathered baseline."""
    with open(BASELINE_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, sort_keys=True)
    print(f"✅ Baseline updated in {BASELINE_FILE.relative_to(REPO_ROOT)} ({len(data)} files recorded)")


def run_audit(
    soft_limit: int = DEFAULT_SOFT_LIMIT,
    hard_limit: int = DEFAULT_HARD_LIMIT,
    strict_ratchet: bool = True,
) -> Tuple[int, List[str], List[str], List[str]]:
    """
    Runs full architecture guardrail audit.
    Returns:
        (exit_code, errors, warnings, info_messages)
    """
    backend_files = scan_directory(REPO_ROOT / 'app', BACKEND_EXTENSIONS)
    frontend_files = scan_directory(REPO_ROOT / 'frontend' / 'src', FRONTEND_EXTENSIONS)
    all_files = {**backend_files, **frontend_files}

    baseline = load_baseline()

    errors = []
    warnings = []
    info = []

    # Sort files by line count descending
    sorted_files = sorted(all_files.items(), key=lambda x: x[1], reverse=True)

    for path, lines in sorted_files:
        is_grandfathered = path in baseline
        baseline_lines = baseline.get(path, 0)

        # Anti-ratchet check for legacy files
        if is_grandfathered and strict_ratchet:
            max_allowed = baseline_lines + RATCHET_GROWTH_TOLERANCE
            if lines > max_allowed:
                errors.append(
                    f"RATCHET VIOLATION: '{path}' grew to {lines} lines (baseline: {baseline_lines}, max allowed: {max_allowed}). "
                    f"Refactor this module into smaller components rather than expanding it!"
                )
            elif lines < baseline_lines - 50:
                info.append(
                    f"REFACTOR SUCCESS: '{path}' shrank from {baseline_lines} to {lines} lines! (-{baseline_lines - lines})"
                )

        # Hard limit check for new or un-grandfathered files
        if not is_grandfathered and lines > hard_limit:
            errors.append(
                f"HARD LIMIT VIOLATION: New file '{path}' has {lines} lines (max allowed for new files: {hard_limit}). "
                f"Split this file according to Single Responsibility Principle before merging."
            )

        # Soft limit warning
        if lines > soft_limit:
            warnings.append(
                f"SOFT LIMIT: '{path}' has {lines} lines (> {soft_limit}). Consider modularizing."
            )

    exit_code = 1 if errors else 0
    return exit_code, errors, warnings, info


def main():
    parser = argparse.ArgumentParser(description="Liara Architecture Guardrail & Monolith Checker")
    parser.add_argument('--soft-limit', type=int, default=DEFAULT_SOFT_LIMIT, help="Soft line count limit (warning)")
    parser.add_argument('--hard-limit', type=int, default=DEFAULT_HARD_LIMIT, help="Hard line count limit for new files")
    parser.add_argument('--update-baseline', action='store_true', help="Update baseline with current scan")
    parser.add_argument('--ci', action='store_true', help="Run in strict CI mode")
    args = parser.parse_args()

    if args.update_baseline:
        backend_files = scan_directory(REPO_ROOT / 'app', BACKEND_EXTENSIONS)
        frontend_files = scan_directory(REPO_ROOT / 'frontend' / 'src', FRONTEND_EXTENSIONS)
        all_files = {**backend_files, **frontend_files}
        # Only record files over soft limit in baseline to track legacy exceptions
        legacy_exceptions = {k: v for k, v in all_files.items() if v >= args.soft_limit}
        save_baseline(legacy_exceptions)
        return 0

    print("=" * 70)
    print(" 🏛️  LIARA ARCHITECTURE GUARDRAILS (Issue #21)")
    print("=" * 70)

    exit_code, errors, warnings, info = run_audit(
        soft_limit=args.soft_limit,
        hard_limit=args.hard_limit,
        strict_ratchet=True
    )

    if info:
        print("\n🎉 Modularization Progress:")
        for msg in info:
            print(f"   ✓ {msg}")

    if warnings:
        print(f"\n⚠️  Architecture Warnings ({len(warnings)} files > {args.soft_limit} lines):")
        for w in warnings[:15]:
            print(f"   • {w}")
        if len(warnings) > 15:
            print(f"   ... and {len(warnings) - 15} more files.")

    if errors:
        print(f"\n❌ Architecture Errors ({len(errors)} violations):")
        for err in errors:
            print(f"   🔴 {err}")
        print("\n🚫 Build blocked: Monolith growth detected. Refactor or split oversized files.")
    else:
        print(f"\n✅ All architecture guardrails passed! No unauthorized monolith growth.")

    print("=" * 70)
    sys.exit(exit_code)


if __name__ == '__main__':
    main()
