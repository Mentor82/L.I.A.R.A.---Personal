"""
MCP Validation Router - Code validation and review via MCP (Ollama)
Provides semantic analysis, code review, and AI-powered validation
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
import logging

from services.ai_validator_mcp_service import get_mcp_validator, MCP_CODE_MODEL
from core.dependencies import require_active_user, require_admin
from api.models.base_models import User

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/validate-mcp", tags=["validation-mcp"])

# ============================================================================
# REQUEST/RESPONSE MODELS
# ============================================================================

class CodeRequest(BaseModel):
    """Code validation request"""
    code: str
    language: str
    model: Optional[str] = MCP_CODE_MODEL

class CodeReviewRequest(BaseModel):
    """Code review request"""
    code: str
    language: str
    focus: Optional[str] = "general"  # general, security, performance, readability
    model: Optional[str] = MCP_CODE_MODEL

class FixSuggestionsRequest(BaseModel):
    """Fix suggestions request"""
    code: str
    language: str
    issues: List[str]
    model: Optional[str] = MCP_CODE_MODEL

class TextGenerationRequest(BaseModel):
    """Text generation request"""
    model: str
    prompt: str
    temperature: Optional[float] = 0.7
    top_p: Optional[float] = 0.9
    num_predict: Optional[int] = 256

# ============================================================================
# ENDPOINTS
# ============================================================================

@router.get("/health")
async def health_check(current_user: User = Depends(require_admin)):
    """Check MCP server health

    Admin-only (issue #16): response leaks the internal MCP backend endpoint URL.
    """
    try:
        mcp = await get_mcp_validator()
        is_healthy = await mcp.health_check()
        
        return {
            "status": "healthy" if is_healthy else "unhealthy",
            "service": "MCP-Validator",
            "endpoint": "http://192.168.178.150:3333",
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Health check failed: {str(e)}")

@router.get("/models")
async def list_models(current_user: User = Depends(require_active_user)):
    """List available Ollama models"""
    try:
        mcp = await get_mcp_validator()
        models = await mcp.list_models()
        
        return {
            "status": "ok",
            "count": len(models),
            "models": [{"name": m.name, "size": m.size} for m in models],
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list models: {str(e)}")

@router.get("/tools")
async def list_tools(current_user: User = Depends(require_admin)):
    """List available MCP tools

    Admin-only (issue #16): reveals internal MCP tool/endpoint topology.
    """
    try:
        mcp = await get_mcp_validator()
        tools = await mcp.list_tools()
        
        return {
            "status": "ok",
            "count": len(tools),
            "tools": [{"name": t.name, "description": t.description, "method": t.method, "path": t.path} for t in tools],
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list tools: {str(e)}")

@router.post("/generate")
async def generate_text(request: TextGenerationRequest, current_user: User = Depends(require_active_user)):
    """Generate text using Ollama model via MCP"""
    try:
        mcp = await get_mcp_validator()
        result = await mcp.generate_text(
            model=request.model,
            prompt=request.prompt,
            temperature=request.temperature,
            top_p=request.top_p,
            num_predict=request.num_predict
        )
        
        if not result:
            raise HTTPException(status_code=500, detail="Text generation failed")
        
        return {
            "status": "ok",
            "model": result.model,
            "response": result.response,
            "done": result.done,
            "total_duration_ms": result.total_duration / 1_000_000 if result.total_duration else None,
            "timestamp": datetime.utcnow().isoformat()
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Generation failed: {str(e)}")

@router.post("/analyze")
async def analyze_code(request: CodeRequest, current_user: User = Depends(require_active_user)):
    """Analyze code for errors and issues using AI"""
    try:
        mcp = await get_mcp_validator()
        result = await mcp.validate_code_with_model(
            code=request.code,
            language=request.language,
            model=request.model
        )
        
        return {
            **result,
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Code analysis failed: {str(e)}")

@router.post("/review")
async def review_code(request: CodeReviewRequest, current_user: User = Depends(require_active_user)):
    """Perform semantic code review"""
    try:
        mcp = await get_mcp_validator()
        result = await mcp.code_review(
            code=request.code,
            language=request.language,
            focus=request.focus
        )
        
        return {
            **result,
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Code review failed: {str(e)}")

@router.post("/suggest-fixes")
async def suggest_fixes(request: FixSuggestionsRequest, current_user: User = Depends(require_active_user)):
    """Generate fix suggestions for code issues"""
    try:
        mcp = await get_mcp_validator()
        result = await mcp.suggest_fixes(
            code=request.code,
            language=request.language,
            issues=request.issues
        )
        
        return {
            **result,
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Fix suggestion failed: {str(e)}")

@router.post("/python-analyze")
async def analyze_python(request: CodeRequest, current_user: User = Depends(require_active_user)):
    """Analyze Python code"""
    request.language = "python"
    return await analyze_code(request, current_user)

@router.post("/javascript-analyze")
async def analyze_javascript(request: CodeRequest, current_user: User = Depends(require_active_user)):
    """Analyze JavaScript code"""
    request.language = "javascript"
    return await analyze_code(request, current_user)

@router.post("/typescript-analyze")
async def analyze_typescript(request: CodeRequest, current_user: User = Depends(require_active_user)):
    """Analyze TypeScript code"""
    request.language = "typescript"
    return await analyze_code(request, current_user)

@router.post("/cpp-analyze")
async def analyze_cpp(request: CodeRequest, current_user: User = Depends(require_active_user)):
    """Analyze C++ code"""
    request.language = "c++"
    return await analyze_code(request, current_user)

@router.post("/go-analyze")
async def analyze_go(request: CodeRequest, current_user: User = Depends(require_active_user)):
    """Analyze Go code"""
    request.language = "go"
    return await analyze_code(request, current_user)

@router.post("/rust-analyze")
async def analyze_rust(request: CodeRequest, current_user: User = Depends(require_active_user)):
    """Analyze Rust code"""
    request.language = "rust"
    return await analyze_code(request, current_user)
