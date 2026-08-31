"""
Specialized Code Agent für L.I.A.R.A.
Nutzt das ACI (Agent-Computer Interface) für token-effiziente Software-Entwicklung.
"""
from typing import Optional, Dict, Any
from pathlib import Path

from services.agents.base_agent import BaseAgent
import services.aci as aci


CODE_AGENT_SYSTEM_PROMPT = """Du bist Liaras spezialisierter autonomer Code-Agent.
Deine Aufgabe ist es, Software-Engineering-Aufgaben im Projekt oder Workspace präzise, sauber und fehlerfrei zu lösen.

### Verhaltensregeln & Best Practices (ACI Prinzipien):
1. **Analysieren vor Modifizieren**:
   - Nutze `find_files` und `grep_search`, um relevante Dateien und Definitionen zu lokalisieren.
   - Nutze `view_file` mit Zeilenbereichen (z.B. start_line=1, end_line=50), um den Kontext zu verstehen.
2. **Präzise, minimalinvasive Änderungen**:
   - Nutze `replace_chunk` für gezielte Code-Änderungen anstelle von vollständigen Datei-Überschreibungen.
   - Achte bei `target_content` auf exakte Einrückung und Whitespaces.
3. **Validierung & Sicherheit**:
   - Vor jedem Schreibvorgang wird die Python-Syntax automatisch geprüft.
   - Wenn ein Tool einen Fehler liefert (z.B. SyntaxError oder Target-Block nicht gefunden), analysiere den Fehler mit `view_file` und korrigiere ihn.
4. **Abschluss**:
   - Fasse deine Änderungen in der `<final_answer>` klar zusammen (welche Dateien geändert wurden, warum und was das Ergebnis ist).
"""


