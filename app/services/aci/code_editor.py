"""
ACI (Agent-Computer Interface) - Code Editor
Sichere, chunk-basierte Code-Modifikation mit Vorab-Syntax-Validierung.
Verhindert Token-Verschwendung und Code-Korruption.
"""
import os
from pathlib import Path
from typing import Optional, Dict, Any, Union

from services.session_workspace import (
    resolve_workspace_file,
    create_workspace_file,
    write_workspace_file,
    delete_workspace_file,
    record_file_event,
    _workspace_dir
)
from services.aci.code_validator import validate_python_syntax


def _resolve_file(
    path: Optional[Union[str, Path]] = None,
    user_id: Optional[int] = None,
    session_id: Optional[int] = None,
    filename: Optional[str] = None
) -> Optional[Path]:
    if user_id is not None and session_id is not None and filename:
        return resolve_workspace_file(user_id, session_id, filename)
    if path is not None:
        p = Path(path)
        if p.exists():
            return p.resolve()
    return None


def replace_chunk(
    target_content: str,
    replacement_content: str,
    path: Optional[Union[str, Path]] = None,
    user_id: Optional[int] = None,
    session_id: Optional[int] = None,
    filename: Optional[str] = None,
    allow_multiple: bool = False
) -> Dict[str, Any]:
    """
    Ersetzt einen spezifischen Code-Chunk in einer Datei.
    
    1. Sucht nach exaktem Vorkommen von target_content.
    2. Validiert Eindeutigkeit (wenn allow_multiple=False).
    3. Führt vorab einen Syntax-Check auf dem resultierenden Code durch.
    4. Schreibt erst bei erfolgreicher Validierung auf die Festplatte.
    """
    target = _resolve_file(path, user_id, session_id, filename)
    if not target or not target.exists():
        return {
            "success": False,
            "error": f"Datei nicht gefunden: {filename or path}"
        }

    try:
        with open(target, "r", encoding="utf-8") as f:
            original_content = f.read()
    except Exception as e:
        return {"success": False, "error": f"Fehler beim Lesen der Datei: {str(e)}"}

    # Normalisiere Zeilenenden für robusten Match
    normalized_original = original_content.replace("\r\n", "\n")
    normalized_target = target_content.replace("\r\n", "\n")
    normalized_replacement = replacement_content.replace("\r\n", "\n")

    occurrences = normalized_original.count(normalized_target)
    if occurrences == 0:
        return {
            "success": False,
            "error": (
                "Der angegebene Ziel-Codeblock (target_content) wurde in der Datei nicht exakt gefunden. "
                "Bitte prüfe Einrückungen und Whitespaces via view_file vor der Ersetzung."
            )
        }

    if occurrences > 1 and not allow_multiple:
        return {
            "success": False,
            "error": (
                f"Der Ziel-Codeblock kommt {occurrences}-mal in der Datei vor. "
                "Bitte schließe mehr umgebende Zeilen ein, um den Block eindeutig zu machen, "
                "oder setze allow_multiple=True."
            )
        }

    # Ersetzen
    if allow_multiple:
        new_content = normalized_original.replace(normalized_target, normalized_replacement)
    else:
        new_content = normalized_original.replace(normalized_target, normalized_replacement, 1)

    # Vorab-Validierung für Python-Dateien
    if target.name.endswith(".py"):
        syntax_res = validate_python_syntax(new_content, filename=target.name)
        if not syntax_res["valid"]:
            return {
                "success": False,
                "error": f"Änderung abgebrochen - resultierender Code enthält Syntaxfehler: {syntax_res['error']}",
                "syntax_error": syntax_res
            }

    # Datei schreiben
    try:
        if user_id is not None and session_id is not None and filename:
            save_res = write_workspace_file(user_id, session_id, filename, new_content)
            if not save_res.get("ok"):
                return {"success": False, "error": save_res.get("error", "Speichern fehlgeschlagen")}
            record_file_event(user_id, session_id, filename, source="agent")
        else:
            with open(target, "w", encoding="utf-8") as f:
                f.write(new_content)

        return {
            "success": True,
            "filename": str(filename or target.name),
            "replaced_occurrences": occurrences if allow_multiple else 1,
            "message": f"Code-Chunk in {filename or target.name} erfolgreich aktualisiert."
        }
    except Exception as e:
        return {"success": False, "error": f"Fehler beim Speichern der Datei: {str(e)}"}


def create_file(
    content: str,
    path: Optional[Union[str, Path]] = None,
    user_id: Optional[int] = None,
    session_id: Optional[int] = None,
    filename: Optional[str] = None,
    overwrite: bool = False
) -> Dict[str, Any]:
    """
    Erstellt eine neue Datei im Workspace mit Vorab-Syntaxprüfung.
    """
    fname = filename or (Path(path).name if path else None)
    if not fname:
        return {"success": False, "error": "Kein Dateiname angegeben"}

    # Vorab-Syntax-Check für Python
    if fname.endswith(".py"):
        syntax_res = validate_python_syntax(content, filename=fname)
        if not syntax_res["valid"]:
            return {
                "success": False,
                "error": f"Datei-Erstellung abgebrochen - Syntaxfehler: {syntax_res['error']}",
                "syntax_error": syntax_res
            }

    try:
        if user_id is not None and session_id is not None:
            # Session Workspace
            if overwrite:
                save_res = write_workspace_file(user_id, session_id, fname, content)
                if not save_res.get("ok"):
                    # Falls Datei noch nicht existiert, create probieren
                    create_res = create_workspace_file(user_id, session_id, fname, content)
                    if not create_res.get("ok"):
                        return {"success": False, "error": create_res.get("error")}
            else:
                create_res = create_workspace_file(user_id, session_id, fname, content)
                if not create_res.get("ok"):
                    return {"success": False, "error": create_res.get("error")}
            
            record_file_event(user_id, session_id, fname, source="agent")
            return {"success": True, "filename": fname, "message": f"Datei {fname} erfolgreich erstellt."}
        
        elif path is not None:
            p = Path(path)
            if p.exists() and not overwrite:
                return {"success": False, "error": f"Datei {path} existiert bereits und overwrite=False"}
            
            p.parent.mkdir(parents=True, exist_ok=True)
            with open(p, "w", encoding="utf-8") as f:
                f.write(content)
            return {"success": True, "filename": str(p), "message": f"Datei {p} erfolgreich geschrieben."}

        return {"success": False, "error": "Ungültige Pfadangaben"}
    except Exception as e:
        return {"success": False, "error": f"Fehler beim Erstellen der Datei: {str(e)}"}


def delete_file(
    path: Optional[Union[str, Path]] = None,
    user_id: Optional[int] = None,
    session_id: Optional[int] = None,
    filename: Optional[str] = None
) -> Dict[str, Any]:
    """
    Löscht eine Datei im Workspace sicher.
    """
    if user_id is not None and session_id is not None and filename:
        res = delete_workspace_file(user_id, session_id, filename)
        if not res.get("ok"):
            return {"success": False, "error": res.get("error")}
        return {"success": True, "filename": filename, "message": f"Datei {filename} gelöscht."}

    if path is not None:
        p = Path(path)
        if not p.exists():
            return {"success": False, "error": f"Datei {path} existiert nicht."}
        try:
            p.unlink()
            return {"success": True, "filename": str(p), "message": f"Datei {p} gelöscht."}
        except Exception as e:
            return {"success": False, "error": f"Fehler beim Löschen: {str(e)}"}

    return {"success": False, "error": "Ungültige Pfadangaben"}
