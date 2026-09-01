"""
Specialized Research Agent für L.I.A.R.A.
Spezialist für mehrstufige Recherchen, Faktenabgleiche und Quellenextraktion.
"""
from typing import Optional, Dict, Any
from services.agents.base_agent import BaseAgent
from services.web_search_service import WebSearchService
from services.search_broker import get_search_broker
from services.github_service import get_github_service


RESEARCH_AGENT_SYSTEM_PROMPT = """Du bist Liaras spezialisierter autonomer Recherche-Agent.
Deine Aufgabe ist es, komplexe Fragestellungen strukturiert, faktenbasiert und mit klaren Quellenangaben zu recherchieren.

### Verhaltensregeln:
1. **Mehrstufige Recherche**:
   - Zerlege komplexe Fragen in gezielte Suchbegriffe.
   - Nutze `web_search` für aktuelle Ereignisse und allgemeine Web-Recherchen.
   - Nutze `wikipedia_search` für Hintergrund- und Basiswissen.
   - Nutze `github_search` und `github_repo_readme` für Open-Source-Projekte, Software-Bibliotheken, Code-Recherchen und GitHub-Analysen.
2. **Quellenvalidierung**:
   - Gleiche Daten und Zahlen zwischen mehreren Quellen ab.
   - Zitiere Quellen immer mit Name und (falls verfügbar) URL.
3. **Strukturierte Zusammenfassung**:
   - Schließe deine Recherche in der `<final_answer>` mit einer klaren Struktur (Kernaussage, Details, Quellenliste) ab.
"""


class ResearchAgent(BaseAgent):
    """
    Spezialisierter Recherche-Agent.
    """

    def __init__(
        self,
        # Cloud model, not a small local one - confirmed live that
        # llama3.2:3b failed to correctly synthesize an answer from real,
        # enriched SearXNG source text even when the answer was plainly
        # present in a source (Bundesliga-table-leader test).
        model: str = "gpt-oss:120b-cloud",
        max_steps: int = 10
    ):
        super().__init__(
            name="ResearchAgent",
            role_description="Spezialist für Internetrecherche, GitHub-Analysen, Faktenprüfung und Wissensaggregation.",
            system_prompt=RESEARCH_AGENT_SYSTEM_PROMPT,
            model=model,
            max_steps=max_steps
        )
        self.search_service = WebSearchService()
        self.search_broker = get_search_broker()
        self.github_service = get_github_service()
        self._register_research_tools()

    def _register_research_tools(self):
        # 1. web_search
        self.register_tool(
            name="web_search",
            description="Durchsucht das Internet nach aktuellen Informationen und Fakten.",
            parameters={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Die Suchanfrage"}
                },
                "required": ["query"]
            },
            handler=self._tool_web_search
        )

        # 2. wikipedia_search
        self.register_tool(
            name="wikipedia_search",
            description="Sucht nach Artikeln und Definitionen in der Wikipedia.",
            parameters={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Suchbegriff"},
                    "language": {"type": "string", "description": "Sprache (de oder en, Standard 'de')"}
                },
                "required": ["query"]
            },
            handler=self._tool_wikipedia_search
        )

        # 3. github_search
        self.register_tool(
            name="github_search",
            description="Durchsucht GitHub nach Open-Source Repositories, Projekten, Programmiersprachen oder Topics.",
            parameters={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Suchbegriff (z.B. 'llm orchestration', 'tts')"},
                    "language": {"type": "string", "description": "Programmiersprache (optional, z.B. 'python', 'rust')"},
                    "sort": {"type": "string", "enum": ["stars", "forks", "updated"], "description": "Sortierung (Standard: 'stars')"},
                    "limit": {"type": "number", "description": "Max Anzahl Repositories (Standard: 5)"}
                },
                "required": ["query"]
            },
            handler=self._tool_github_search
        )

        # 4. github_repo_readme
        self.register_tool(
            name="github_repo_readme",
            description="Lädt die README.md eines GitHub-Repositories (z.B. 'owner/repo') zur Detailanalyse.",
            parameters={
                "type": "object",
                "properties": {
                    "repo": {"type": "string", "description": "Repository im Format 'owner/repo', z.B. 'psf/requests'"}
                },
                "required": ["repo"]
            },
            handler=self._tool_github_readme
        )

        # 5. fetch_web_page
        self.register_tool(
            name="fetch_web_page",
            description="Liest den Textinhalt einer Webseite oder Artikels direkt über ihre URL ab.",
            parameters={
                "type": "object",
                "properties": {
                    "url": {"type": "string", "description": "Die Web-Adresse (z.B. 'https://www.heise.de/...')"}
                },
                "required": ["url"]
            },
            handler=self._tool_fetch_web_page
        )

    async def _tool_web_search(self, query: str) -> Dict[str, Any]:
        try:
            results = await self.search_broker.search(query)
            if not results:
                return {"error": f"Keine Ergebnisse für '{query}' gefunden (Suche nicht verfügbar oder keine Treffer)."}
            return {
                "query": query,
                "results": [
                    {"title": r["title"], "url": r["url"], "snippet": r["snippet"]}
                    for r in results
                ]
            }
        except Exception as e:
            return {"error": f"Websuche fehlgeschlagen: {str(e)}"}

    async def _tool_wikipedia_search(self, query: str, language: str = "de") -> Dict[str, Any]:
        try:
            res = await self.search_service.search_wikipedia(query, language=language)
            return res
        except Exception as e:
            return {"error": f"Wikipedia-Suche fehlgeschlagen: {str(e)}"}

    async def _tool_github_search(self, query: str, language: Optional[str] = None, sort: str = "stars", limit: int = 5, **kwargs) -> Dict[str, Any]:
        return await self.github_service.search_repositories(query=query, language=language, sort=sort, limit=limit)

    async def _tool_github_readme(self, repo: str, **kwargs) -> Dict[str, Any]:
        return await self.github_service.get_repository_readme(repo=repo)

    async def _tool_fetch_web_page(self, url: str, **kwargs) -> Dict[str, Any]:
        from services.tool_executor import get_tool_executor
        return await get_tool_executor()._execute_fetch_web_page({"url": url})


