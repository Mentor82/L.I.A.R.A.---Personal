"""
AI Validation Router - Multi-Backend with Fallback
Primary: liara-core (192.168.178.60:11434)
Fallback: liara (192.168.178.50:11434)
Syntax: ai-validator (192.168.178.150:5000)
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from datetime import datetime

from services.multi_backend_validator import get_validator

router = APIRouter(prefix="/validate", tags=["validation"])

# ============================================================================
# REQUEST MODELS
# ============================================================================

class ValidationRequest(BaseModel):
    """Code validation request"""
    code: str
    language: str = "python"
    strict: bool = False

class TextGenerationRequest(BaseModel):
    """Text generation request"""
    prompt: str
    model: str = "mistral:7b"

# ============================================================================
# ENDPOINTS
# ============================================================================

# ============================================================================
# ENDPOINTS
# ============================================================================

@router.post("/code")
async def validate_code(request: ValidationRequest):
    """Validate code snippet
    
    Supports: python, javascript, bash, json, yaml, c, cpp, go, rust, php, ruby, sql, html, css, java, typescript
    Uses liara-core as primary, liara as fallback, ai-validator for syntax checking
    """
    validator = await get_validator()
    
    result = await validator.validate_syntax(
        code=request.code,
        language=request.language
    )
    
    return result

@router.post("/python")
async def validate_python(request: ValidationRequest):
    """Validate Python code"""
    validator = await get_validator()
    return await validator.validate_syntax(code=request.code, language="python")

@router.post("/javascript")
async def validate_javascript(request: ValidationRequest):
    """Validate JavaScript/TypeScript code"""
    validator = await get_validator()
    return await validator.validate_syntax(code=request.code, language="javascript")

@router.post("/bash")
async def validate_bash(request: ValidationRequest):
    """Validate Bash/Shell script"""
    validator = await get_validator()
    return await validator.validate_syntax(code=request.code, language="bash")

@router.post("/json")
async def validate_json(request: ValidationRequest):
    """Validate JSON"""
    validator = await get_validator()
    return await validator.validate_syntax(code=request.code, language="json")

@router.post("/yaml")
async def validate_yaml(request: ValidationRequest):
    """Validate YAML"""
    validator = await get_validator()
    return await validator.validate_syntax(code=request.code, language="yaml")

# ============================================================================
# EXTENDED LANGUAGE SUPPORT
# ============================================================================

@router.post("/typescript")
async def validate_typescript(request: ValidationRequest):
    """Validate TypeScript code"""
    validator = await get_validator()
    return await validator.validate_syntax(code=request.code, language="typescript")

@router.post("/c")
async def validate_c(request: ValidationRequest):
    """Validate C code"""
    validator = await get_validator()
    return await validator.validate_syntax(code=request.code, language="c")

@router.post("/cpp")
async def validate_cpp(request: ValidationRequest):
    """Validate C++ code"""
    validator = await get_validator()
    return await validator.validate_syntax(code=request.code, language="cpp")

@router.post("/go")
async def validate_go(request: ValidationRequest):
    """Validate Go code"""
    validator = await get_validator()
    return await validator.validate_syntax(code=request.code, language="go")

@router.post("/rust")
async def validate_rust(request: ValidationRequest):
    """Validate Rust code"""
    validator = await get_validator()
    return await validator.validate_syntax(code=request.code, language="rust")

@router.post("/php")
async def validate_php(request: ValidationRequest):
    """Validate PHP code"""
    validator = await get_validator()
    return await validator.validate_syntax(code=request.code, language="php")

@router.post("/ruby")
async def validate_ruby(request: ValidationRequest):
    """Validate Ruby code"""
    validator = await get_validator()
    return await validator.validate_syntax(code=request.code, language="ruby")

@router.post("/sql")
async def validate_sql(request: ValidationRequest):
    """Validate SQL code"""
    validator = await get_validator()
    return await validator.validate_syntax(code=request.code, language="sql")

@router.post("/html")
async def validate_html(request: ValidationRequest):
    """Validate HTML code"""
    validator = await get_validator()
    return await validator.validate_syntax(code=request.code, language="html")

@router.post("/css")
async def validate_css(request: ValidationRequest):
    """Validate CSS code"""
    validator = await get_validator()
    return await validator.validate_syntax(code=request.code, language="css")

@router.post("/java")
async def validate_java(request: ValidationRequest):
    """Validate Java code"""
    validator = await get_validator()
    return await validator.validate_syntax(code=request.code, language="java")

# ============================================================================
# MULTI-BACKEND ENDPOINTS
# ============================================================================

@router.get("/health")
async def validation_health():
    """Check all validation backends health"""
    validator = await get_validator()
    health = await validator.health_check()
    
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        **health
    }

@router.get("/models")
async def get_available_models():
    """Get available models from active backend"""
    validator = await get_validator()
    models = await validator.get_models()
    
    return {
        "models": models,
        "count": len(models),
        "timestamp": datetime.now().isoformat()
    }

@router.post("/generate")
async def generate_text(request: TextGenerationRequest):
    """Generate text using active backend (liara-core or liara)"""
    validator = await get_validator()
    
    result = await validator.generate_text(
        prompt=request.prompt,
        model=request.model
    )
    
    return {
        **result,
        "timestamp": datetime.now().isoformat()
    }
