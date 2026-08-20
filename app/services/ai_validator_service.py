"""
AI Validator Service - Integration with remote AI-Validator
Provides code validation, syntax checking, and linting via REST API
Supports: Python, JavaScript, TypeScript, Bash, JSON, YAML, C, C++, Go, Rust, PHP, Ruby, SQL, HTML, CSS, Java
"""

import httpx
import logging
from typing import Optional, Dict, List, Any
from pydantic import BaseModel
from datetime import datetime
import asyncio

logger = logging.getLogger(__name__)

# AI-Validator Service Configuration
VALIDATOR_HOST = "192.168.178.150"
VALIDATOR_PORT = 5000
VALIDATOR_URL = f"http://{VALIDATOR_HOST}:{VALIDATOR_PORT}"
VALIDATOR_TIMEOUT = 30.0

# Supported Languages
SUPPORTED_LANGUAGES = [
    "python", "javascript", "typescript", "bash", "shell", "sh",
    "json", "yaml", "yml", "c", "cpp", "c++", "go", "golang",
    "rust", "rs", "php", "ruby", "rb", "sql", "html", "css", "java"
]

# ============================================================================
# RESPONSE MODELS
# ============================================================================

class ValidationError(BaseModel):
    """Validation error/warning"""
    tool: Optional[str] = None
    message: str
    line: Optional[int] = None
    column: Optional[int] = None
    severity: str = "error"  # error, warning, info

class ValidationResult(BaseModel):
    """Code validation result"""
    language: str
    status: str  # ok, warning, error
    timestamp: datetime
    errors: List[ValidationError] = []
    warnings: List[ValidationError] = []
    file: Optional[str] = None
    latency_ms: Optional[float] = None

# ============================================================================
# AI VALIDATOR SERVICE
# ============================================================================

