"""
🐙 LIARA GitHub Research Service
Zentrale Schnittstelle zur kostenfreien GitHub REST API für Repository-, Code- und README-Recherchen.
"""

import os
import base64
import logging
from typing import List, Dict, Optional, Any
import httpx

logger = logging.getLogger(__name__)

GITHUB_API_BASE = "https://api.github.com"
DEFAULT_USER_AGENT = "Liara-AI-Assistant/1.0 (+https://liara.lan)"


class GithubService:
    """Service für GitHub-Recherchen (Repositories, Code, READMEs)."""

    def __init__(self, token: Optional[str] = None):
        self.token = token or os.getenv("GITHUB_TOKEN") or os.getenv("GH_TOKEN")
        self._headers = {
            "Accept": "application/vnd.github+json",
            "User-Agent": DEFAULT_USER_AGENT,
            "X-GitHub-Api-Version": "2022-11-28",
        }
        if self.token:
            self._headers["Authorization"] = f"Bearer {self.token}"

    def _get_client(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(timeout=15.0, headers=self._headers, follow_redirects=True)

    async def search_repositories(
        self,
        query: str,
        language: Optional[str] = None,
        sort: str = "stars",
        limit: int = 5
    ) -> Dict[str, Any]:
        """
        Sucht nach Repositories auf GitHub.

        Args:
            query: Suchbegriff (z.B. "text to speech", "fastapi sse")
            language: Optionale Programmiersprache (z.B. "python", "typescript", "rust")
            sort: Sortierung ("stars", "forks", "updated", "help-wanted-issues")
            limit: Max Anzahl der Ergebnisse (1-20, Standard: 5)
        """
        limit = min(max(int(limit), 1), 20)
        q_parts = [query.strip()]
        if language:
            q_parts.append(f"language:{language.strip()}")
        final_query = " ".join(q_parts)

        params = {
            "q": final_query,
            "sort": sort,
            "order": "desc",
            "per_page": limit
        }

        try:
            async with self._get_client() as client:
                resp = await client.get(f"{GITHUB_API_BASE}/search/repositories", params=params)
                if resp.status_code == 403:
                    rate_limit_reset = resp.headers.get("X-RateLimit-Reset")
                    return {
                        "error": "GitHub API Rate-Limit erreicht. Bitte später erneut versuchen oder GITHUB_TOKEN hinterlegen.",
                        "rate_limited": True,
                        "reset_timestamp": rate_limit_reset
                    }
                resp.raise_for_status()
                data = resp.json()

            items = data.get("items", [])
            results = []
            for item in items:
                license_info = item.get("license") or {}
                results.append({
                    "full_name": item.get("full_name"),
                    "name": item.get("name"),
                    "owner": (item.get("owner") or {}).get("login"),
                    "description": item.get("description") or "Keine Beschreibung vorhanden",
                    "stars": item.get("stargazers_count", 0),
                    "forks": item.get("forks_count", 0),
                    "language": item.get("language"),
                    "license": license_info.get("spdx_id") or license_info.get("name") or "Unbekannt",
                    "html_url": item.get("html_url"),
                    "updated_at": item.get("updated_at"),
                    "topics": item.get("topics", [])
                })

            return {
                "success": True,
                "query": final_query,
                "total_count": data.get("total_count", len(results)),
                "count": len(results),
                "repositories": results
            }
        except httpx.HTTPError as e:
            logger.warning(f"GitHub repository search failed: {e}")
            return {"error": f"GitHub Suche fehlgeschlagen: {str(e)}"}
        except Exception as e:
            logger.error(f"Unexpected error during GitHub search: {e}", exc_info=True)
            return {"error": f"Fehler bei GitHub-Suche: {str(e)}"}

    async def get_repository_readme(self, repo: str) -> Dict[str, Any]:
        """
        Holt die README.md eines Repositories ab (z.B. 'fastapi/fastapi').
        """
        repo_clean = repo.strip().strip("/")
        if "/" not in repo_clean:
            return {"error": "Repository muss im Format 'owner/repo' angegeben werden, z.B. 'tiangolo/fastapi'"}

        headers = {**self._headers, "Accept": "application/vnd.github.raw+json"}
        try:
            async with httpx.AsyncClient(timeout=15.0, headers=headers, follow_redirects=True) as client:
                resp = await client.get(f"{GITHUB_API_BASE}/repos/{repo_clean}/readme")
                if resp.status_code == 404:
                    return {"error": f"Keine README für Repository '{repo_clean}' gefunden."}
                elif resp.status_code == 403:
                    return {"error": "GitHub API Rate-Limit erreicht."}
                resp.raise_for_status()
                raw_text = resp.text

            # Truncate content sensibly for LLMs
            max_len = 3000
            truncated = raw_text[:max_len] + ("\n\n[... Inhalt für LLM-Kontext gekürzt ...]" if len(raw_text) > max_len else "")

            return {
                "success": True,
                "repository": repo_clean,
                "readme": truncated,
                "length": len(raw_text),
                "is_truncated": len(raw_text) > max_len
            }
        except httpx.HTTPError as e:
            logger.warning(f"GitHub README fetch failed for {repo_clean}: {e}")
            return {"error": f"README-Abruf fehlgeschlagen: {str(e)}"}
        except Exception as e:
            logger.error(f"Unexpected error fetching README for {repo_clean}: {e}")
            return {"error": f"Fehler beim Laden der README: {str(e)}"}

    async def search_code(
        self,
        query: str,
        repo: Optional[str] = None,
        language: Optional[str] = None,
        limit: int = 5
    ) -> Dict[str, Any]:
        """
        Sucht nach Code-Dateien auf GitHub.
        """
        limit = min(max(int(limit), 1), 15)
        q_parts = [query.strip()]
        if repo:
            q_parts.append(f"repo:{repo.strip()}")
        if language:
            q_parts.append(f"language:{language.strip()}")
        final_query = " ".join(q_parts)

        params = {
            "q": final_query,
            "per_page": limit
        }

        try:
            async with self._get_client() as client:
                resp = await client.get(f"{GITHUB_API_BASE}/search/code", params=params)
                if resp.status_code == 403:
                    return {"error": "GitHub Code-Search API Rate-Limit erreicht (erfordert meist ein GitHub-Token)."}
                resp.raise_for_status()
                data = resp.json()

            items = data.get("items", [])
            results = []
            for item in items:
                repo_info = item.get("repository") or {}
                results.append({
                    "name": item.get("name"),
                    "path": item.get("path"),
                    "repository": repo_info.get("full_name"),
                    "html_url": item.get("html_url")
                })

            return {
                "success": True,
                "query": final_query,
                "total_count": data.get("total_count", len(results)),
                "count": len(results),
                "code_results": results
            }
        except httpx.HTTPError as e:
            logger.warning(f"GitHub code search failed: {e}")
            return {"error": f"GitHub Code-Suche fehlgeschlagen: {str(e)}"}


_github_service = None

def get_github_service() -> GithubService:
    """Singleton getter für GithubService"""
    global _github_service
    if _github_service is None:
        _github_service = GithubService()
    return _github_service


def register_github_tools(registry) -> None:
    """Registriert GitHub-Recherche-Tools in der ToolRegistry."""
    from services.tool_registry import ToolDefinition, ToolParameter, ToolCategory

    registry.register_tool(ToolDefinition(
        name="github_search",
        description=(
            "Durchsucht GitHub nach Open-Source Repositories, Projekten oder Themen. "
            "Liefert Reponame, Sterne, Forks, Lizenz, Beschreibung, URL und Topics."
        ),
        category=ToolCategory.INFORMATION,
        parameters=[
            ToolParameter(name="query", type="string", description="Die Suchanfrage (z.B. 'voice assistant', 'fastapi sse')", required=True),
            ToolParameter(name="language", type="string", description="Filter nach Programmiersprache (z.B. 'python', 'rust', 'typescript')", required=False),
            ToolParameter(name="sort", type="string", description="Sortierung ('stars', 'forks', 'updated')", required=False, default="stars", enum=["stars", "forks", "updated"]),
            ToolParameter(name="limit", type="number", description="Max Anzahl der Ergebnisse (Standard: 5)", required=False, default=5)
        ],
        function=_stub_fn,
        requires_consent=False,
        privacy_level="low"
    ))

    registry.register_tool(ToolDefinition(
        name="github_repo_readme",
        description="Liest die README.md eines GitHub-Repositories (z.B. 'tiangolo/fastapi') zur Analyse ab.",
        category=ToolCategory.INFORMATION,
        parameters=[
            ToolParameter(name="repo", type="string", description="Repository im Format 'owner/repo', z.B. 'psf/requests' oder 'tiangolo/fastapi'", required=True)
        ],
        function=_stub_fn,
        requires_consent=False,
        privacy_level="low"
    ))


async def _stub_fn(**kwargs):
    return {"error": "Not implemented"}

