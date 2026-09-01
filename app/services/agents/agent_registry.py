"""
Agent Registry für L.I.A.R.A.
Zentrale Verwaltung und Instanziierung von spezialisierten Agenten-Profilen.
"""
from typing import Dict, List, Any, Optional
from services.agents.base_agent import BaseAgent
from services.agents.code_agent import CodeAgent
from services.agents.research_agent import ResearchAgent
from services.agents.productivity_agent import ProductivityAgent
from services.agents.vision_agent import VisionAgent


class AgentRegistry:
    """
    Registry zur Entdeckung und Instanziierung spezialisierter Agenten.
    """

    _PROFILES: Dict[str, Dict[str, Any]] = {
        "code": {
            "id": "code",
            "name": "Code Agent",
            "description": "Autonomer Software Engineering & Refactoring Agent mit ACI (Agent-Computer Interface).",
            "default_model": "qwen2.5-coder:7b",
            "icon": "💻",
            "category": "development",
            "tools": [
                "view_file",
                "grep_search",
                "find_files",
                "replace_chunk",
                "create_file",
                "delete_file",
                "validate_syntax",
                "run_terminal_command",
                "delegate_research"
            ],
            "class": CodeAgent
        },
        "research": {
            "id": "research",
            "name": "Research Agent",
            "description": "Faktenbasierte Recherche mit Quellenverifizierung über SearXNG, Wikipedia und GitHub.",
            # Cloud model, not a small local one - confirmed live that
            # llama3.2:3b failed to correctly synthesize an answer from real,
            # enriched search source text even when the answer was plainly
            # present in a source.
            "default_model": "gpt-oss:120b-cloud",
            "icon": "🔍",
            "category": "information",
            "tools": [
                "web_search",
                "wikipedia_search",
                "github_search",
                "github_repo_readme",
                "fetch_web_page"
            ],
            "class": ResearchAgent
        },
        "productivity": {
            "id": "productivity",
            "name": "Productivity Agent",
            "description": "Autonome Aufgabenverwaltung, Terminplanung, Notizen und 4D Memory Gedächtnisabruf.",
            "default_model": "llama3.2:3b",
            "icon": "📅",
            "category": "productivity",
            "tools": [
                "create_note",
                "list_notes",
                "create_task",
                "list_tasks",
                "update_task_status",
                "create_calendar_event",
                "list_calendar_events",
                "search_memory",
                "delegate_research"
            ],
            "class": ProductivityAgent
        },
        "vision": {
            "id": "vision",
            "name": "Vision Agent",
            "description": "Optischer Sensor- & Wahrnehmungs-Agent mit 2-Stufen-Befund (VISION_FACTS vs. VISION_INTERPRETATION), OCR und NPU-Objekterkennung.",
            "default_model": "qwen3.5:cloud",
            "icon": "👁️",
            "category": "multimodal",
            "tools": [
                "analyze_image",
                "detect_objects",
                "delegate_research"
            ],
            "class": VisionAgent
        }
    }

    @classmethod
    def list_agents(cls) -> List[Dict[str, Any]]:
        """Gibt eine Übersicht aller registrierten Agenten-Profile zurück."""
        result = []
        for profile in cls._PROFILES.values():
            result.append({
                "id": profile["id"],
                "name": profile["name"],
                "description": profile["description"],
                "default_model": profile["default_model"],
                "icon": profile["icon"],
                "category": profile["category"],
                "tools": profile["tools"]
            })
        return result

    @classmethod
    def get_profile(cls, agent_id: str) -> Optional[Dict[str, Any]]:
        return cls._PROFILES.get(agent_id)

    @classmethod
    def create_agent(
        cls,
        agent_id: str,
        user_id: Optional[int] = None,
        session_id: Optional[int] = None,
        workspace_root: Optional[str] = None,
        model: Optional[str] = None,
        max_steps: Optional[int] = None
    ) -> BaseAgent:
        """Erzeugt eine konfigurierte Instanz des angeforderten Agenten."""
        profile = cls._PROFILES.get(agent_id)
        if not profile:
            raise ValueError(f"Unbekannter Agent-Typ: '{agent_id}'. Verfügbar: {list(cls._PROFILES.keys())}")

        agent_cls = profile["class"]
        chosen_model = model or profile["default_model"]
        steps = max_steps or 12
        uid = user_id or 1

        if agent_cls == CodeAgent:
            return CodeAgent(
                user_id=uid,
                session_id=session_id,
                workspace_root=workspace_root,
                model=chosen_model,
                max_steps=steps
            )
        elif agent_cls == ResearchAgent:
            return ResearchAgent(
                model=chosen_model,
                max_steps=steps
            )
        elif agent_cls == ProductivityAgent:
            return ProductivityAgent(
                user_id=uid,
                model=chosen_model,
                max_steps=steps
            )
        elif agent_cls == VisionAgent:
            return VisionAgent(
                user_id=uid,
                session_id=session_id,
                model=chosen_model,
                max_steps=steps
            )
        else:
            return agent_cls(model=chosen_model, max_steps=steps)
