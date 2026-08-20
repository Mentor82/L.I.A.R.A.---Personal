"""
AI Validator - Extended Language Support Module
Adds support for C, C++, Go, Rust, Ruby, PHP, Java, SQL, HTML/CSS, and more
"""

import subprocess
import tempfile
import os
import json
import logging
from typing import Dict, List, Any

logger = logging.getLogger(__name__)

# ============================================================================
# C/C++ VALIDATION
# ============================================================================

def validate_c(filepath, strict=False):
    """Validate C code"""
    results = {
        "language": "c",
        "file": filepath,
        "status": "ok",
        "errors": [],
        "warnings": []
    }
    
    # Compile check with gcc
    try:
        output = subprocess.run(
            ['gcc', '-fsyntax-only', '-Wall', '-Wextra', filepath],
            capture_output=True, timeout=10
        )
        
        if output.returncode != 0:
            results["status"] = "error"
            stderr = output.stderr.decode()
            # Parse gcc errors
            for line in stderr.split('\n'):
                if line.strip():
                    results["errors"].append({
                        "tool": "gcc",
                        "message": line,
                        "severity": "error"
                    })
            logger.error(f"❌ C compilation error: {filepath}")
        else:
            logger.info(f"✅ C syntax OK: {filepath}")
    except Exception as e:
        results["status"] = "error"
        results["errors"].append({
            "message": f"Compilation error: {str(e)}",
            "severity": "error"
        })
    
    return results

def validate_cpp(filepath, strict=False):
    """Validate C++ code"""
    results = {
        "language": "cpp",
        "file": filepath,
        "status": "ok",
        "errors": [],
        "warnings": []
    }
    
    # Compile check with g++
    try:
        output = subprocess.run(
            ['g++', '-fsyntax-only', '-Wall', '-Wextra', filepath],
            capture_output=True, timeout=10
        )
        
        if output.returncode != 0:
            results["status"] = "error"
            stderr = output.stderr.decode()
            for line in stderr.split('\n'):
                if line.strip():
                    results["errors"].append({
                        "tool": "g++",
                        "message": line,
                        "severity": "error"
                    })
            logger.error(f"❌ C++ compilation error: {filepath}")
        else:
            logger.info(f"✅ C++ syntax OK: {filepath}")
    except Exception as e:
        results["status"] = "error"
        results["errors"].append({"message": str(e), "severity": "error"})
    
    return results

# ============================================================================
# GO VALIDATION
# ============================================================================

def validate_go(filepath, strict=False):
    """Validate Go code"""
    results = {
        "language": "go",
        "file": filepath,
        "status": "ok",
        "errors": [],
        "warnings": []
    }
    
    # Go fmt check
    try:
        output = subprocess.run(
            ['go', 'fmt', '-l', filepath],
            capture_output=True, timeout=10
        )
        
        if output.stdout:
            results["warnings"].append({
                "tool": "go fmt",
                "message": "Code formatting not compliant",
                "severity": "warning"
            })
    except Exception as e:
        logger.debug(f"Go fmt skipped: {e}")
    
    # Go vet check
    try:
        output = subprocess.run(
            ['go', 'vet', filepath],
            capture_output=True, timeout=10
        )
        
        if output.returncode != 0:
            results["status"] = "error"
            results["errors"].append({
                "tool": "go vet",
                "message": output.stderr.decode(),
                "severity": "error"
            })
    except Exception as e:
        logger.debug(f"Go vet skipped: {e}")
    
    return results

# ============================================================================
# RUST VALIDATION
# ============================================================================

def validate_rust(filepath, strict=False):
    """Validate Rust code"""
    results = {
        "language": "rust",
        "file": filepath,
        "status": "ok",
        "errors": [],
        "warnings": []
    }
    
    # rustc check
    try:
        output = subprocess.run(
            ['rustc', '--crate-type', 'lib', '--edition', '2021', filepath],
            capture_output=True, timeout=10
        )
        
        if output.returncode != 0:
            results["status"] = "error"
            stderr = output.stderr.decode()
            results["errors"].append({
                "tool": "rustc",
                "message": stderr,
                "severity": "error"
            })
            logger.error(f"❌ Rust compilation error: {filepath}")
        else:
            logger.info(f"✅ Rust syntax OK: {filepath}")
    except Exception as e:
        results["status"] = "error"
        results["errors"].append({
            "message": f"Rust compiler error: {str(e)}",
            "severity": "error"
        })
    
    return results

