"""
Specialized Research Agent für L.I.A.R.A.
Spezialist für mehrstufige Recherchen, Faktenabgleiche und Quellenextraktion.
"""
from typing import Optional, Dict, Any
from services.agents.base_agent import BaseAgent
from services.web_search_service import WebSearchService
from services.search_broker import get_search_broker


RESEARCH_AGENT_SYSTEM_PROMPT = """Du bist Liaras spezialisierter autonomer Recherche-Agent.
Deine Aufgabe ist es, komplexe Fragestellungen strukturiert, faktenbasiert und mit klaren Quellenangaben zu recherchieren.

### Verhaltensregeln:
1. **Mehrstufige Recherche**:
   - Zerlege komplexe Fragen in 2-3 gezielte Suchbegriffe.
   - Nutze `web_search` für aktuelle Ereignisse und `wikipedia_search` für Hintergrund- und Basiswissen.
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
        model: str = "llama3.2:3b",
        max_steps: int = 10
    ):
        super().__init__(
            name="ResearchAgent",
            role_description="Spezialist für Internetrecherche, Faktenprüfung und Wissensaggregation.",
            system_prompt=RESEARCH_AGENT_SYSTEM_PROMPT,
            model=model,
            max_steps=max_steps
        )
        self.search_service = WebSearchService()
        self.search_broker = get_search_broker()
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

    async def _tool_web_search(self, query: str) -> Dict[str, Any]:
        # Real web search via the self-hosted SearXNG instance (SearchBroker),
        # same backend chat_streaming.py's general web_search tool uses -
        # web_search_service.py's DuckDuckGo Instant Answer API only returns
        # something for narrow infobox/definition-style queries and comes
        # back empty for the kind of open research questions this agent is
        # actually meant to handle.
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
