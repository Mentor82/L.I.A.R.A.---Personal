"""
🌍 LIARA Web Search Service
Privacy-focused web search integration using DuckDuckGo Instant Answer API
"""

import httpx
from typing import List, Dict, Optional, Any
import logging
from datetime import datetime
import json

logger = logging.getLogger(__name__)

# WMO weather codes used by Open-Meteo -> German descriptions
# https://open-meteo.com/en/docs (see "WMO Weather interpretation codes")
_WMO_WEATHER_CODES = {
    0: "Klarer Himmel", 1: "Überwiegend klar", 2: "Teilweise bewölkt", 3: "Bedeckt",
    45: "Nebel", 48: "Gefrierender Nebel",
    51: "Leichter Nieselregen", 53: "Mäßiger Nieselregen", 55: "Starker Nieselregen",
    56: "Leichter gefrierender Nieselregen", 57: "Starker gefrierender Nieselregen",
    61: "Leichter Regen", 63: "Mäßiger Regen", 65: "Starker Regen",
    66: "Leichter gefrierender Regen", 67: "Starker gefrierender Regen",
    71: "Leichter Schneefall", 73: "Mäßiger Schneefall", 75: "Starker Schneefall",
    77: "Schneegriesel",
    80: "Leichte Regenschauer", 81: "Mäßige Regenschauer", 82: "Heftige Regenschauer",
    85: "Leichte Schneeschauer", 86: "Starke Schneeschauer",
    95: "Gewitter", 96: "Gewitter mit leichtem Hagel", 99: "Gewitter mit starkem Hagel",
}


