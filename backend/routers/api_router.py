"""
API Router for ZealX Backend
Provides endpoints for Flutter-FastAPI connection and handles all ZealX API requests
"""

from fastapi import APIRouter, Depends, HTTPException, Request, BackgroundTasks, Response
from fastapi.responses import JSONResponse, FileResponse, StreamingResponse
from typing import Dict, Any, List, Optional
import time
import asyncio
import json
import uuid
from datetime import datetime
import logging
import io
import os
import sys
sys.path.append(os.path.abspath("/Users/momo/Desktop/x"))

from pydantic import BaseModel

from backend.models.api import (
    ZealXRequest, ZealXResponse, BrainXRequest, BrainXResponse, 
    AutoXRequest, AutoXResponse, AutoXTask, ErrorDetail, 
    SystemStatus, APIAccountStatus, FireLayersConfig, ADXStatus
)
from backend.core.firelayers import fire_layers
from backend.core.logging_manager import logging_manager
from backend.core.config import Settings
from storagex.storage_manager import generate_file_content, get_adx_optimized_file_operations, get_client_storage_instructions
from storagex.database import get_database_schema, generate_client_db_init_script, export_database_data
from storagex.storagex import StorageX

# Configure logger
logger = logging.getLogger("zealx.api_router")

# Initialize StorageX
storage = StorageX()

# Create router
router = APIRouter(prefix="/api", tags=["ZealX API"])

# Dependency to get settings
async def get_settings():
    return Settings()

# Dependency to get API manager from request state
async def get_api_manager(request: Request):
    if not hasattr(request.state, "api_manager"):
        raise HTTPException(
            status_code=500,
            detail="API Account Manager not initialized"
        )
    return request.state.api_manager

@router.get("/health")
async def health_check():
    """Health check endpoint for the ZealX API"""
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}

@router.post("/zealx", response_model=ZealXResponse)
async def zealx_endpoint(
    request: ZealXRequest,
    background_tasks: BackgroundTasks,
    settings: Settings = Depends(get_settings),
    api_manager = Depends(get_api_manager)
):
    """
    Main ZealX API endpoint
    Routes requests to appropriate handler based on action type
    """
    start_time = time.time()
    
    try:
        # Route to appropriate handler based on action type
        if request.action == "brainx":
            # Handle BrainX request
            brainx_request = BrainXRequest(
                messages=request.data if isinstance(request.data, list) else [],
                stream=False
            )
            response = await handle_brainx_request(brainx_request, api_manager)
            
            # Create ZealX response
            return ZealXResponse(
                response=response.content,
                meta={
                    "ai_engine": "BrainX",
                    "model": response.model,
                    "processing_time": response.processing_time,
                    "usage": response.usage,
                    "fire_layers_stats": response.fire_layers_stats
                },
                request_id=request.request_id,
                success=True
            )
            
        elif request.action == "autox":
            # Handle AutoX request
            if not isinstance(request.data, dict):
                raise HTTPException(
                    status_code=400,
                    detail="AutoX requests require a dictionary in the data field"
                )
                
            autox_request = AutoXRequest(
                app_id=request.data.get("app_id", ""),
                trigger_type=request.data.get("trigger_type", ""),
                trigger_data=request.data.get("trigger_data", {})
            )
            
            response = await handle_autox_request(
                autox_request, 
                background_tasks,
                user_id=request.user_id
            )
            
            # Create ZealX response
            return ZealXResponse(
                response={"task_id": response.task_id, "status": response.status},
                meta={
                    "ai_engine": "AutoX",
                    "processing_time": f"{int((time.time() - start_time) * 1000)}ms"
                },
                request_id=request.request_id,
                success=True
            )
            
        elif request.action == "system":
            # Handle system request
            if not isinstance(request.data, dict):
                raise HTTPException(
                    status_code=400,
                    detail="System requests require a dictionary in the data field"
                )
                
            system_action = request.data.get("system_action", "")
            
            if system_action == "status":
                status = await get_system_status()
                return ZealXResponse(
                    response=status.dict(),
                    meta={
                        "processing_time": f"{int((time.time() - start_time) * 1000)}ms"
                    },
                    request_id=request.request_id,
                    success=True
                )
            elif system_action == "api_status":
                api_status = await api_manager.get_all_accounts_status()
                return ZealXResponse(
                    response=api_status.dict(),
                    meta={
                        "processing_time": f"{int((time.time() - start_time) * 1000)}ms"
                    },
                    request_id=request.request_id,
                    success=True
                )
            else:
                raise HTTPException(
                    status_code=400,
                    detail=f"Unknown system action: {system_action}"
                )
        
        else:
            # Unknown action type
            raise HTTPException(
                status_code=400,
                detail=f"Unknown action type: {request.action}"
            )
    
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        # Log the error
        logger.error(f"Error processing ZealX request: {str(e)}", exc_info=True)
        
        # Create error response
        error_detail = ErrorDetail(
            code="PROCESSING_ERROR",
            message=f"Error processing {request.action} request",
            details={"error": str(e)},
            suggestion="Please check your request and try again"
        )
        
        return ZealXResponse(
            response=None,
            meta={
                "processing_time": f"{int((time.time() - start_time) * 1000)}ms"
            },
            request_id=request.request_id,
            success=False,
            error=error_detail
        )

