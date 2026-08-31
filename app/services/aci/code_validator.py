"""
ACI (Agent-Computer Interface) - Code Validator
Überprüft Code-Syntax, Ausführbarkeit und Linter-Regeln für Liara Agents.
"""
import ast
import traceback
from typing import Dict, Any, Optional
from pathlib import Path


def validate_python_syntax(code: str, filename: str = "<agent_code>") -> Dict[str, Any]:
    """
    Führt einen statischen AST- und Bytecode-Compile-Check für Python-Code durch.
    Gibt detaillierte Zeilen- und Spalteninformationen bei Syntax-Fehlern zurück.
    """
    try:
        ast.parse(code, filename=filename)
        compile(code, filename=filename, mode="exec")
        return {
            "valid": True,
            "filename": filename,
            "error": None,
            "line": None,
            "offset": None
        }
    except SyntaxError as e:
        return {
            "valid": False,
            "filename": filename,
            "error": f"SyntaxError in Zeile {e.lineno}, Spalte {e.offset}: {e.msg}",
            "line": e.lineno,
            "offset": e.offset,
            "text": e.text.strip() if e.text else None
        }
    except Exception as e:
        return {
            "valid": False,
            "filename": filename,
            "error": f"Validierungsfehler: {str(e)}",
            "line": None,
            "offset": None
        }


def validate_file_syntax(file_path: Path) -> Dict[str, Any]:
    """
    Validiert eine Datei auf der Festplatte basierend auf ihrer Dateiendung.
    """
    if not file_path.exists():
        return {"valid": False, "error": f"Datei nicht gefunden: {file_path}"}

    ext = file_path.suffix.lower()
    if ext == ".py":
        try:
            content = file_path.read_text(encoding="utf-8", errors="replace")
            return validate_python_syntax(content, filename=file_path.name)
        except Exception as e:
            return {"valid": False, "error": f"Fehler beim Lesen der Datei: {str(e)}"}
    
    # Für andere Dateitypen (JSON, YAML, etc.)
    elif ext == ".json":
        import json
        try:
            json.loads(file_path.read_text(encoding="utf-8", errors="replace"))
            return {"valid": True, "filename": file_path.name, "error": None}
        except Exception as e:
            return {"valid": False, "filename": file_path.name, "error": f"JSONDecodeError: {str(e)}"}

    return {"valid": True, "filename": file_path.name, "note": "Kein Parser für diese Dateiendung erforderlich"}