class WebSearchService:
    """Privacy-focused web search service"""
    
    def __init__(self):
        # DuckDuckGo Instant Answer API (no API key needed, privacy-focused)
        self.ddg_api = "https://api.duckduckgo.com/"
        self.user_agent = "Liara/1.0 (Privacy-focused AI Assistant)"
        self._client = httpx.AsyncClient(timeout=10.0, headers={'User-Agent': self.user_agent})
    
    async def search_instant_answer(self, query: str) -> Dict:
        """
        Search using DuckDuckGo Instant Answer API
        
        Args:
            query: Search query
            
        Returns:
            Structured search result with instant answer
        """
        try:
            params = {
                'q': query,
                'format': 'json',
                'no_redirect': 1,
                'no_html': 1,
                'skip_disambig': 1
            }
            
            response = await self._client.get(self.ddg_api, params=params)
            response.raise_for_status()
            data = response.json()

            result = {
                'query': query,
                'timestamp': datetime.utcnow().isoformat(),
                'abstract': data.get('Abstract', ''),
                'abstract_text': data.get('AbstractText', ''),
                'abstract_source': data.get('AbstractSource', ''),
                'abstract_url': data.get('AbstractURL', ''),
                'heading': data.get('Heading', ''),
                'answer': data.get('Answer', ''),
                'answer_type': data.get('AnswerType', ''),
                'definition': data.get('Definition', ''),
                'definition_source': data.get('DefinitionSource', ''),
                'definition_url': data.get('DefinitionURL', ''),
                'related_topics': [],
                'results': []
            }
            
            # Extract related topics
            for topic in data.get('RelatedTopics', []):
                if 'Text' in topic:
                    result['related_topics'].append({
                        'text': topic.get('Text', ''),
                        'url': topic.get('FirstURL', '')
                    })
            
            # Extract results
            for item in data.get('Results', []):
                result['results'].append({
                    'text': item.get('Text', ''),
                    'url': item.get('FirstURL', '')
                })
            
            logger.info(f"Web search completed for: {query}")
            return result
            
        except httpx.TimeoutException:
            logger.error(f"Search timeout for query: {query}")
            return {'error': 'Search timeout', 'query': query}
        except httpx.HTTPError as e:
            logger.error(f"Search error for query '{query}': {e}")
            return {'error': str(e), 'query': query}

    async def search_wikipedia(self, query: str, language: str = 'de') -> Dict:
        """
        Search Wikipedia for quick facts
        
        Args:
            query: Search query
            language: Language code (de, en, etc.)
            
        Returns:
            Wikipedia summary
        """
        try:
            api_url = f"https://{language}.wikipedia.org/api/rest_v1/page/summary/{query}"

            response = await self._client.get(api_url)
            response.raise_for_status()
            data = response.json()
            
            return {
                'query': query,
                'title': data.get('title', ''),
                'extract': data.get('extract', ''),
                'description': data.get('description', ''),
                'url': data.get('content_urls', {}).get('desktop', {}).get('page', ''),
                'thumbnail': data.get('thumbnail', {}).get('source', ''),
                'timestamp': datetime.utcnow().isoformat()
            }
            
        except httpx.HTTPError as e:
            logger.error(f"Wikipedia search error: {e}")
            return {'error': str(e), 'query': query}

    async def get_weather_info(self, location: str, forecast_days: int = 3) -> Dict:
        """
        Get weather information using open-meteo.com (no API key needed)

        Args:
            location: City name or coordinates
            forecast_days: Days of daily forecast to include alongside the
                current conditions (1-7, same Open-Meteo call, no extra
                request needed - 0 skips the "forecast" key entirely for
                callers that only want current conditions)

        Returns:
            Weather information, plus a "forecast" list of
            {date, condition, temp_max, temp_min, precipitation} when
            forecast_days > 0
        """
        try:
            # First, geocode the location using open-meteo geocoding API
            geocode_url = "https://geocoding-api.open-meteo.com/v1/search"
            geocode_params = {
                'name': location,
                'count': 1,
                'language': 'de',
                'format': 'json'
            }

            geo_response = await self._client.get(geocode_url, params=geocode_params)
            geo_response.raise_for_status()
            geo_data = geo_response.json()

            if not geo_data.get('results'):
                return {'error': f'Location not found: {location}'}

            place = geo_data['results'][0]
            latitude = place['latitude']
            longitude = place['longitude']

            # Get weather data
            weather_url = "https://api.open-meteo.com/v1/forecast"
            weather_params = {
                'latitude': latitude,
                'longitude': longitude,
                'current': 'temperature_2m,relative_humidity_2m,weather_code,wind_speed_10m',
                'timezone': 'Europe/Berlin'
            }
            forecast_days = max(0, min(forecast_days, 7))
            if forecast_days:
                weather_params['daily'] = 'weather_code,temperature_2m_max,temperature_2m_min,precipitation_sum'
                weather_params['forecast_days'] = forecast_days

            weather_response = await self._client.get(weather_url, params=weather_params)
            weather_response.raise_for_status()
            weather_data = weather_response.json()

            current = weather_data.get('current', {})

            result = {
                'location': place['name'],
                'country': place.get('country', ''),
                'latitude': latitude,
                'longitude': longitude,
                'temperature': current.get('temperature_2m'),
                'humidity': current.get('relative_humidity_2m'),
                'wind_speed': current.get('wind_speed_10m'),
                'weather_code': current.get('weather_code'),
                'timestamp': current.get('time'),
                'timezone': weather_data.get('timezone')
            }

            daily = weather_data.get('daily')
            if forecast_days and daily:
                result['forecast'] = [
                    {
                        'date': daily['time'][i],
                        'condition': _WMO_WEATHER_CODES.get(daily['weather_code'][i], 'Unbekannt'),
                        'temp_max': daily['temperature_2m_max'][i],
                        'temp_min': daily['temperature_2m_min'][i],
                        'precipitation': daily['precipitation_sum'][i],
                    }
                    for i in range(len(daily.get('time', [])))
                ]

            return result

        except httpx.HTTPError as e:
            logger.error(f"Weather API error: {e}")
            return {'error': str(e), 'location': location}
    
    def format_for_llm(self, search_result: Dict, result_type: str = 'search') -> str:
        """
        Format search results for LLM context
        
        Args:
            search_result: Search result dictionary
            result_type: Type of result (search, wikipedia, weather)
            
        Returns:
            Formatted string for LLM context
        """
        if 'error' in search_result:
            return f"Search error: {search_result['error']}"
        
        if result_type == 'wikipedia':
            return f"""Wikipedia Information:
Titel: {search_result.get('title', 'N/A')}
Beschreibung: {search_result.get('description', 'N/A')}
Zusammenfassung: {search_result.get('extract', 'N/A')}
URL: {search_result.get('url', 'N/A')}
"""
        
        elif result_type == 'weather':
            condition = _WMO_WEATHER_CODES.get(search_result.get('weather_code'), 'Unbekannt')
            text = f"""Wetter-Information für {search_result.get('location', 'N/A')}:
Wetterlage: {condition}
Temperatur: {search_result.get('temperature', 'N/A')}°C
Luftfeuchtigkeit: {search_result.get('humidity', 'N/A')}%
Windgeschwindigkeit: {search_result.get('wind_speed', 'N/A')} km/h
Stand: {search_result.get('timestamp', 'N/A')}
"""
            forecast = search_result.get('forecast')
            if forecast:
                text += "\nVorhersage:\n"
                for day in forecast:
                    text += (
                        f"{day['date']}: {day['condition']}, "
                        f"{day['temp_min']}°C bis {day['temp_max']}°C, "
                        f"Niederschlag {day['precipitation']} mm\n"
                    )
            return text
        
        else:  # DuckDuckGo instant answer
            parts = []
            
            if search_result.get('abstract_text'):
                parts.append(f"Zusammenfassung: {search_result['abstract_text']}")
                parts.append(f"Quelle: {search_result.get('abstract_source', 'N/A')}")
            
            if search_result.get('answer'):
                parts.append(f"Antwort: {search_result['answer']}")
            
            if search_result.get('definition'):
                parts.append(f"Definition: {search_result['definition']}")
            
            if search_result.get('related_topics'):
                topics = search_result['related_topics'][:3]  # First 3
                parts.append("Verwandte Themen:")
                for topic in topics:
                    parts.append(f"  - {topic['text']}")
            
            return "\n".join(parts) if parts else "Keine direkten Ergebnisse gefunden."


