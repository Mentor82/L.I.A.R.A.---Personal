"""
🔍 Tool-Call Parser
Extrahiert Tool-Aufrufe aus Ollama-Antworten
"""
import re
import json
from typing import Optional, Dict, Any, List
from dataclasses import dataclass


@dataclass
class ToolCall:
    """Geparster Tool-Aufruf"""
    tool_name: str
    parameters: Dict[str, Any]
    raw_text: str
    confidence: float = 1.0


class ToolCallParser:
    """Parser für Tool-Aufrufe im Ollama-Stream"""
    
    # Pattern für <tool_call>...</tool_call>
    TOOL_CALL_PATTERN = re.compile(
        r'<tool_call>\s*(.*?)\s*</tool_call>',
        re.DOTALL | re.IGNORECASE
    )
    
    # Pattern für JSON-ähnliche Tool-Calls ohne Tags
    JSON_TOOL_PATTERN = re.compile(
        r'\{\s*"tool"\s*:\s*"([^"]+)"\s*,\s*"parameters"\s*:\s*(\{.*?\})\s*\}',
        re.DOTALL
    )
    
    # Pattern für function-call Style (alternative Syntax)
    FUNCTION_CALL_PATTERN = re.compile(
        r'<function>\s*(\w+)\((.*?)\)\s*</function>',
        re.DOTALL
    )
    
    def __init__(self):
        pass
    
    def contains_tool_call(self, text: str) -> bool:
        """
        Schnelle Prüfung ob Text einen Tool-Call enthält
        
        Args:
            text: Zu prüfender Text
            
        Returns:
            True wenn Tool-Call gefunden
        """
        return bool(
            self.TOOL_CALL_PATTERN.search(text) or
            self.JSON_TOOL_PATTERN.search(text) or
            self.FUNCTION_CALL_PATTERN.search(text)
        )
    
    def extract_tool_call(self, text: str) -> Optional[ToolCall]:
        """
        Extrahiert ersten Tool-Call aus Text
        
        Args:
            text: Text mit potenziellem Tool-Call
            
        Returns:
            ToolCall oder None
        """
        # Versuch 1: <tool_call> XML-Style
        match = self.TOOL_CALL_PATTERN.search(text)
        if match:
            return self._parse_xml_style(match)
        
        # Versuch 2: Plain JSON
        match = self.JSON_TOOL_PATTERN.search(text)
        if match:
            return self._parse_json_style(match)
        
        # Versuch 3: <function> Style
        match = self.FUNCTION_CALL_PATTERN.search(text)
        if match:
            return self._parse_function_style(match)
        
        return None
    
    def extract_all_tool_calls(self, text: str) -> List[ToolCall]:
        """
        Extrahiert alle Tool-Calls aus Text
        
        Args:
            text: Text mit potenziellen Tool-Calls
            
        Returns:
            Liste von ToolCalls
        """
        tool_calls = []
        
        # XML-Style
        for match in self.TOOL_CALL_PATTERN.finditer(text):
            call = self._parse_xml_style(match)
            if call:
                tool_calls.append(call)
        
        # JSON-Style
        for match in self.JSON_TOOL_PATTERN.finditer(text):
            call = self._parse_json_style(match)
            if call:
                tool_calls.append(call)
        
        # Function-Style
        for match in self.FUNCTION_CALL_PATTERN.finditer(text):
            call = self._parse_function_style(match)
            if call:
                tool_calls.append(call)
        
        return tool_calls
    
    def _parse_xml_style(self, match: re.Match) -> Optional[ToolCall]:
        """
        Parse <tool_call>{ "tool": "...", "parameters": {...} }</tool_call>
        """
        try:
            json_str = match.group(1).strip()
            data = json.loads(json_str)
            
            return ToolCall(
                tool_name=data.get("tool", ""),
                parameters=data.get("parameters", {}),
                raw_text=match.group(0),
                confidence=1.0
            )
        except (json.JSONDecodeError, KeyError) as e:
            # Fallback: Versuche robusteres Parsing
            return self._fuzzy_parse_json(match.group(1), match.group(0))
    
    def _parse_json_style(self, match: re.Match) -> Optional[ToolCall]:
        """
        Parse direct JSON: { "tool": "...", "parameters": {...} }
        """
        try:
            tool_name = match.group(1)
            params_str = match.group(2)
            parameters = json.loads(params_str)
            
            return ToolCall(
                tool_name=tool_name,
                parameters=parameters,
                raw_text=match.group(0),
                confidence=0.9
            )
        except json.JSONDecodeError:
            return None
    
    def _parse_function_style(self, match: re.Match) -> Optional[ToolCall]:
        """
        Parse <function>tool_name(param1="value", param2=123)</function>
        """
        try:
            tool_name = match.group(1)
            params_str = match.group(2)
            
            # Parse Python-style parameters
            parameters = self._parse_function_params(params_str)
            
            return ToolCall(
                tool_name=tool_name,
                parameters=parameters,
                raw_text=match.group(0),
                confidence=0.8
            )
        except Exception:
            return None
    
    def _parse_function_params(self, params_str: str) -> Dict[str, Any]:
        """
        Parse function-style parameters: param1="value", param2=123
        """
        params = {}
        
        # Split by comma (außerhalb von Strings)
        param_pattern = re.compile(r'(\w+)\s*=\s*(["\']?)([^,]*?)\2(?:,|$)')
        
        for match in param_pattern.finditer(params_str):
            param_name = match.group(1)
            param_value = match.group(3).strip()
            
            # Type conversion
            if param_value.lower() == 'true':
                params[param_name] = True
            elif param_value.lower() == 'false':
                params[param_name] = False
            elif param_value.isdigit():
                params[param_name] = int(param_value)
            elif self._is_float(param_value):
                params[param_name] = float(param_value)
            else:
                params[param_name] = param_value
        
        return params
    
    def _fuzzy_parse_json(self, json_str: str, raw_text: str) -> Optional[ToolCall]:
        """
        Robusteres JSON-Parsing für fehlerhafte Syntax
        """
        try:
            # Versuche gängige Fehler zu korrigieren
            fixed = json_str.replace("'", '"')  # Single quotes → double quotes
            fixed = re.sub(r',\s*}', '}', fixed)  # Trailing commas
            fixed = re.sub(r',\s*]', ']', fixed)
            
            data = json.loads(fixed)
            
            return ToolCall(
                tool_name=data.get("tool", ""),
                parameters=data.get("parameters", {}),
                raw_text=raw_text,
                confidence=0.7
            )
        except:
            return None
    
    def _is_float(self, value: str) -> bool:
        """Prüfe ob String ein Float ist"""
        try:
            float(value)
            return '.' in value
        except ValueError:
            return False
    
    def remove_tool_calls(self, text: str) -> str:
        """
        Entfernt alle Tool-Calls aus Text
        
        Args:
            text: Original-Text
            
        Returns:
            Text ohne Tool-Calls
        """
        # Remove XML-style
        text = self.TOOL_CALL_PATTERN.sub('', text)
        
        # Remove JSON-style
        text = self.JSON_TOOL_PATTERN.sub('', text)
        
        # Remove function-style
        text = self.FUNCTION_CALL_PATTERN.sub('', text)
        
        # Clean up extra whitespace
        text = re.sub(r'\n\n+', '\n\n', text)
        text = text.strip()
        
        return text
    
    def validate_tool_call(self, tool_call: ToolCall, required_params: List[str]) -> bool:
        """
        Validiere ob alle erforderlichen Parameter vorhanden sind
        
        Args:
            tool_call: Der Tool-Call
            required_params: Liste erforderlicher Parameter-Namen
            
        Returns:
            True wenn valide
        """
        return all(
            param in tool_call.parameters
            for param in required_params
        )


# Singleton instance
_parser = None

def get_tool_parser() -> ToolCallParser:
    """Get or create ToolCallParser singleton"""
    global _parser
    if _parser is None:
        _parser = ToolCallParser()
    return _parser