class CodeAgent(BaseAgent):
    """
    Spezialisierter Coding-Agent mit ACI-Toolkit.
    """

    def __init__(
        self,
        user_id: Optional[int] = None,
        session_id: Optional[int] = None,
        workspace_root: Optional[str] = None,
        model: str = "qwen2.5-coder:7b",
        max_steps: int = 15
    ):
        super().__init__(
            name="CodeAgent",
            role_description="Spezialist für Code-Analyse, Refactoring, Bugfixing und Patch-Erstellung.",
            system_prompt=CODE_AGENT_SYSTEM_PROMPT,
            model=model,
            max_steps=max_steps
        )
        self.user_id = user_id
        self.session_id = session_id
        self.workspace_root = workspace_root
        self._register_aci_tools()

    def _register_aci_tools(self):
        """Registriert alle ACI-Werkzeuge mit Scope auf den aktuellen Workspace."""
        
        # 1. view_file
        self.register_tool(
            name="view_file",
            description="Liest einen begrenzten Zeilenbereich einer Datei mit Zeilennummern.",
            parameters={
                "type": "object",
                "properties": {
                    "filename": {"type": "string", "description": "Relativer Pfad der Datei im Workspace, z.B. 'main.py'"},
                    "start_line": {"type": "integer", "description": "Startzeile (1-basiert, Standard 1)"},
                    "end_line": {"type": "integer", "description": "Endzeile (inklusive, Standard: start + 100)"}
                },
                "required": ["filename"]
            },
            handler=self._tool_view_file
        )

        # 2. grep_search
        self.register_tool(
            name="grep_search",
            description="Sucht nach einem Textbegriff oder Regex in allen Dateien des Workspaces.",
            parameters={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Suchbegriff oder Regex"},
                    "file_pattern": {"type": "string", "description": "Optionales Dateimuster, z.B. '*.py'"},
                    "case_sensitive": {"type": "boolean", "description": "Groß-/Kleinschreibung beachten (Standard false)"}
                },
                "required": ["query"]
            },
            handler=self._tool_grep_search
        )

        # 3. find_files
        self.register_tool(
            name="find_files",
            description="Listet alle Dateien im Workspace passend zu einem Glob-Muster auf.",
            parameters={
                "type": "object",
                "properties": {
                    "pattern": {"type": "string", "description": "Dateimuster, z.B. '*.py' oder '*.*' (Standard '*')"}
                }
            },
            handler=self._tool_find_files
        )

        # 4. replace_chunk
        self.register_tool(
            name="replace_chunk",
            description="Ersetzt einen exakten Codeblock in einer Datei durch einen neuen Block (mit Syntaxprüfung).",
            parameters={
                "type": "object",
                "properties": {
                    "filename": {"type": "string", "description": "Dateipfad im Workspace"},
                    "target_content": {"type": "string", "description": "Der exakte bestehende Codeblock, der ersetzt werden soll"},
                    "replacement_content": {"type": "string", "description": "Der neue Ersatz-Codeblock"}
                },
                "required": ["filename", "target_content", "replacement_content"]
            },
            handler=self._tool_replace_chunk
        )

        # 5. create_file
        self.register_tool(
            name="create_file",
            description="Erstellt eine neue Datei im Workspace.",
            parameters={
                "type": "object",
                "properties": {
                    "filename": {"type": "string", "description": "Dateipfad im Workspace"},
                    "content": {"type": "string", "description": "Vollständiger Inhalt der neuen Datei"},
                    "overwrite": {"type": "boolean", "description": "Bestehende Datei überschreiben (Standard false)"}
                },
                "required": ["filename", "content"]
            },
            handler=self._tool_create_file
        )

        # 6. delete_file
        self.register_tool(
            name="delete_file",
            description="Löscht eine Datei im Workspace.",
            parameters={
                "type": "object",
                "properties": {
                    "filename": {"type": "string", "description": "Dateipfad im Workspace"}
                },
                "required": ["filename"]
            },
            handler=self._tool_delete_file
        )

        # 7. validate_syntax
        self.register_tool(
            name="validate_syntax",
            description="Prüft Python-Code auf Syntaxfehler ohne ihn auszuführen.",
            parameters={
                "type": "object",
                "properties": {
                    "code": {"type": "string", "description": "Der zu prüfende Python-Code"}
                },
                "required": ["code"]
            },
            handler=lambda code: aci.validate_python_syntax(code)
        )

    # Tool Handlers
    def _tool_view_file(self, filename: str, start_line: int = 1, end_line: Optional[int] = None):
        return aci.view_file(
            path=Path(self.workspace_root) / filename if self.workspace_root else None,
            user_id=self.user_id,
            session_id=self.session_id,
            filename=filename,
            start_line=start_line,
            end_line=end_line
        )

    def _tool_grep_search(self, query: str, file_pattern: Optional[str] = None, case_sensitive: bool = False):
        return aci.grep_search(
            query=query,
            root_dir=self.workspace_root,
            file_pattern=file_pattern,
            case_sensitive=case_sensitive,
            user_id=self.user_id,
            session_id=self.session_id
        )

    def _tool_find_files(self, pattern: str = "*"):
        return aci.find_files(
            root_dir=self.workspace_root,
            pattern=pattern,
            user_id=self.user_id,
            session_id=self.session_id
        )

    def _tool_replace_chunk(self, filename: str, target_content: str, replacement_content: str):
        return aci.replace_chunk(
            target_content=target_content,
            replacement_content=replacement_content,
            path=Path(self.workspace_root) / filename if self.workspace_root else None,
            user_id=self.user_id,
            session_id=self.session_id,
            filename=filename
        )

    def _tool_create_file(self, filename: str, content: str, overwrite: bool = False):
        return aci.create_file(
            content=content,
            path=Path(self.workspace_root) / filename if self.workspace_root else None,
            user_id=self.user_id,
            session_id=self.session_id,
            filename=filename,
            overwrite=overwrite
        )

    def _tool_delete_file(self, filename: str):
        return aci.delete_file(
            path=Path(self.workspace_root) / filename if self.workspace_root else None,
            user_id=self.user_id,
            session_id=self.session_id,
            filename=filename
        )