# Singleton instance
_web_search_service: Optional[WebSearchService] = None


def get_web_search_service() -> WebSearchService:
    """Get singleton instance of WebSearchService"""
    global _web_search_service
    if _web_search_service is None:
        _web_search_service = WebSearchService()
    return _web_search_service


def register_web_tools(registry) -> None:
    """Registriert Web-Such- und Webseiten-Lese-Tools in der ToolRegistry."""
    from services.tool_registry import ToolDefinition, ToolParameter, ToolCategory

    # 🌍 Web Search Tool
    registry.register_tool(ToolDefinition(
        name="web_search",
        description=(
            "Durchsucht das Internet nach Informationen. search_type='instant' (Standard) "
            "für schnelle Fakten/Definitionen via DuckDuckGo. search_type='web' für "
            "Recherche-Fragen zu aktuellen Ereignissen oder Themen, die mehrere echte Quellen "
            "brauchen - durchsucht das offene Web (SearXNG) und liefert tatsächlich abgerufene "
            "Quellentexte mit URL/Titel statt nur einem kurzen Snippet. Bei search_type='web' "
            "steuert policy='fresh' die Sortierung nach Aktualität (neueste Quellen zuerst, "
            "Quellen ohne Datum werden markiert) - Standard ist policy='general' (Relevanz). "
            "search_type='images' sucht gezielt nach Bildern zu einem Thema/Motiv (z.B. 'Katzen "
            "Fotos', 'Eiffelturm bei Nacht') - die Bilder werden dem Nutzer direkt als Vorschaubilder "
            "im Chat angezeigt, nicht als Text."
        ),
        category=ToolCategory.INFORMATION,
        parameters=[
            ToolParameter(name="query", type="string", description="Die Suchanfrage", required=True),
            ToolParameter(name="search_type", type="string", description="Art der Suche", required=False, default="instant", enum=["instant", "web", "wikipedia", "images"]),
            ToolParameter(name="language", type="string", description="Sprache der Ergebnisse", required=False, default="de", enum=["de", "en"]),
            ToolParameter(name="policy", type="string", description="Nur für search_type='web': 'general' (Relevanz, Standard) oder 'fresh' (neueste Quellen zuerst)", required=False, default="general", enum=["general", "fresh"])
        ],
        function=_stub_fn,
        requires_consent=True,
        privacy_level="low"
    ))

    # 🌐 Web Page Fetch Tool (direct URL reading / curl-like)
    registry.register_tool(ToolDefinition(
        name="fetch_web_page",
        description=(
            "Liest den Textinhalt einer Webseite (URL) über eine sichere Sandbox ab. "
            "Nutze dieses Tool, wenn der Nutzer dir einen direkten Link (z.B. 'https://...') "
            "nennt oder du einen Artikel, eine Dokumentation oder Webseite im Detail analysieren möchtest."
        ),
        category=ToolCategory.INFORMATION,
        parameters=[
            ToolParameter(name="url", type="string", description="Die vollständige Web-Adresse (z.B. 'https://docs.python.org/3/' oder 'https://www.heise.de/...')", required=True)
        ],
        function=_stub_fn,
        requires_consent=False,
        privacy_level="low"
    ))


