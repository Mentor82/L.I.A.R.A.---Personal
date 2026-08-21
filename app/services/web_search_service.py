"""
🌍 LIARA Web Search Service
Privacy-focused web search integration using DuckDuckGo Instant Answer API
"""

import httpx
import requests  # For synchronous Wikipedia API calls
from typing import List, Dict, Optional
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
            
            response = requests.get(
                self.ddg_api,
                params=params,
                headers={'User-Agent': self.user_agent},
                timeout=10
            )
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
            
        except requests.exceptions.Timeout:
            logger.error(f"Search timeout for query: {query}")
            return {'error': 'Search timeout', 'query': query}
        except requests.exceptions.RequestException as e:
            logger.error(f"Search error for query '{query}': {e}")
            return {'error': str(e), 'query': query}
    
    def search_wikipedia(self, query: str, language: str = 'de') -> Dict:
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
            
            response = requests.get(
                api_url,
                headers={'User-Agent': self.user_agent},
                timeout=10
            )
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
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Wikipedia search error: {e}")
            return {'error': str(e), 'query': query}
    
    def get_weather_info(self, location: str) -> Dict:
        """
        Get weather information using open-meteo.com (no API key needed)
        
        Args:
            location: City name or coordinates
            
        Returns:
            Weather information
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
            
            geo_response = requests.get(geocode_url, params=geocode_params, timeout=10)
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
            
            weather_response = requests.get(weather_url, params=weather_params, timeout=10)
            weather_response.raise_for_status()
            weather_data = weather_response.json()
            
            current = weather_data.get('current', {})
            
            return {
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
            
        except requests.exceptions.RequestException as e:
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
            return f"""Wetter-Information für {search_result.get('location', 'N/A')}:
Wetterlage: {condition}
Temperatur: {search_result.get('temperature', 'N/A')}°C
Luftfeuchtigkeit: {search_result.get('humidity', 'N/A')}%
Windgeschwindigkeit: {search_result.get('wind_speed', 'N/A')} km/h
Stand: {search_result.get('timestamp', 'N/A')}
"""
        
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