@router.post("/brainx", response_model=BrainXResponse)
async def brainx_endpoint(
    request: BrainXRequest,
    api_manager = Depends(get_api_manager)
):
    """
    Dedicated BrainX endpoint for direct access to the AI model
    """
    return await handle_brainx_request(request, api_manager)

@router.post("/autox", response_model=AutoXResponse)
async def autox_endpoint(
    request: AutoXRequest,
    background_tasks: BackgroundTasks,
    user_id: str = "anonymous"
):
    """
    Dedicated AutoX endpoint for automation tasks
    """
    return await handle_autox_request(request, background_tasks, user_id)

@router.get("/autox/tasks/{task_id}", response_model=AutoXTask)
async def get_autox_task(task_id: str):
    """
    Get details of a specific AutoX task
    """
    # Get task details from database
    tasks = await logging_manager.get_recent_tasks(limit=100)
    task = next((t for t in tasks if t["task_id"] == task_id), None)
    
    if not task:
        raise HTTPException(
            status_code=404,
            detail=f"Task {task_id} not found"
        )
    
    # Get logs for this task
    logs = await logging_manager.get_task_logs(task_id)
    
    # Convert to AutoXTask model
    return AutoXTask(
        task_id=task["task_id"],
        app_id=task["app_id"],
        action_type=task["action_type"],
        action_data=task["action_data"],
        priority=task["priority"],
        created_at=datetime.fromisoformat(task["created_at"]),
        status=task["status"],
        execution_log=logs
    )

@router.get("/autox/tasks", response_model=List[AutoXTask])
async def get_autox_tasks(limit: int = 10):
    """
    Get recent AutoX tasks
    """
    tasks = await logging_manager.get_recent_tasks(limit=limit)
    
    # Convert to AutoXTask models
    return [
        AutoXTask(
            task_id=task["task_id"],
            app_id=task["app_id"],
            action_type=task["action_type"],
            action_data=task["action_data"],
            priority=task["priority"],
            created_at=datetime.fromisoformat(task["created_at"]),
            status=task["status"],
            execution_log=[]  # Don't include logs in the list view for efficiency
        )
        for task in tasks
    ]

@router.get("/system/status", response_model=SystemStatus)
async def system_status_endpoint(
    api_manager = Depends(get_api_manager)
):
    """
    Get system status including ADX information
    """
    return await get_system_status(api_manager)

@router.get("/system/api_status", response_model=APIAccountStatus)
async def api_status_endpoint(
    api_manager = Depends(get_api_manager)
):
    """
    Get API account status for multi-account management
    """
    return await api_manager.get_all_accounts_status()

