"""
Specialized Code Agent für L.I.A.R.A.
Nutzt das ACI (Agent-Computer Interface) für token-effiziente Software-Entwicklung.
"""
import logging
from typing import Optional, Dict, Any
from pathlib import Path

from services.agents.base_agent import BaseAgent
import services.aci as aci

logger = logging.getLogger(__name__)

# Reuses the exact reasoning already proven live for delegate_research this
# session - reliable at multi-step native tool-calling, so worth the same
# tradeoff (cloud model, no local-hardware contention) for code delegation.
CODE_DELEGATION_MODEL = "gpt-oss:120b-cloud"
CODE_DELEGATION_MAX_STEPS = 15
CODE_DELEGATION_BUDGET_INSTRUCTION = """
### Zusätzliche Regel für diese delegierte Teilaufgabe:
Du hast nur ein knappes Schritt-Budget. Priorisiere die wichtigste Änderung
zuerst, nutze `view_file`/`grep_search` sparsam, und schließe zwingend mit
einer <final_answer> ab, sobald die Kernänderung steht - auch wenn nicht
jede denkbare Verbesserung erledigt ist.
"""


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
        max_steps: int = 15,
        propose_only: bool = False
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
        # True for the normal-chat delegation path (delegate_code_task): every
        # write becomes a pending proposal the user must accept in the
        # Workspace tab (session_workspace.create_proposal), same gate
        # workspace_propose_change already uses - not a direct write like the
        # Agent Hub's own CodeAgent usage. run_terminal_command is skipped
        # entirely in this mode (see _register_aci_tools) since its writes
        # can't cleanly reduce to a single filename+content proposal.
        self.propose_only = propose_only
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
            description=(
                "Schlägt einen Ersatz für einen exakten Codeblock in einer Datei vor (mit "
                "Syntaxprüfung). Ändert NICHTS direkt - der Nutzer sieht den Vorschlag mit Diff "
                "im Workspace-Tab und muss ihn explizit annehmen."
                if self.propose_only else
                "Ersetzt einen exakten Codeblock in einer Datei durch einen neuen Block (mit Syntaxprüfung)."
            ),
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
            description=(
                "Schlägt eine neue Datei im Workspace vor. Ändert NICHTS direkt - der Nutzer "
                "sieht den Vorschlag mit Diff im Workspace-Tab und muss ihn explizit annehmen."
                if self.propose_only else
                "Erstellt eine neue Datei im Workspace."
            ),
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
            description=(
                "Schlägt das Löschen einer Datei im Workspace vor. Ändert NICHTS direkt - der "
                "Nutzer muss den Vorschlag im Workspace-Tab explizit annehmen."
                if self.propose_only else
                "Löscht eine Datei im Workspace."
            ),
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

        # 8. run_terminal_command - reuses code_sandbox.py's run_code()
        # (same sandbox as the Workspace "Run" button: unprivileged
        # liara-runner user, network-isolated, time/memory/process limits)
        # with language="bash" instead of an interpreter, so no new sudoers
        # rule was needed - run_sandboxed.sh already whitelists this exact
        # invocation shape, just with a new bash|sh case added to its own
        # language dispatch. Skipped entirely in propose_only mode: its
        # side effects (arbitrary shell script output) don't reduce to a
        # single filename+content proposal the way create_file/replace_chunk/
        # delete_file do, and the normal-chat delegation path is meant to be
        # strictly more conservative than the Agent Hub's own CodeAgent use.
        if not self.propose_only:
            self.register_tool(
                name="run_terminal_command",
                description=(
                    "Führt einen einzelnen Shell-Befehl in der sandboxed Session-Umgebung aus "
                    "(unprivilegierter Nutzer, netzwerk-isoliert, Zeit-/Speicher-/Prozess-Limits, "
                    "KEIN Internetzugriff). Nutze dies z.B. zum Ausführen von Tests, Inspizieren von "
                    "Dateien (find/wc/grep/cat) oder kurzen Berechnungen. NICHT für 'pip install' "
                    "(dafür workspace_propose_dependency_change nutzen, das braucht Netzzugriff) und "
                    "NICHT für interaktive Programme (kein stdin-Dialog möglich, nur ein Aufruf mit "
                    "vollständigem Ergebnis)."
                ),
                parameters={
                    "type": "object",
                    "properties": {
                        "command": {"type": "string", "description": "Der auszuführende Shell-Befehl"}
                    },
                    "required": ["command"]
                },
                handler=self._tool_run_terminal_command
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

    def _require_propose_context(self) -> Optional[Dict[str, Any]]:
        if self.user_id is None or self.session_id is None:
            return {"error": "Kein aktiver Workspace (keine Chat-Session) - Vorschläge brauchen eine Session."}
        return None

    def _tool_replace_chunk(self, filename: str, target_content: str, replacement_content: str):
        if self.propose_only:
            err = self._require_propose_context()
            if err:
                return err
            dry = aci.replace_chunk(
                target_content=target_content,
                replacement_content=replacement_content,
                user_id=self.user_id,
                session_id=self.session_id,
                filename=filename,
                dry_run=True
            )
            if not dry.get("success"):
                return dry
            from services.session_workspace import create_proposal
            res = create_proposal(
                self.user_id, self.session_id, filename, "update",
                dry["new_content"], f"Von delegate_code_task vorgeschlagen: {filename}"
            )
            if not res.get("ok"):
                return {"success": False, "error": res.get("error", "Vorschlag fehlgeschlagen")}
            return {"success": True, "filename": filename, "proposed": True, "message": f"Änderung an {filename} als Vorschlag angelegt - Nutzer muss noch bestätigen."}

        return aci.replace_chunk(
            target_content=target_content,
            replacement_content=replacement_content,
            path=Path(self.workspace_root) / filename if self.workspace_root else None,
            user_id=self.user_id,
            session_id=self.session_id,
            filename=filename
        )

    def _tool_create_file(self, filename: str, content: str, overwrite: bool = False):
        if self.propose_only:
            err = self._require_propose_context()
            if err:
                return err
            from services.session_workspace import create_proposal
            action = "update" if overwrite else "create"
            res = create_proposal(
                self.user_id, self.session_id, filename, action,
                content, f"Von delegate_code_task vorgeschlagen: {filename}"
            )
            if not res.get("ok"):
                return {"success": False, "error": res.get("error", "Vorschlag fehlgeschlagen")}
            return {"success": True, "filename": filename, "proposed": True, "message": f"Neue Datei {filename} als Vorschlag angelegt - Nutzer muss noch bestätigen."}

        return aci.create_file(
            content=content,
            path=Path(self.workspace_root) / filename if self.workspace_root else None,
            user_id=self.user_id,
            session_id=self.session_id,
            filename=filename,
            overwrite=overwrite
        )

    def _tool_delete_file(self, filename: str):
        if self.propose_only:
            err = self._require_propose_context()
            if err:
                return err
            from services.session_workspace import create_proposal
            res = create_proposal(
                self.user_id, self.session_id, filename, "delete",
                None, f"Von delegate_code_task vorgeschlagen: Löschen von {filename}"
            )
            if not res.get("ok"):
                return {"success": False, "error": res.get("error", "Vorschlag fehlgeschlagen")}
            return {"success": True, "filename": filename, "proposed": True, "message": f"Löschen von {filename} als Vorschlag angelegt - Nutzer muss noch bestätigen."}

        return aci.delete_file(
            path=Path(self.workspace_root) / filename if self.workspace_root else None,
            user_id=self.user_id,
            session_id=self.session_id,
            filename=filename
        )

    def _tool_run_terminal_command(self, command: str) -> Dict[str, Any]:
        if not self.user_id or not self.session_id:
            return {"error": "Kein aktiver Workspace (keine Chat-Session) - run_terminal_command braucht eine Session."}

        from services.session_workspace import SESSION_FILES_DIR
        from services.code_sandbox import run_code

        session_dir = SESSION_FILES_DIR / str(self.user_id) / str(self.session_id)
        result = run_code(
            "bash", command, session_dir,
            user_id=self.user_id, session_id=self.session_id,
        )
        if result.error:
            return {"error": result.error}
        return {
            "stdout": result.stdout,
            "stderr": result.stderr,
            "exit_code": result.exit_code,
            "timed_out": result.timed_out,
            "files_changed": [f.name for f in result.files],
        }


# Maps a proposed file's extension to the language string both validator
# services expect. Files with no mapped extension (docs, config formats
# neither service knows) are skipped for validation entirely rather than
# forcing a guess - not every proposal is code.
PROPOSAL_VALIDATION_LANGUAGES = {
    "py": "python", "js": "javascript", "jsx": "javascript", "mjs": "javascript", "cjs": "javascript",
    "ts": "typescript", "tsx": "typescript",
    "sh": "bash", "bash": "bash",
    "json": "json", "yml": "yaml", "yaml": "yaml",
    "c": "c", "cpp": "cpp", "cc": "cpp", "h": "c", "hpp": "cpp",
    "go": "go", "rs": "rust", "php": "php", "rb": "ruby",
    "sql": "sql", "html": "html", "htm": "html", "css": "css", "java": "java",
}


async def _run_background_proposal_validation(user_id: int, session_id: int, proposals: list) -> None:
    """
    Fire-and-forget background check for proposals a delegated CodeAgent run
    just created - never awaited by the caller, so it can take as long as it
    needs (the MCP semantic review is itself an LLM call) without adding a
    millisecond of latency to the chat response that triggered it. Writes
    straight onto the proposal via attach_proposal_validation() once done -
    the Workspace tab's own proposal list is the "visible follow-up card"
    here, not a second chat message, since that's exactly where the user
    already looks to decide whether to accept.
    """
    from datetime import datetime, timezone
    from services.session_workspace import attach_proposal_validation

    for p in proposals:
        if p.get("action") == "delete" or not p.get("new_content"):
            continue
        filename = p.get("filename", "")
        ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
        language = PROPOSAL_VALIDATION_LANGUAGES.get(ext)
        if not language:
            continue

        code = p["new_content"]
        validation: Dict[str, Any] = {
            "filename": filename,
            "language": language,
            "checked_at": datetime.now(timezone.utc).isoformat(),
        }

        try:
            from services.ai_validator_service import get_ai_validator_service
            validator = await get_ai_validator_service()
            syntax_result = await validator.validate_code(code, language)
            validation["syntax"] = {
                "status": syntax_result.status,
                "errors": [e.model_dump() for e in syntax_result.errors],
                "warnings": [w.model_dump() for w in syntax_result.warnings],
            }
        except Exception as e:
            validation["syntax"] = {"status": "error", "message": str(e)}

        try:
            from services.ai_validator_mcp_service import get_mcp_validator
            mcp = await get_mcp_validator()
            validation["semantic"] = await mcp.code_review(code, language)
        except Exception as e:
            validation["semantic"] = {"status": "error", "message": str(e)}

        try:
            attach_proposal_validation(user_id, session_id, p["id"], validation)
        except Exception as e:
            logger.error(f"Failed to attach validation to proposal {p.get('id')}: {e}")


async def run_delegated_code_task(task: str, user_id: Optional[int], session_id: Optional[int]) -> Dict[str, Any]:
    """
    Runs a CodeAgent sub-instance (propose_only=True - every write becomes a
    pending Workspace proposal, never a direct write) to completion for a
    delegated code task from the normal chat, mirroring research_agent.py's
    run_delegated_research(). Requires an active Workspace session (the same
    session_id as the chat itself) since CodeAgent's ACI tools operate on
    session-scoped files - there's no sensible "code task" without one.

    Diffs the pending-proposal list before/after the run (rather than
    threading proposal_id through every tool handler's return value back up
    through base_agent.py's generic history_log, which doesn't currently
    capture tool *results* at all, only calls) to find exactly which
    proposals this run just created, then kicks off background validation
    for them - fire-and-forget, never awaited here.
    """
    if user_id is None or session_id is None:
        return {"error": "delegate_code_task braucht eine aktive Workspace-Session (Chat mit Session-ID)."}

    from services.session_workspace import list_proposals
    before_ids = {p["id"] for p in list_proposals(user_id, session_id, status="pending")}

    sub_agent = CodeAgent(
        user_id=user_id,
        session_id=session_id,
        model=CODE_DELEGATION_MODEL,
        max_steps=CODE_DELEGATION_MAX_STEPS,
        propose_only=True,
    )
    sub_agent.system_prompt += CODE_DELEGATION_BUDGET_INSTRUCTION
    result = await sub_agent.run(task=task, user_id=user_id, session_id=session_id)

    new_proposals = [
        p for p in list_proposals(user_id, session_id, status="pending")
        if p["id"] not in before_ids
    ]
    if new_proposals:
        import asyncio
        asyncio.create_task(_run_background_proposal_validation(user_id, session_id, new_proposals))

    if result.get("success"):
        return {"answer": result["answer"]}
    if result.get("paused"):
        return {
            "answer": result.get("continuation_summary")
                or "Aufgabe pausiert (Schritt-Budget aufgebraucht) - Fortschritt wurde gespeichert.",
            "paused": True,
        }
    return {"error": result.get("error", "Code Agent lieferte kein Ergebnis")}