# ============================================================================
# PHP VALIDATION
# ============================================================================

def validate_php(filepath, strict=False):
    """Validate PHP code"""
    results = {
        "language": "php",
        "file": filepath,
        "status": "ok",
        "errors": [],
        "warnings": []
    }
    
    # PHP syntax check
    try:
        output = subprocess.run(
            ['php', '-l', filepath],
            capture_output=True, timeout=10
        )
        
        if output.returncode != 0:
            results["status"] = "error"
            stdout = output.stdout.decode()
            results["errors"].append({
                "tool": "php",
                "message": stdout,
                "severity": "error"
            })
            logger.error(f"❌ PHP syntax error: {filepath}")
        else:
            logger.info(f"✅ PHP syntax OK: {filepath}")
    except Exception as e:
        results["status"] = "error"
        results["errors"].append({"message": str(e), "severity": "error"})
    
    return results

# ============================================================================
# RUBY VALIDATION
# ============================================================================

def validate_ruby(filepath, strict=False):
    """Validate Ruby code"""
    results = {
        "language": "ruby",
        "file": filepath,
        "status": "ok",
        "errors": [],
        "warnings": []
    }
    
    # Ruby syntax check
    try:
        output = subprocess.run(
            ['ruby', '-c', filepath],
            capture_output=True, timeout=10
        )
        
        if output.returncode != 0:
            results["status"] = "error"
            stderr = output.stderr.decode()
            results["errors"].append({
                "tool": "ruby",
                "message": stderr,
                "severity": "error"
            })
            logger.error(f"❌ Ruby syntax error: {filepath}")
        else:
            logger.info(f"✅ Ruby syntax OK: {filepath}")
    except Exception as e:
        results["status"] = "error"
        results["errors"].append({"message": str(e), "severity": "error"})
    
    return results

# ============================================================================
# SQL VALIDATION
# ============================================================================

def validate_sql(filepath, strict=False):
    """Validate SQL code"""
    results = {
        "language": "sql",
        "file": filepath,
        "status": "ok",
        "errors": [],
        "warnings": []
    }
    
    try:
        with open(filepath, 'r') as f:
            sql_code = f.read().strip()
        
        # Basic SQL syntax check (sqlparse if available)
        try:
            import sqlparse
            parsed = sqlparse.parse(sql_code)
            
            if not parsed or not sql_code:
                results["status"] = "error"
                results["errors"].append({
                    "message": "Invalid SQL syntax",
                    "severity": "error"
                })
            else:
                logger.info(f"✅ SQL syntax OK: {filepath}")
        except ImportError:
            # Basic validation without sqlparse
            required_keywords = ['SELECT', 'INSERT', 'UPDATE', 'DELETE', 'CREATE']
            if not any(kw in sql_code.upper() for kw in required_keywords):
                results["warnings"].append({
                    "message": "No common SQL keywords found",
                    "severity": "warning"
                })
            logger.info(f"✅ SQL basic check OK: {filepath}")
    except Exception as e:
        results["status"] = "error"
        results["errors"].append({"message": str(e), "severity": "error"})
    
    return results

# ============================================================================
# HTML/CSS VALIDATION
# ============================================================================

def validate_html(filepath, strict=False):
    """Validate HTML code"""
    results = {
        "language": "html",
        "file": filepath,
        "status": "ok",
        "errors": [],
        "warnings": []
    }
    
    try:
        # HTMLLint if available
        output = subprocess.run(
            ['htmlhint', filepath],
            capture_output=True, timeout=10
        )
        
        if output.returncode != 0 and output.stdout:
            warnings = output.stdout.decode()
            results["warnings"].append({
                "tool": "htmlhint",
                "message": warnings,
                "severity": "warning"
            })
    except:
        # Basic validation
        with open(filepath, 'r') as f:
            html = f.read()
        
        if html.count('<') != html.count('>'):
            results["status"] = "error"
            results["errors"].append({
                "message": "Mismatched HTML tags",
                "severity": "error"
            })
        
        logger.info(f"✅ HTML basic check OK: {filepath}")
    
    return results

