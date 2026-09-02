"""
AI Validator MCP Service - Integration with Ollama MCP Server
Uses Model Context Protocol for code validation and model management
Supports direct MCP calls to Port 3333
"""

import httpx
import logging
from typing import Optional, Dict, List, Any, AsyncGenerator
from pydantic import BaseModel
from datetime import datetime
import asyncio
import json

logger = logging.getLogger(__name__)

# MCP Configuration
MCP_HOST = "192.168.178.150"
MCP_PORT = 3333
MCP_URL = f"http://{MCP_HOST}:{MCP_PORT}"
MCP_TIMEOUT = 30.0

# "qwen2.5-coder:7b" (the previous default here) isn't actually pulled on
# this MCP adapter's Ollama backend - confirmed live via GET /models, every
# call defaulting to it was silently failing with a 502. gpt-oss:120b-cloud
# is the same model already proven reliable this session for structured/
# JSON output elsewhere (delegate_code_task, context compaction) - these
# calls are all background/fire-and-forget, so its extra size costs nothing
# a user waits on.
MCP_CODE_MODEL = "gpt-oss:120b-cloud"

# ============================================================================
# RESPONSE MODELS
# ============================================================================

class MCPTool(BaseModel):
    """MCP Tool Definition"""
    name: str
    description: str
    method: str
    path: str
    parameters: Dict[str, Any] = {}

class MCPModel(BaseModel):
    """Ollama Model Info"""
    name: str
    size: Optional[int] = None
    digest: Optional[str] = None
    modified_at: Optional[str] = None

class MCPGenerateRequest(BaseModel):
    """Request for MCP text generation"""
    model: str
    prompt: str
    stream: bool = False
    options: Optional[Dict[str, Any]] = None

class MCPGenerateResponse(BaseModel):
    """Response from MCP text generation"""
    model: str
    response: str
    done: bool
    context: Optional[List[int]] = None
    total_duration: Optional[int] = None
    load_duration: Optional[int] = None
    prompt_eval_count: Optional[int] = None
    eval_count: Optional[int] = None

# ============================================================================
# MCP VALIDATOR SERVICE
# ============================================================================