# Cloud model for delegated research sub-tasks, not ResearchAgent's own
# small local default above - confirmed live that llama3.2:3b failed to
# correctly synthesize an answer from real, enriched search source text
# even when the answer was plainly present in a source.
DELEGATION_MODEL = "gpt-oss:120b-cloud"
DELEGATION_MAX_STEPS = 12

DELEGATION_BUDGET_INSTRUCTION = """

### Zusätzliche Regel für diese delegierte Teilaufgabe:
Du hast nur ein knappes Schritt-Budget. Nutze höchstens 2-3 Tool-Aufrufe
insgesamt, dann schließe zwingend mit einer <final_answer> ab - auch wenn
du noch nicht jede denkbare Facette recherchiert hast. Eine solide Antwort
aus 2-3 guten Quellen ist besser als kein Ergebnis, weil das Budget
aufgebraucht wurde."""


async def run_delegated_research(task: str) -> Dict[str, Any]:
    """
    Runs a ResearchAgent sub-instance to completion for a delegated
    sub-task and returns just its final answer/error - shared by both
    delegation call sites (base_agent.py's Agent Hub tool and
    tool_executor.py's normal-chat tool) so the behavior/tuning lives in
    one place instead of two copies drifting apart.

    Appends DELEGATION_BUDGET_INSTRUCTION to the sub-agent's *system*
    prompt rather than just the task text - confirmed live that a hint
    buried in the user-turn task text was not enough: a broad "what's new
    in Python 3.13" question still burned through a 10-step budget with
    that hint in place, while a narrower single-fact lookup finished in 2
    steps regardless. A system-level instruction carries more weight.
    """
    sub_agent = ResearchAgent(model=DELEGATION_MODEL, max_steps=DELEGATION_MAX_STEPS)
    sub_agent.system_prompt += DELEGATION_BUDGET_INSTRUCTION
    result = await sub_agent.run(task=task)
    if result.get("success"):
        return {"answer": result["answer"]}
    return {"error": result.get("error", "Research Agent lieferte kein Ergebnis")}


