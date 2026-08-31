"""
ACI (Agent-Computer Interface) - File Navigator
Token-effiziente Datei-Navigation, Fensterausschnitte und Code-Suche für Liara Agents.
"""
import os
import re
import fnmatch
from pathlib import Path
from typing import Optional, List, Dict, Any, Union

from services.session_workspace import resolve_workspace_file, _workspace_dir


def _resolve_target_path(
    path: Optional[Union[str, Path]] = None,
    user_id: Optional[int] = None,
    session_id: Optional[int] = None,
    filename: Optional[str] = None
) -> Optional[Path]:
    """
    Hilfsfunktion zur Auflösung von Dateipfaden:
    Entweder über einen direkten Pfad (z.B. für Server-/Repo-Tasks oder Tests)
    oder über (user_id, session_id, filename) für isolierte Session-Workspaces.
    """
    if user_id is not None and session_id is not None and filename:
        return resolve_workspace_file(user_id, session_id, filename)
    
    if path is not None:
        p = Path(path)
        if p.exists() and p.is_file():
            return p.resolve()
    
    return None


def view_file(
    path: Optional[Union[str, Path]] = None,
    start_line: int = 1,
    end_line: Optional[int] = None,
    max_lines: int = 150,
    user_id: Optional[int] = None,
    session_id: Optional[int] = None,
    filename: Optional[str] = None
) -> Dict[str, Any]:
    """
    Liest einen begrenzten Zeilenbereich einer Datei und formatiert die Ausgabe
    mit 1-basierten Zeilennummern.
    
    Verhindert Kontext-Überladung bei großen Dateien (SWE-agent ACI Prinzip).
    """
    target = _resolve_target_path(path, user_id, session_id, filename)
    if not target or not target.exists():
        return {
            "success": False,
            "error": f"Datei nicht gefunden: {filename or path}",
            "lines": [],
            "total_lines": 0
        }

    try:
        with open(target, "r", encoding="utf-8", errors="replace") as f:
            all_lines = f.readlines()
    except Exception as e:
        return {
            "success": False,
            "error": f"Fehler beim Lesen der Datei: {str(e)}",
            "lines": [],
            "total_lines": 0
        }

    total_lines = len(all_lines)
    if total_lines == 0:
        return {
            "success": True,
            "filename": str(filename or target.name),
            "start_line": 1,
            "end_line": 0,
            "total_lines": 0,
            "content": "(Datei ist leer)",
            "lines": []
        }

    # 1-basierte Zeilenindizes normalisieren
    start_idx = max(1, start_line)
    if end_line is None or end_line <= 0:
        end_idx = min(total_lines, start_idx + max_lines - 1)
    else:
        end_idx = min(total_lines, end_line)

    if end_idx - start_idx + 1 > max_lines:
        end_idx = start_idx + max_lines - 1

    selected_lines = all_lines[start_idx - 1 : end_idx]
    
    formatted_output = []
    for i, line in enumerate(selected_lines, start=start_idx):
        formatted_output.append(f"{i:4d} | {line.rstrip(chr(10)).rstrip(chr(13))}")

    content_str = "\n".join(formatted_output)

    return {
        "success": True,
        "filename": str(filename or target.name),
        "start_line": start_idx,
        "end_line": end_idx,
        "total_lines": total_lines,
        "has_more": end_idx < total_lines,
        "content": content_str,
        "lines": selected_lines
    }


def find_files(
    root_dir: Optional[Union[str, Path]] = None,
    pattern: str = "*",
    max_depth: int = 5,
    user_id: Optional[int] = None,
    session_id: Optional[int] = None
) -> Dict[str, Any]:
    """
    Sucht nach Dateien im Workspace / Verzeichnis passend zum Glob-Pattern.
    """
    if user_id is not None and session_id is not None:
        base = _workspace_dir(user_id, session_id)
    elif root_dir:
        base = Path(root_dir)
    else:
        base = Path(".")

    if not base.exists():
        return {"success": False, "error": f"Verzeichnis existiert nicht: {base}", "files": []}

    matches = []
    base_resolved = base.resolve()

    for root, dirs, files in os.walk(base_resolved):
        # Ignoriere versteckte Ordner wie .git, .venv, node_modules, metadata
        dirs[:] = [d for d in dirs if not d.startswith(".") and d not in ("node_modules", "metadata", "__pycache__")]
        
        # Tiefenlimit
        rel_root = Path(root).relative_to(base_resolved)
        if len(rel_root.parts) > max_depth:
            continue

        for f in files:
            if f.startswith("."):
                continue
            if fnmatch.fnmatch(f, pattern):
                rel_path = (rel_root / f).as_posix() if str(rel_root) != "." else f
                matches.append(rel_path)

    return {
        "success": True,
        "count": len(matches),
        "files": sorted(matches)
    }


def grep_search(
    query: str,
    root_dir: Optional[Union[str, Path]] = None,
    file_pattern: Optional[str] = None,
    case_sensitive: bool = False,
    is_regex: bool = False,
    max_results: int = 50,
    user_id: Optional[int] = None,
    session_id: Optional[int] = None
) -> Dict[str, Any]:
    """
    Durchsucht Dateien nach einem Textmuster oder regulärem Ausdruck.
    Liefert Dateinamen, Zeilennummern und Trefferzeilen.
    """
    if not query:
        return {"success": False, "error": "Suchbegriff darf nicht leer sein", "matches": []}

    if user_id is not None and session_id is not None:
        base = _workspace_dir(user_id, session_id)
    elif root_dir:
        base = Path(root_dir)
    else:
        base = Path(".")

    if not base.exists():
        return {"success": False, "error": f"Verzeichnis existiert nicht: {base}", "matches": []}

    flags = 0 if case_sensitive else re.IGNORECASE
    try:
        if is_regex:
            pattern = re.compile(query, flags)
        else:
            pattern = re.compile(re.escape(query), flags)
    except re.error as e:
        return {"success": False, "error": f"Ungültiger regulärer Ausdruck: {str(e)}", "matches": []}

    results = []
    base_resolved = base.resolve()

    for root, dirs, files in os.walk(base_resolved):
        dirs[:] = [d for d in dirs if not d.startswith(".") and d not in ("node_modules", "metadata", "__pycache__", ".venv")]

        for file in files:
            if file.startswith(".") or file.endswith((".pyc", ".tar.gz", ".zip", ".png", ".jpg", ".bin")):
                continue
            
            if file_pattern and not fnmatch.fnmatch(file, file_pattern):
                continue

            file_path = Path(root) / file
            rel_path = file_path.relative_to(base_resolved).as_posix()

            try:
                with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                    for line_num, line in enumerate(f, start=1):
                        if pattern.search(line):
                            results.append({
                                "file": rel_path,
                                "line_number": line_num,
                                "content": line.strip()
                            })
                            if len(results) >= max_results:
                                return {
                                    "success": True,
                                    "query": query,
                                    "count": len(results),
                                    "capped": True,
                                    "matches": results
                                }
            except Exception:
                continue

    return {
        "success": True,
        "query": query,
        "count": len(results),
        "capped": False,
        "matches": results
    }