def validate_css(filepath, strict=False):
    """Validate CSS code"""
    results = {
        "language": "css",
        "file": filepath,
        "status": "ok",
        "errors": [],
        "warnings": []
    }
    
    try:
        # CSSLint if available
        output = subprocess.run(
            ['csslint', filepath],
            capture_output=True, timeout=10
        )
        
        if output.returncode != 0 and output.stdout:
            warnings = output.stdout.decode()
            results["warnings"].append({
                "tool": "csslint",
                "message": warnings,
                "severity": "warning"
            })
    except:
        # Basic validation
        with open(filepath, 'r') as f:
            css = f.read()
        
        if css.count('{') != css.count('}'):
            results["status"] = "error"
            results["errors"].append({
                "message": "Mismatched CSS braces",
                "severity": "error"
            })
        
        logger.info(f"✅ CSS basic check OK: {filepath}")
    
    return results

# ============================================================================
# JAVA VALIDATION
# ============================================================================

def validate_java(filepath, strict=False):
    """Validate Java code"""
    results = {
        "language": "java",
        "file": filepath,
        "status": "ok",
        "errors": [],
        "warnings": []
    }
    
    try:
        # Javac syntax check
        output = subprocess.run(
            ['javac', '-d', '/tmp', filepath],
            capture_output=True, timeout=10
        )
        
        if output.returncode != 0:
            results["status"] = "error"
            stderr = output.stderr.decode()
            results["errors"].append({
                "tool": "javac",
                "message": stderr,
                "severity": "error"
            })
            logger.error(f"❌ Java compilation error: {filepath}")
        else:
            logger.info(f"✅ Java syntax OK: {filepath}")
    except Exception as e:
        results["status"] = "error"
        results["errors"].append({"message": str(e), "severity": "error"})
    
    return results

# ============================================================================
# TYPESCRIPT VALIDATION
# ============================================================================

def validate_typescript(filepath, strict=False):
    """Validate TypeScript code"""
    results = {
        "language": "typescript",
        "file": filepath,
        "status": "ok",
        "errors": [],
        "warnings": []
    }
    
    try:
        # tsc check
        output = subprocess.run(
            ['tsc', '--noEmit', filepath],
            capture_output=True, timeout=10
        )
        
        if output.returncode != 0:
            results["status"] = "error"
            stderr = output.stderr.decode()
            results["errors"].append({
                "tool": "tsc",
                "message": stderr,
                "severity": "error"
            })
    except:
        logger.debug("TypeScript compiler not available, falling back to ESLint")
        # Fallback to ESLint for JavaScript validation
        try:
            output = subprocess.run(
                ['eslint', filepath],
                capture_output=True, timeout=10
            )
            if output.returncode != 0 and output.stdout:
                warnings = json.loads(output.stdout.decode())
                results["warnings"].extend(warnings if isinstance(warnings, list) else [warnings])
        except:
            pass
    
    return results

# ============================================================================
# LANGUAGE MAPPING
# ============================================================================

LANGUAGE_VALIDATORS = {
    'c': validate_c,
    'cpp': validate_cpp,
    'c++': validate_cpp,
    'go': validate_go,
    'golang': validate_go,
    'rust': validate_rust,
    'rs': validate_rust,
    'php': validate_php,
    'ruby': validate_ruby,
    'rb': validate_ruby,
    'sql': validate_sql,
    'html': validate_html,
    'css': validate_css,
    'java': validate_java,
    'typescript': validate_typescript,
    'ts': validate_typescript,
}

def get_validator(language: str):
    """Get validator function for language"""
    return LANGUAGE_VALIDATORS.get(language.lower())

# ============================================================================
# FILE EXTENSION MAPPING
# ============================================================================

FILE_EXTENSIONS = {
    'c': '.c',
    'cpp': '.cpp',
    'c++': '.cpp',
    'go': '.go',
    'golang': '.go',
    'rust': '.rs',
    'rs': '.rs',
    'php': '.php',
    'ruby': '.rb',
    'rb': '.rb',
    'sql': '.sql',
    'html': '.html',
    'css': '.css',
    'java': '.java',
    'typescript': '.ts',
    'ts': '.ts',
}

def get_file_extension(language: str) -> str:
    """Get file extension for language"""
    return FILE_EXTENSIONS.get(language.lower(), '.txt')