class MCPValidatorService:
    """Service for remote AI validation via MCP (Ollama)"""
    
    def __init__(self, host: str = MCP_HOST, port: int = MCP_PORT):
        self.host = host
        self.port = port
        self.url = f"http://{host}:{port}"
        self.client: Optional[httpx.AsyncClient] = None
        self.tools_cache: Optional[List[MCPTool]] = None
        self.models_cache: Optional[List[MCPModel]] = None
    
    async def __aenter__(self):
        """Async context manager entry"""
        self.client = httpx.AsyncClient(timeout=MCP_TIMEOUT)
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self.client:
            await self.client.aclose()
    
    async def health_check(self) -> bool:
        """Check MCP server health"""
        try:
            # Try to list models - simple health check
            models = await self.list_models()
            is_healthy = models is not None and len(models) > 0
            
            log_msg = f"✅ MCP Server healthy ({len(models)} models available)" if is_healthy else "❌ MCP Server unhealthy"
            logger.info(log_msg)
            return is_healthy
        except Exception as e:
            logger.error(f"❌ MCP health check failed: {str(e)}")
            return False
    
    async def list_tools(self) -> List[MCPTool]:
        """List available MCP tools"""
        if self.tools_cache:
            return self.tools_cache
        
        try:
            if not self.client:
                self.client = httpx.AsyncClient(timeout=MCP_TIMEOUT)
            
            response = await self.client.get(f"{self.url}/tools")
            response.raise_for_status()
            
            tools_data = response.json()
            tools = [MCPTool(**tool) for tool in tools_data.get("tools", [])]
            self.tools_cache = tools
            
            logger.info(f"📋 MCP Tools available: {[t.name for t in tools]}")
            return tools
        except Exception as e:
            logger.error(f"Failed to list MCP tools: {str(e)}")
            return []
    
    async def list_models(self) -> List[MCPModel]:
        """List available Ollama models via MCP"""
        try:
            if not self.client:
                self.client = httpx.AsyncClient(timeout=MCP_TIMEOUT)
            
            response = await self.client.get(f"{self.url}/models")
            response.raise_for_status()
            
            models_data = response.json()
            models = [MCPModel(**model) for model in models_data.get("models", [])]
            
            logger.info(f"🤖 Available Models: {[m.name for m in models]}")
            return models
        except Exception as e:
            logger.error(f"Failed to list models: {str(e)}")
            return []
    
    async def generate_text(
        self,
        model: str,
        prompt: str,
        stream: bool = False,
        temperature: float = 0.7,
        top_p: float = 0.9,
        num_predict: int = 256
    ) -> Optional[MCPGenerateResponse]:
        """Generate text using Ollama model via MCP"""
        try:
            if not self.client:
                self.client = httpx.AsyncClient(timeout=MCP_TIMEOUT)
            
            payload = {
                "model": model,
                "prompt": prompt,
                "stream": stream,
                "options": {
                    "temperature": temperature,
                    "top_p": top_p,
                    "num_predict": num_predict
                }
            }
            
            response = await self.client.post(
                f"{self.url}/generate",
                json=payload
            )
            response.raise_for_status()
            
            data = response.json()
            result = MCPGenerateResponse(**data)
            
            logger.info(f"✅ Generated text using {model}")
            return result
        except Exception as e:
            logger.error(f"Failed to generate text: {str(e)}")
            return None
    
    async def validate_code_with_model(
        self,
        code: str,
        language: str,
        model: str = MCP_CODE_MODEL
    ) -> Dict[str, Any]:
        """
        Use AI model to validate/analyze code
        Returns semantic validation results
        """
        try:
            prompt = f"""Analyze the following {language} code for errors, issues, and improvements.
Respond in JSON format with "errors", "warnings", "suggestions" arrays.

Code:
```{language}
{code}
```

Respond ONLY with valid JSON, no other text."""
            
            result = await self.generate_text(
                model=model,
                prompt=prompt,
                temperature=0.3,  # Lower temp for consistency
                num_predict=1024
            )
            
            if not result:
                return {"status": "error", "message": "Generation failed"}
            
            # Parse JSON response
            try:
                analysis = json.loads(result.response)
                return {
                    "status": "ok" if not analysis.get("errors") else "error",
                    "language": language,
                    "model": model,
                    "analysis": analysis,
                    "total_duration_ms": result.total_duration / 1_000_000 if result.total_duration else None
                }
            except json.JSONDecodeError:
                return {
                    "status": "ok",
                    "language": language,
                    "model": model,
                    "raw_analysis": result.response
                }
        except Exception as e:
            logger.error(f"Code validation failed: {str(e)}")
            return {"status": "error", "message": str(e)}
    
    async def code_review(
        self,
        code: str,
        language: str,
        focus: str = "general"  # general, security, performance, readability
    ) -> Dict[str, Any]:
        """
        Perform semantic code review using AI
        Focus areas: general, security, performance, readability
        """
        try:
            focus_prompt = {
                "security": "Focus on security vulnerabilities, input validation, and safe practices.",
                "performance": "Focus on performance issues, inefficiencies, and optimization opportunities.",
                "readability": "Focus on code clarity, naming, structure, and documentation.",
                "general": "Perform a general code review covering all aspects."
            }.get(focus, "Perform a general code review.")
            
            prompt = f"""Perform a code review of the following {language} code.
{focus_prompt}

Code:
```{language}
{code}
```

Provide your review in JSON format with "issues", "improvements", "rating" (1-10).
Respond ONLY with valid JSON."""
            
            result = await self.generate_text(
                model=MCP_CODE_MODEL,
                prompt=prompt,
                temperature=0.4,
                num_predict=2048
            )
            
            if not result:
                return {"status": "error", "message": "Review failed"}
            
            try:
                review = json.loads(result.response)
                return {
                    "status": "ok",
                    "language": language,
                    "focus": focus,
                    "review": review
                }
            except json.JSONDecodeError:
                return {
                    "status": "ok",
                    "language": language,
                    "focus": focus,
                    "raw_review": result.response
                }
        except Exception as e:
            logger.error(f"Code review failed: {str(e)}")
            return {"status": "error", "message": str(e)}
    
    async def suggest_fixes(
        self,
        code: str,
        language: str,
        issues: List[str]
    ) -> Dict[str, Any]:
        """Generate fix suggestions for code issues"""
        try:
            issues_str = "\n".join(f"- {issue}" for issue in issues)
            
            prompt = f"""Fix the following issues in {language} code:
{issues_str}

Original code:
```{language}
{code}
```

Provide the fixed code in JSON format with "fixed_code" and "explanation".
Respond ONLY with valid JSON."""
            
            result = await self.generate_text(
                model=MCP_CODE_MODEL,
                prompt=prompt,
                temperature=0.2,
                num_predict=2048
            )
            
            if not result:
                return {"status": "error", "message": "Fix generation failed"}
            
            try:
                fixes = json.loads(result.response)
                return {
                    "status": "ok",
                    "language": language,
                    "fixes": fixes
                }
            except json.JSONDecodeError:
                return {
                    "status": "ok",
                    "language": language,
                    "raw_fixes": result.response
                }
        except Exception as e:
            logger.error(f"Fix suggestion failed: {str(e)}")
            return {"status": "error", "message": str(e)}


# ============================================================================
# SINGLETON INSTANCE
# ============================================================================

_mcp_validator_instance: Optional[MCPValidatorService] = None

async def get_mcp_validator() -> MCPValidatorService:
    """Get or create MCP validator singleton"""
    global _mcp_validator_instance
    if _mcp_validator_instance is None:
        _mcp_validator_instance = MCPValidatorService()
    return _mcp_validator_instance