# Client Storage API Endpoints
@router.get("/storage/files")
async def get_storage_files(request: Request):
    """
    Get all files for client-side storage.
    
    Returns:
        dict: List of files and their metadata for client-side storage
    """
    files = storage.get_all_files_for_client()
    return JSONResponse(content=files)

@router.get("/storage/file/{filename}")
async def get_storage_file(filename: str, request: Request):
    """
    Get a specific file for client-side storage.
    
    Args:
        filename (str): Name of the file to retrieve
        
    Returns:
        dict: File metadata and content for client-side storage
    """
    # Handle special files
    if filename == "stats.json":
        return JSONResponse(content=storage.get_stats())
    elif filename == "maintenance.json":
        return JSONResponse(content=storage.get_maintenance_instructions())
    elif filename == "cleanup.json":
        return JSONResponse(content=storage.get_cleanup_instructions())
    elif filename == "client_storage_instructions.json":
        return JSONResponse(content=get_client_storage_instructions())
    
    # For other files, return from the all files list
    files = storage.get_all_files_for_client()
    for file in files["files"]:
        if file["filename"] == filename:
            return JSONResponse(content=file)
    
    raise HTTPException(status_code=404, detail=f"File {filename} not found")

@router.get("/storage/db/schema")
async def get_db_schema(request: Request):
    """
    Get database schema for client-side storage.
    
    Returns:
        dict: Database schema for client-side storage
    """
    schema = get_database_schema()
    return JSONResponse(content=schema)

@router.get("/storage/db/init-script")
async def get_db_init_script(request: Request):
    """
    Get database initialization script for client-side storage.
    
    Returns:
        str: Database initialization script
    """
    script = generate_client_db_init_script()
    return Response(content=script, media_type="text/plain")

@router.get("/storage/db/export")
async def export_db_data(request: Request, limit: int = 100):
    """
    Export database data for client-side storage.
    
    Args:
        limit (int): Maximum number of records to export
        
    Returns:
        list: Database records for client-side storage
    """
    data = export_database_data(limit=limit)
    return JSONResponse(content=data)

# ADX Mode API Endpoints
class AdxModeRequest(BaseModel):
    mode: str

@router.post("/storage/adx/mode")
async def set_adx_mode(request: AdxModeRequest):
    """
    Set the ADX mode for StorageX operations.
    
    Args:
        mode (str): ADX mode (NORMAL, OPTIMIZED, CONSERVATIVE, SUSPENDED)
        
    Returns:
        dict: Updated ADX settings
    """
    result = storage.set_adx_mode(request.mode)
    return JSONResponse(content=result)

@router.get("/storage/adx/settings")
async def get_adx_settings(request: Request, mode: Optional[str] = None):
    """
    Get ADX settings for file operations.
    
    Args:
        mode (str, optional): ADX mode to get settings for
        
    Returns:
        dict: ADX settings for file operations
    """
    # If no mode specified, use the current mode from storage
    if mode is None:
        mode = storage.stats["adx_mode"]
    
    settings = get_adx_optimized_file_operations(mode)
    return JSONResponse(content=settings)

@router.get("/storage/adx/status")
async def get_adx_status(request: Request):
    """
    Get current ADX status.
    
    Returns:
        dict: Current ADX status
    """
    status = {
        "adx_mode": storage.stats["adx_mode"],
        "settings": get_adx_optimized_file_operations(storage.stats["adx_mode"]),
        "timestamp": storage.stats.get("last_updated", "")
    }
    return JSONResponse(content=status)

# Memory API Endpoints
class MemoryRequest(BaseModel):
    text: str
    embedding: Optional[List[float]] = None

@router.post("/storage/memory")
async def store_memory(request: MemoryRequest):
    """
    Store memory data for client-side storage.
    
    Args:
        text (str): Text to store
        embedding (list, optional): Vector embedding for the text
        
    Returns:
        dict: Memory data for client-side storage
    """
    result = storage.store_memory_with_embedding(request.text, request.embedding)
    return JSONResponse(content=result)

