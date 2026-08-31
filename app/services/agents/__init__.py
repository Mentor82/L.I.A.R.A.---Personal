"""
Specialized Agents Subsystem für L.I.A.R.A.
"""
from services.agents.base_agent import BaseAgent
from services.agents.code_agent import CodeAgent
from services.agents.research_agent import ResearchAgent
from services.agents.agent_registry import AgentRegistry

__all__ = [
    "BaseAgent",
    "CodeAgent",
    "ResearchAgent",
    "AgentRegistry",
]
