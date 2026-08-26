"""
Ollama Management API Router
Model download, deletion, and management operations
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks, Depends
from pydantic import BaseModel
from typing import Optional, Dict, List
import subprocess
import requests
import asyncio
import time
from datetime import datetime

from core.dependencies import require_admin
from api.models.base_models import User

router = APIRouter(prefix="/ollama", tags=["Ollama Management"])

# Track ongoing pull operations
pull_status: Dict[str, Dict] = {}


class ModelPullRequest(BaseModel):
    """Request to pull a new model"""
    model_name: str
    

class ModelDeleteRequest(BaseModel):
    """Request to delete a model"""
    model_name: str


@router.get("/available")
async def get_available_models():
    """
    Get list of popular models available for download from Ollama library
    
    Returns curated list of recommended models with descriptions
    """
    # Curated list of popular Ollama models
    available_models = [
        {
            "name": "llama3.2:1b",
            "size": "1.3 GB",
            "description": "Fastest Llama model, great for quick responses",
            "category": "general",
            "recommended": True
        },
        {
            "name": "llama3.2:3b",
            "size": "2.0 GB",
            "description": "Balanced Llama model for most tasks",
            "category": "general",
            "recommended": True
        },
        {
            "name": "phi3.5:3.8b",
            "size": "2.2 GB",
            "description": "Microsoft's compact coding model",
            "category": "coding",
            "recommended": True
        },
        {
            "name": "qwen2.5:7b",
            "size": "4.7 GB",
            "description": "Alibaba's multilingual powerhouse",
            "category": "multilingual",
            "recommended": True
        },
        {
            "name": "deepseek-r1:7b",
            "size": "4.7 GB",
            "description": "Advanced reasoning and logic",
            "category": "reasoning",
            "recommended": True
        },
        {
            "name": "mistral:7b",
            "size": "4.1 GB",
            "description": "Fast and efficient general model",
            "category": "general",
            "recommended": False
        },
        {
            "name": "gemma2:9b",
            "size": "5.4 GB",
            "description": "Google's powerful chat model",
            "category": "chat",
            "recommended": False
        },
        {
            "name": "llama3.1:8b",
            "size": "4.7 GB",
            "description": "Previous Llama generation",
            "category": "general",
            "recommended": False
        },
        {
            "name": "mixtral:8x7b",
            "size": "26.4 GB",
            "description": "Mixture of Experts, very capable",
            "category": "advanced",
            "recommended": False
        }
    ]
    
    return {
        "total": len(available_models),
        "models": available_models,
        "source": "ollama-library"
    }


@router.post("/pull")
async def pull_model(
    request: ModelPullRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(require_admin),
):
    """
    Start pulling (downloading) a model from Ollama library

    This is a background operation - use /ollama/pull/status/{model_name} to check progress

    Admin-only (issue #16): downloads real disk/network resources.
    """
    model_name = request.model_name
    
    if model_name in pull_status and pull_status[model_name].get("status") == "in_progress":
        raise HTTPException(status_code=409, detail="Model is already being downloaded")
    
    # Initialize status
    pull_status[model_name] = {
        "status": "in_progress",
        "progress": 0,
        "message": "Starting download...",
        "started_at": datetime.utcnow().isoformat()
    }
    
    # Start pull in background
    background_tasks.add_task(execute_pull, model_name)
    
    return {
        "message": f"Started pulling {model_name}",
        "status": "in_progress",
        "check_status_at": f"/ollama/pull/status/{model_name}"
    }


async def execute_pull(model_name: str):
    """Execute the actual model pull operation"""
    try:
        # Use ollama pull command
        process = subprocess.Popen(
            ['ollama', 'pull', model_name],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1
        )
        
        # Monitor output for progress
        for line in process.stdout:
            line = line.strip()
            pull_status[model_name]["message"] = line
            
            # Try to extract percentage if present
            if "%" in line:
                try:
                    percent_str = line.split("%")[0].split()[-1]
                    pull_status[model_name]["progress"] = int(float(percent_str))
                except:
                    pass
        
        process.wait()
        
        if process.returncode == 0:
            pull_status[model_name] = {
                "status": "completed",
                "progress": 100,
                "message": f"Successfully pulled {model_name}",
                "completed_at": datetime.utcnow().isoformat()
            }
        else:
            pull_status[model_name] = {
                "status": "failed",
                "progress": 0,
                "message": "Download failed",
                "error": "Process exited with error"
            }
            
    except Exception as e:
        pull_status[model_name] = {
            "status": "failed",
            "progress": 0,
            "message": str(e),
            "error": str(e)
        }


@router.get("/pull/status/{model_name}")
async def get_pull_status(model_name: str, current_user: User = Depends(require_admin)):
    """
    Get the current status of a model pull operation

    Returns:
        - status: "in_progress", "completed", or "failed"
        - progress: 0-100
        - message: Current status message

    Admin-only (issue #16): status of an admin-only pull operation.
    """
    if model_name not in pull_status:
        raise HTTPException(status_code=404, detail="No pull operation found for this model")
    
    return pull_status[model_name]


@router.delete("/model/{model_name}")
async def delete_model(model_name: str, current_user: User = Depends(require_admin)):
    """
    Delete a downloaded model

    This frees up disk space

    Admin-only (issue #16): permanently deletes an installed model.
    """
    try:
        result = subprocess.run(
            ['ollama', 'rm', model_name],
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode == 0:
            return {
                "success": True,
                "message": f"Successfully deleted {model_name}",
                "model": model_name
            }
        else:
            raise HTTPException(
                status_code=400,
                detail=f"Failed to delete model: {result.stderr}"
            )
            
    except subprocess.TimeoutExpired:
        raise HTTPException(status_code=504, detail="Delete operation timed out")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/library/search")
async def search_library(query: str):
    """
    Search Ollama library for models
    
    Returns models matching the search query
    """
    # Get all available models and filter
    available = await get_available_models()
    
    query_lower = query.lower()
    filtered = [
        m for m in available["models"]
        if query_lower in m["name"].lower() or query_lower in m["description"].lower()
    ]
    
    return {
        "query": query,
        "results": len(filtered),
        "models": filtered
    }


@router.get("/storage")
async def get_storage_info(current_user: User = Depends(require_admin)):
    """
    Get storage information for Ollama models

    Returns disk usage and model sizes

    Admin-only (issue #16): reveals installed-model inventory and disk usage.
    """
    try:
        # Get list of installed models with sizes
        result = subprocess.run(
            ['ollama', 'list'],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if result.returncode != 0:
            return {"error": "Failed to get model list"}
        
        lines = result.stdout.strip().split('\n')[1:]  # Skip header
        total_size_gb = 0.0
        models = []
        
        for line in lines:
            if line.strip():
                parts = line.split()
                if len(parts) >= 4:  # NAME ID SIZE MODIFIED
                    name = parts[0]
                    size_str = parts[2]  # SIZE is 3rd column
                    unit = parts[3] if len(parts) > 3 else 'GB'  # Unit might be separate
                    
                    # Combine size and unit if separated
                    if unit in ['GB', 'MB', 'KB']:
                        full_size = f"{size_str} {unit}"
                    else:
                        full_size = size_str
                        unit = 'GB' if 'GB' in size_str else 'MB'
                    
                    # Parse size to GB
                    try:
                        size_value = float(size_str)
                        if unit == 'MB':
                            size_gb = size_value / 1024
                        elif unit == 'KB':
                            size_gb = size_value / (1024 * 1024)
                        else:  # GB
                            size_gb = size_value
                        
                        total_size_gb += size_gb
                        models.append({
                            "name": name,
                            "size": full_size,
                            "size_gb": round(size_gb, 2)
                        })
                    except ValueError:
                        pass
        
        return {
            "total_models": len(models),
            "total_size_gb": round(total_size_gb, 2),
            "models": sorted(models, key=lambda x: x['size_gb'], reverse=True)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