@router.get("/storage/memory/{memory_id}")
async def get_memory(memory_id: int, request: Request):
    """
    Get memory retrieval instructions for client-side storage.
    
    Args:
        memory_id (int): ID of the memory to retrieve
        
    Returns:
        dict: Memory retrieval instructions for client-side implementation
    """
    result = storage.get_memory_instructions(memory_id)
    return JSONResponse(content=result)

class SearchRequest(BaseModel):
    query_embedding: List[float]
    top_k: Optional[int] = 5

@router.post("/storage/search")
async def search_memories(request: SearchRequest):
    """
    Get search instructions for client-side storage.
    
    Args:
        query_embedding (list): Vector embedding to search for
        top_k (int, optional): Number of results to return
        
    Returns:
        dict: Search instructions for client-side implementation
    """
    result = storage.search_similar_memories_instructions(request.query_embedding, request.top_k)
    return JSONResponse(content=result)

# Helper functions

async def handle_brainx_request(
    request: BrainXRequest,
    api_manager
) -> BrainXResponse:
    """
    Handle BrainX request by processing through FireLayers X++ and Mistral 7B
    """
    start_time = time.time()
    
    # Apply FireLayers X++ preprocessing
    fire_layers_config = request.fire_layers or FireLayersConfig()
    fire_layers.config = fire_layers_config
    
    # Preprocess messages
    processed_messages = fire_layers.preprocess_messages(request.messages)
    
    # Get optimized parameters
    params = {
        "temperature": request.temperature,
        "max_tokens": request.max_tokens,
        "stream": request.stream
    }
    optimized_params = fire_layers.get_optimized_parameters(processed_messages, params)
    
    # In a real implementation, this would call Mistral 7B
    # For now, we'll simulate the response
    await asyncio.sleep(0.2)  # Simulate API call
    
    # Simulate token usage
    prompt_tokens = sum(len(m.content.split()) for m in processed_messages)
    completion_tokens = 20  # Simulated
    
    # Record inference time
    inference_time = int((time.time() - start_time) * 1000)
    fire_layers.record_inference_time(inference_time)
    
    # Get FireLayers stats
    fire_layers_stats = fire_layers.get_stats()
    fire_layers_stats.update({
        "compression_ratio": len(processed_messages) / len(request.messages) if request.messages else 1.0,
        "adaptive_temp": optimized_params["temperature"],
        "inference_time": inference_time
    })
    
    # Create response
    return BrainXResponse(
        content="This is a simulated response from BrainX (Mistral 7B). In a real implementation, this would be the actual model output.",
        usage={
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": prompt_tokens + completion_tokens
        },
        fire_layers_stats=fire_layers_stats,
        processing_time=f"{inference_time}ms",
        model="mistral-7b"
    )

async def handle_autox_request(
    request: AutoXRequest,
    background_tasks: BackgroundTasks,
    user_id: str
) -> AutoXResponse:
    """
    Handle AutoX request by creating and scheduling a task
    """
    # Generate task ID
    task_id = f"task_{str(uuid.uuid4())[:8]}"
    
    # Log the task
    await logging_manager.log_task(
        task_id=task_id,
        app_id=request.app_id,
        action_type=request.trigger_type,
        action_data=request.trigger_data,
        priority=request.priority,
        status="queued"
    )
    
    # Log initial action
    await logging_manager.log_action(
        task_id=task_id,
        action="queue_task",
        status="success",
        details={
            "user_id": user_id,
            "app_id": request.app_id,
            "trigger_type": request.trigger_type
        }
    )
    
    # Schedule task execution
    if request.execution_mode == "async":
        background_tasks.add_task(
            execute_autox_task,
            task_id,
            request.app_id,
            request.trigger_type,
            request.trigger_data,
            request.priority
        )
        
        return AutoXResponse(
            task_id=task_id,
            status="queued"
        )
    else:
        # For sync execution, run the task now
        result = await execute_autox_task(
            task_id,
            request.app_id,
            request.trigger_type,
            request.trigger_data,
            request.priority
        )
        
        return AutoXResponse(
            task_id=task_id,
            status="completed" if result["success"] else "failed",
            result=result,
            execution_time=result.get("execution_time")
        )