async def fetch_web_page_safe(url: str) -> Dict[str, Any]:
    """
    Liest den Textinhalt einer Webseite über die SSRF-gehärtete ProxySandbox ab.
    """
    import asyncio
    from services.web_safety.proxy_sandbox import ProxySandbox

    url_clean = (url or "").strip()
    if not url_clean:
        return {"error": "Keine URL angegeben."}
    if not url_clean.startswith(("http://", "https://")):
        url_clean = "https://" + url_clean

    try:
        sandbox = ProxySandbox()
        fetched = await asyncio.to_thread(sandbox.fetch_safe, url_clean)
        if isinstance(fetched, dict) and fetched.get("error"):
            return {"error": f"Fehler beim Laden der Webseite: {fetched['error']}", "url": url_clean}

        text_content = fetched.get("text_content", "") if isinstance(fetched, dict) else ""
        max_chars = 4000
        truncated_text = text_content[:max_chars] + ("\n\n[... Inhalt für LLM-Kontext gekürzt ...]" if len(text_content) > max_chars else "")

        return {
            "success": True,
            "url": url_clean,
            "title": fetched.get("title", "") if isinstance(fetched, dict) else "",
            "description": fetched.get("description", "") if isinstance(fetched, dict) else "",
            "text": truncated_text,
            "length": len(text_content),
            "is_truncated": len(text_content) > max_chars
        }
    except Exception as e:
        return {"error": f"Abruf der Webseite fehlgeschlagen: {str(e)}", "url": url_clean}


_WMO_WEATHER_CODES = {
    0: "Klarer Himmel", 1: "Überwiegend klar", 2: "Teilweise bewölkt", 3: "Bedeckt",
    45: "Nebel", 48: "Gefrierender Nebel",
    51: "Leichter Nieselregen", 53: "Mäßiger Nieselregen", 55: "Starker Nieselregen",
    56: "Leichter gefrierender Nieselregen", 57: "Starker gefrierender Nieselregen",
    61: "Leichter Regen", 63: "Mäßiger Regen", 65: "Starker Regen",
    66: "Leichter gefrierender Regen", 67: "Starker gefrierender Regen",
    71: "Leichter Schneefall", 73: "Mäßiger Schneefall", 75: "Starker Schneefall",
    77: "Schneegriesel",
    80: "Leichte Regenschauer", 81: "Mäßige Regenschauer", 82: "Heftige Regenschauer",
    85: "Leichte Schneeschauer", 86: "Starke Schneeschauer",
    95: "Gewitter", 96: "Gewitter mit leichtem Hagel", 99: "Gewitter mit starkem Hagel",
}


async def execute_weather_tool(params: Dict[str, Any]) -> Dict[str, Any]:
    """Führt Wetter-Abfrage aus."""
    service = get_web_search_service()
    city = params.get("city")
    country = params.get("country")
    days = params.get("days", 3)
    try:
        days = max(1, min(int(days), 7))
    except (TypeError, ValueError):
        days = 3

    result = await service.get_weather_info(city, forecast_days=days)
    if "error" in result:
        return {"city": city, "country": country, "error": result["error"]}

    return {
        "city": result.get("location", city),
        "country": result.get("country", country),
        "temperature": result.get("temperature"),
        "condition": _WMO_WEATHER_CODES.get(result.get("weather_code"), "Unbekannt"),
        "humidity": result.get("humidity"),
        "wind_speed": result.get("wind_speed"),
        "forecast": result.get("forecast", [])
    }


async def _stub_fn(**kwargs):
    return {"error": "Not implemented"}

