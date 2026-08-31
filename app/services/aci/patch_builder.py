"""
ACI (Agent-Computer Interface) - Patch Builder
Erstellt Unified Diffs und Patches für Liaras Proposal- und Backup-System.
"""
import difflib
from typing import List, Dict, Any, Optional
from pathlib import Path


def generate_unified_diff(
    original_text: str,
    modified_text: str,
    from_file: str = "a/file",
    to_file: str = "b/file"
) -> str:
    """
    Erzeugt einen standardisierten Unified Diff zwischen zwei Textständen.
    """
    orig_lines = original_text.splitlines(keepends=True)
    mod_lines = modified_text.splitlines(keepends=True)
    diff = difflib.unified_diff(
        orig_lines,
        mod_lines,
        fromfile=from_file,
        tofile=to_file
    )
    return "".join(diff)


def create_patch_summary(changes: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Aggregiert mehrere Dateiänderungen zu einem strukturierten Patch-Summary.
    """
    files_changed = len(changes)
    total_additions = 0
    total_deletions = 0
    diffs = []

    for change in changes:
        fname = change.get("filename", "unknown")
        orig = change.get("original", "")
        mod = change.get("modified", "")
        diff_str = generate_unified_diff(orig, mod, from_file=f"a/{fname}", to_file=f"b/{fname}")
        
        # Zähle Zeilen
        for line in diff_str.splitlines():
            if line.startswith("+") and not line.startswith("+++"):
                total_additions += 1
            elif line.startswith("-") and not line.startswith("---"):
                total_deletions += 1
        
        diffs.append({
            "filename": fname,
            "diff": diff_str
        })

    return {
        "files_changed": files_changed,
        "additions": total_additions,
        "deletions": total_deletions,
        "diffs": diffs
    }