async def execute_autox_task(
    task_id: str,
    app_id: str,
    trigger_type: str,
    trigger_data: Dict[str, Any],
    priority: int
) -> Dict[str, Any]:
    """
    Execute an AutoX task and log the results
    In a real implementation, this would dispatch to app-specific handlers
    """
    start_time = time.time()
    
    try:
        # Update task status
        await logging_manager.log_task(
            task_id=task_id,
            app_id=app_id,
            action_type=trigger_type,
            action_data=trigger_data,
            priority=priority,
            status="processing"
        )
        
        # Log processing start
        await logging_manager.log_action(
            task_id=task_id,
            action="start_processing",
            status="success",
            details={
                "app_id": app_id,
                "trigger_type": trigger_type
            }
        )
        
        # Simulate task execution
        await asyncio.sleep(0.5)  # Simulate processing time
        
        # In a real implementation, this would handle the task based on app_id and trigger_type
        # For now, we'll just simulate success
        result = {
            "success": True,
            "message": f"Successfully processed {trigger_type} for {app_id}",
            "execution_time": f"{int((time.time() - start_time) * 1000)}ms",
            "details": {
                "processed_at": datetime.now().isoformat()
            }
        }
        
        # Log successful completion
        await logging_manager.log_action(
            task_id=task_id,
            action="complete_task",
            status="success",
            details=result
        )
        
        # Update task status
        await logging_manager.log_task(
            task_id=task_id,
            app_id=app_id,
            action_type=trigger_type,
            action_data=trigger_data,
            priority=priority,
            status="completed"
        )
        
        return result
    
    except Exception as e:
        # Log error
        error_details = {
            "error": str(e),
            "execution_time": f"{int((time.time() - start_time) * 1000)}ms"
        }
        
        await logging_manager.log_action(
            task_id=task_id,
            action="execute_task",
            status="error",
            details=error_details
        )
        
        # Update task status
        await logging_manager.log_task(
            task_id=task_id,
            app_id=app_id,
            action_type=trigger_type,
            action_data=trigger_data,
            priority=priority,
            status="failed"
        )
        
        return {
            "success": False,
            "error": str(e),
            "execution_time": f"{int((time.time() - start_time) * 1000)}ms"
        }

async def get_system_status(api_manager = None) -> SystemStatus:
    """
    Get current system status including ADX information
    """
    import psutil
    from backend.models.api import ADXStatus
    
    # Get system metrics
    cpu_usage = psutil.cpu_percent(interval=0.1)
    memory_usage = psutil.virtual_memory().percent
    
    # Get uptime (simulated for now)
    uptime = 3600  # 1 hour
    
    # Get ADX status (simulated for now)
    adx_status = ADXStatus(
        is_sleeping=False,
        power_saving_mode=False,
        throttling_mode=False,
        monitoring_interval=60,
        last_activity=datetime.now(),
        stats={
            "sleep_count": 0,
            "wake_count": 0,
            "total_sleep_time": 0
        }
    )
    
    # Get API status if available
    api_status = {}
    if api_manager:
        accounts_status = await api_manager.get_all_accounts_status()
        api_status = {
            "cloudflare_accounts": {
                "active": accounts_status.total_accounts,
                "healthy": accounts_status.healthy_accounts,
                "rate_limited": accounts_status.rate_limited_accounts,
                "error": accounts_status.error_accounts
            },
            "response_times": {
                "brainx": "150ms",  # Simulated for now
                "autox": "80ms"     # Simulated for now
            }
        }
    
    return SystemStatus(
        status="online",
        uptime=uptime,
        active_users=10,  # Simulated for now
        memory_usage=memory_usage,
        cpu_usage=cpu_usage,
        adx_status=adx_status,
        api_status=api_status
    )
