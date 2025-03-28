# autox.py - AutoX AI router for ZealX Backend

from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks, Request
from typing import List, Dict, Any, Optional
import time
import json
import requests
import asyncio
from datetime import datetime
import uuid

from backend.core.config import settings
from backend.core.dependencies import get_current_active_user, get_api_account_manager, get_storage_manager, get_zealx_instance
from backend.models.user import User
from backend.models.api import AutoXRequest, AutoXTask, ZealXResponse

# Create router
router = APIRouter()

class AutoXAIService:
    """AutoX AI service for automation tasks using Cloudflare Workers AI."""
    
    def __init__(self, api_account_manager):
        self.api_account_manager = api_account_manager
        self.model = "llama-3"
        self.base_url = "https://api.cloudflare.com/client/v4/accounts/{account_id}/ai/run/{model}"
    
    async def process_trigger(self, app_id: str, trigger_type: str, trigger_data: Dict[str, Any]):
        """Process a trigger and generate a task.
        
        Args:
            app_id: ID of the app that triggered the event
            trigger_type: Type of trigger (message, notification, etc.)
            trigger_data: Data associated with the trigger
            
        Returns:
            dict: Task to execute
        """
        start_time = time.time()
        
        # Get API account
        account = self.api_account_manager.get_next_account()
        api_key = account["api_key"]
        account_id = account["account_id"]
        
        # Prepare request
        url = self.base_url.format(account_id=account_id, model=self.model)
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        # Create system prompt
        system_prompt = f"""You are AutoX AI, an automation assistant that processes triggers from apps and generates tasks to execute.
        
Current app: {app_id}
Trigger type: {trigger_type}

Your task is to analyze the trigger data and generate a task to execute. The task should include:
1. The action type (e.g., send_message, set_reminder, etc.)
2. The action data (parameters needed to execute the action)
3. The priority (1-5, where 1 is highest priority)

Respond with a JSON object containing the task details.
"""
        
        # Create user prompt with trigger data
        user_prompt = f"Process this trigger data: {json.dumps(trigger_data, indent=2)}"
        
        # Prepare payload
        payload = {
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "temperature": 0.3,
            "max_tokens": 512
        }
        
        # Send request
        try:
            response = requests.post(url, headers=headers, json=payload)
            response.raise_for_status()
            
            # Parse response
            result = response.json()
            
            # Extract response text
            if "result" in result and "response" in result["result"]:
                response_text = result["result"]["response"]
            else:
                response_text = "Error: Invalid response format from AutoX AI"
            
            # Parse response text as JSON
            try:
                # Extract JSON from response text if needed
                if "{" in response_text and "}" in response_text:
                    json_start = response_text.find("{")
                    json_end = response_text.rfind("}") + 1
                    json_str = response_text[json_start:json_end]
                    task_data = json.loads(json_str)
                else:
                    task_data = json.loads(response_text)
                
                # Create task
                task = {
                    "task_id": str(uuid.uuid4()),
                    "app_id": app_id,
                    "action_type": task_data.get("action_type", "unknown"),
                    "action_data": task_data.get("action_data", {}),
                    "priority": task_data.get("priority", 3),
                    "created_at": datetime.now().isoformat()
                }
            except json.JSONDecodeError:
                # If response is not valid JSON, create a default task
                task = {
                    "task_id": str(uuid.uuid4()),
                    "app_id": app_id,
                    "action_type": "unknown",
                    "action_data": {"error": "Failed to parse response", "raw_response": response_text},
                    "priority": 5,
                    "created_at": datetime.now().isoformat()
                }
            
            # Calculate processing time
            processing_time = time.time() - start_time
            
            # Return task with metadata
            return {
                "task": task,
                "meta": {
                    "ai_engine": "AutoX",
                    "model": self.model,
                    "processing_time": f"{int(processing_time * 1000)}ms",
                    "account_index": account["index"]
                }
            }
        except requests.exceptions.RequestException as e:
            # Handle API errors
            error_message = f"AutoX API error: {str(e)}"
            
            # Try with another account if possible
            if len(settings.cloudflare.api_keys) > 1:
                print(f"Error with account {account['index']}, trying another account...")
                return await self.process_trigger(app_id, trigger_type, trigger_data)
            
            # Create error task
            task = {
                "task_id": str(uuid.uuid4()),
                "app_id": app_id,
                "action_type": "error",
                "action_data": {"error": error_message},
                "priority": 5,
                "created_at": datetime.now().isoformat()
            }
            
            return {
                "task": task,
                "meta": {
                    "ai_engine": "AutoX",
                    "error": error_message,
                    "processing_time": f"{int((time.time() - start_time) * 1000)}ms"
                }
            }

@router.post("/process-trigger", response_model=ZealXResponse)
async def process_trigger(
    request: AutoXRequest,
    current_user: User = Depends(get_current_active_user),
    api_account_manager = Depends(get_api_account_manager),
    storage_manager = Depends(get_storage_manager),
    zealx = Depends(get_zealx_instance)
):
    """Process a trigger and generate a task."""
    # Create AutoX AI instance
    autox_ai = AutoXAIService(api_account_manager)
    
    # Process trigger
    result = await autox_ai.process_trigger(
        app_id=request.app_id,
        trigger_type=request.trigger_type,
        trigger_data=request.trigger_data
    )
    
    # Store task in StorageX
    task_json = json.dumps(result["task"])
    storage_manager.store_structured_data(f"tasks/{result['task']['task_id']}.json", result["task"])
    
    # Trigger event in ZealX
    zealx.trigger_event(
        app_id=request.app_id,
        event_type=request.trigger_type,
        event_data=request.trigger_data
    )
    
    return ZealXResponse(
        response=result["task"],
        meta=result["meta"]
    )

@router.post("/execute-task", response_model=ZealXResponse)
async def execute_task(
    task: AutoXTask,
    current_user: User = Depends(get_current_active_user),
    zealx = Depends(get_zealx_instance)
):
    """Execute a task."""
    start_time = time.time()
    
    # Execute task in ZealX
    result = zealx.autox.execute_task(task.dict())
    
    # Calculate processing time
    processing_time = time.time() - start_time
    
    return ZealXResponse(
        response={"task_id": task.task_id, "status": "executed", "result": result},
        meta={
            "ai_engine": "AutoX Core",
            "processing_time": f"{int(processing_time * 1000)}ms"
        }
    )

@router.get("/adx-status")
async def get_adx_status(
    current_user: User = Depends(get_current_active_user),
    zealx = Depends(get_zealx_instance)
):
    """Get ADX status."""
    adx = zealx.adx
    
    return {
        "is_sleeping": adx.is_sleeping,
        "power_saving_mode": adx.power_saving_mode if hasattr(adx, "power_saving_mode") else False,
        "throttling_mode": adx.throttling_mode if hasattr(adx, "throttling_mode") else False,
        "monitoring_interval": adx.monitoring_interval,
        "last_activity": adx.last_activity.isoformat(),
        "stats": adx.stats
    }

@router.post("/adx-control")
async def control_adx(
    action: str,
    current_user: User = Depends(get_current_active_user),
    zealx = Depends(get_zealx_instance)
):
    """Control ADX."""
    adx = zealx.adx
    
    if action == "sleep":
        adx.sleep()
        return {"status": "success", "message": "ADX put to sleep"}
    elif action == "wake":
        adx.wake()
        return {"status": "success", "message": "ADX woken up"}
    elif action == "check_resources":
        adx.check_system_resources()
        return {"status": "success", "message": "System resources checked"}
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid action: {action}"
        )