class AIValidatorService:
    """Service for remote AI code validation"""
    
    def __init__(self, host: str = VALIDATOR_HOST, port: int = VALIDATOR_PORT):
        self.host = host
        self.port = port
        self.url = f"http://{host}:{port}"
        self.client = None
        self._last_health_check = None
        self._is_healthy = False
    
    async def initialize(self):
        """Initialize async HTTP client"""
        self.client = httpx.AsyncClient(timeout=VALIDATOR_TIMEOUT)
        await self.health_check()
    
    async def shutdown(self):
        """Shutdown async HTTP client"""
        if self.client:
            await self.client.aclose()
    
    async def health_check(self) -> bool:
        """Check if AI-Validator is available"""
        try:
            if not self.client:
                self.client = httpx.AsyncClient(timeout=VALIDATOR_TIMEOUT)
            
            response = await self.client.get(
                f"{self.url}/api/summary",
                timeout=5.0
            )
            self._is_healthy = response.status_code in [200, 400, 500]
            self._last_health_check = datetime.now()
            logger.info(f"AI-Validator health check: {'✅ OK' if self._is_healthy else '❌ DOWN'}")
            return self._is_healthy
        except Exception as e:
            logger.warning(f"AI-Validator health check failed: {e}")
            self._is_healthy = False
            return False
    
    async def validate_code(
        self,
        code: str,
        language: str = "python",
        strict: bool = False
    ) -> ValidationResult:
        """Validate code snippet
        
        Args:
            code: Code to validate
            language: Programming language (python, javascript, bash, json, yaml)
            strict: Strict validation mode
        
        Returns:
            ValidationResult with errors and warnings
        """
        if not self._is_healthy:
            await self.health_check()
        
        if not self._is_healthy:
            return ValidationResult(
                language=language,
                status="error",
                timestamp=datetime.now(),
                errors=[ValidationError(
                    message=f"AI-Validator service unavailable at {self.url}",
                    severity="error"
                )]
            )
        
        try:
            start_time = datetime.now()
            
            response = await self.client.post(
                f"{self.url}/api/validate",
                json={
                    "code": code,
                    "language": language,
                    "strict": strict
                }
            )
            
            latency_ms = (datetime.now() - start_time).total_seconds() * 1000
            
            if response.status_code == 200:
                data = response.json()
                
                # Parse errors and warnings
                errors = [
                    ValidationError(**err) if isinstance(err, dict) else ValidationError(message=str(err))
                    for err in data.get("errors", [])
                ]
                warnings = [
                    ValidationError(**w) if isinstance(w, dict) else ValidationError(message=str(w), severity="warning")
                    for w in data.get("warnings", [])
                ]
                
                return ValidationResult(
                    language=language,
                    status=data.get("status", "ok"),
                    timestamp=datetime.now(),
                    errors=errors,
                    warnings=warnings,
                    file=data.get("file"),
                    latency_ms=latency_ms
                )
            else:
                logger.error(f"Validation failed: {response.text}")
                return ValidationResult(
                    language=language,
                    status="error",
                    timestamp=datetime.now(),
                    errors=[ValidationError(
                        message=f"Validation service error: {response.status_code}",
                        severity="error"
                    )],
                    latency_ms=latency_ms
                )
        
        except Exception as e:
            logger.error(f"Validation request failed: {e}")
            return ValidationResult(
                language=language,
                status="error",
                timestamp=datetime.now(),
                errors=[ValidationError(
                    message=f"Validation request error: {str(e)}",
                    severity="error"
                )]
            )
    
    # ========================================================================
    # LANGUAGE-SPECIFIC METHODS
    # ========================================================================
    
    async def validate_python(self, code: str, strict: bool = False) -> ValidationResult:
        """Validate Python code"""
        return await self.validate_code(code, "python", strict)
    
    async def validate_javascript(self, code: str, strict: bool = False) -> ValidationResult:
        """Validate JavaScript/TypeScript code"""
        return await self.validate_code(code, "javascript", strict)
    
    async def validate_typescript(self, code: str, strict: bool = False) -> ValidationResult:
        """Validate TypeScript code"""
        return await self.validate_code(code, "typescript", strict)
    
    async def validate_bash(self, code: str, strict: bool = False) -> ValidationResult:
        """Validate Bash/Shell script"""
        return await self.validate_code(code, "bash", strict)
    
    async def validate_json(self, code: str) -> ValidationResult:
        """Validate JSON"""
        return await self.validate_code(code, "json")
    
    async def validate_yaml(self, code: str) -> ValidationResult:
        """Validate YAML"""
        return await self.validate_code(code, "yaml")
    
    async def validate_c(self, code: str, strict: bool = False) -> ValidationResult:
        """Validate C code"""
        return await self.validate_code(code, "c", strict)
    
    async def validate_cpp(self, code: str, strict: bool = False) -> ValidationResult:
        """Validate C++ code"""
        return await self.validate_code(code, "cpp", strict)
    
    async def validate_go(self, code: str, strict: bool = False) -> ValidationResult:
        """Validate Go code"""
        return await self.validate_code(code, "go", strict)
    
    async def validate_rust(self, code: str, strict: bool = False) -> ValidationResult:
        """Validate Rust code"""
        return await self.validate_code(code, "rust", strict)
    
    async def validate_php(self, code: str, strict: bool = False) -> ValidationResult:
        """Validate PHP code"""
        return await self.validate_code(code, "php", strict)
    
    async def validate_ruby(self, code: str, strict: bool = False) -> ValidationResult:
        """Validate Ruby code"""
        return await self.validate_code(code, "ruby", strict)
    
    async def validate_sql(self, code: str) -> ValidationResult:
        """Validate SQL code"""
        return await self.validate_code(code, "sql")
    
    async def validate_html(self, code: str) -> ValidationResult:
        """Validate HTML code"""
        return await self.validate_code(code, "html")
    
    async def validate_css(self, code: str) -> ValidationResult:
        """Validate CSS code"""
        return await self.validate_code(code, "css")
    
    async def validate_java(self, code: str, strict: bool = False) -> ValidationResult:
        """Validate Java code"""
        return await self.validate_code(code, "java", strict)
    
    async def validate_yaml(self, code: str) -> ValidationResult:
        """Validate YAML"""
        return await self.validate_code(code, "yaml")
    
    @property
    def is_available(self) -> bool:
        """Check if validator is available"""
        return self._is_healthy

# ============================================================================
# SINGLETON INSTANCE
# ============================================================================

_validator_service: Optional[AIValidatorService] = None

async def get_ai_validator_service() -> AIValidatorService:
    """Get or create AI Validator service instance"""
    global _validator_service
    
    if _validator_service is None:
        _validator_service = AIValidatorService()
        await _validator_service.initialize()
    
    return _validator_service
