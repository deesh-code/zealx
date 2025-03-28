# api.py - Unified API router for ZealX Backend

from fastapi import APIRouter, Depends, HTTPException, status, Request, BackgroundTasks
from typing import List, Dict, Any, Optional, Union
import time
import json
from datetime import datetime

from backend.core.config import settings
from backend.core.dependencies import get_current_active_user, get_api_account_manager, get_storage_manager, get_zealx_instance
from backend.models.user import User
from backend.models.api import ZealXRequest, ZealXResponse, ActionType, Message, MessageRole

# Import routers for delegation
from backend.routers.brainx import BrainXAI
from backend.routers.autox import AutoXAIService

# Create router
router = APIRouter()

class IntentRouter:
    """Routes requests to the appropriate AI service based on user intent."""
    
    def __init__(self, api_account_manager):
        self.api_account_manager = api_account_manager
        self.brainx = BrainXAI(api_account_manager)
        self.autox = AutoXAIService(api_account_manager)
    
    async def route_request(self, request: ZealXRequest):
        """Route request to the appropriate AI service.
        
        Args:
            request: ZealX API request
            
        Returns:
            dict: Response from the appropriate AI service
        """
        start_time = time.time()
        
        # Route based on action type
        if request.action == ActionType.BRAINX:
            # Process with BrainX
            if isinstance(request.data, list):
                # Convert to Message objects if they're not already
                messages = []
                for msg in request.data:
                    if isinstance(msg, dict):
                        messages.append(Message(**msg))
                    else:
                        messages.append(msg)
                
                # Generate response from BrainX
                result = await self.brainx.generate_response(messages)
                result["meta"]["router"] = "intent_router"
                return result
            else:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid data format for BrainX action"
                )
        
        elif request.action == ActionType.AUTOX:
            # Process with AutoX
            if isinstance(request.data, dict):
                app_id = request.data.get("app_id")
                trigger_type = request.data.get("trigger_type")
                trigger_data = request.data.get("trigger_data")
                
                if not all([app_id, trigger_type, trigger_data]):
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Missing required fields for AutoX action"
                    )
                
                # Process trigger with AutoX
                result = await self.autox.process_trigger(app_id, trigger_type, trigger_data)
                result["meta"]["router"] = "intent_router"
                return {
                    "response": result["task"],
                    "meta": result["meta"]
                }
            else:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid data format for AutoX action"
                )
        
        elif request.action == ActionType.STORAGE:
            # Process with StorageX
            # This would be implemented in a real system
            return {
                "response": "Storage operations not implemented in demo",
                "meta": {
                    "ai_engine": "StorageX",
                    "processing_time": f"{int((time.time() - start_time) * 1000)}ms",
                    "router": "intent_router"
                }
            }
        
        elif request.action == ActionType.SYSTEM:
            # Process system actions
            # This would be implemented in a real system
            return {
                "response": "System operations not implemented in demo",
                "meta": {
                    "ai_engine": "System",
                    "processing_time": f"{int((time.time() - start_time) * 1000)}ms",
                    "router": "intent_router"
                }
            }
        
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid action type: {request.action}"
            )

@router.post("/zealx", response_model=ZealXResponse)
async def process_zealx_request(
    request: ZealXRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_active_user),
    api_account_manager = Depends(get_api_account_manager),
    storage_manager = Depends(get_storage_manager),
    zealx = Depends(get_zealx_instance)
):
    """Process a ZealX request and route to the appropriate AI service."""
    # Create intent router
    router = IntentRouter(api_account_manager)
    
    # Record activity in ADX to prevent sleep mode
    zealx.adx.record_activity()
    
    # Route request
    result = await router.route_request(request)
    
    # Store request in background
    def store_request():
        try:
            # Store request data
            request_data = {
                "user_id": current_user.username,
                "action": request.action,
                "timestamp": datetime.now().isoformat(),
                "data": request.data if not isinstance(request.data, list) else [msg.dict() for msg in request.data]
            }
            
            # Store in StorageX
            storage_manager.store_structured_data(
                f"requests/{current_user.username}_{int(time.time())}.json",
                request_data
            )
        except Exception as e:
            print(f"Error storing request: {str(e)}")
    
    background_tasks.add_task(store_request)
    
    return ZealXResponse(
        response=result["response"],
        meta=result["meta"]
    )

@router.post("/detect-intent")
async def detect_intent(
    message: str,
    current_user: User = Depends(get_current_active_user),
    api_account_manager = Depends(get_api_account_manager)
):
    """Detect user intent from a message and suggest the appropriate action."""
    # Create BrainX instance
    brainx = BrainXAI(api_account_manager)
    
    # Create system prompt for intent detection
    system_prompt = """You are an intent detection system for ZealX. 
    Analyze the user message and determine if it's:
    1. A question or conversation (BrainX)
    2. An automation request (AutoX)
    3. A data storage request (StorageX)
    4. A system command (System)
    
    Respond with a JSON object containing:
    {
        "intent": "brainx|autox|storage|system",
        "confidence": 0.0-1.0,
        "app_id": "app_name" (only for AutoX),
        "action": "specific_action" (optional)
    }
    """
    
    # Create messages
    messages = [
        Message(role=MessageRole.SYSTEM, content=system_prompt),
        Message(role=MessageRole.USER, content=message)
    ]
    
    # Generate response
    result = await brainx.generate_response(messages, temperature=0.3, max_tokens=256)
    
    # Parse response as JSON
    try:
        # Extract JSON from response text if needed
        response_text = result["response"]
        if "{" in response_text and "}" in response_text:
            json_start = response_text.find("{")
            json_end = response_text.rfind("}") + 1
            json_str = response_text[json_start:json_end]
            intent_data = json.loads(json_str)
        else:
            intent_data = json.loads(response_text)
        
        return {
            "message": message,
            "detected_intent": intent_data,
            "meta": result["meta"]
        }
    except json.JSONDecodeError:
        return {
            "message": message,
            "detected_intent": {
                "intent": "brainx",  # Default to BrainX
                "confidence": 0.5,
                "error": "Failed to parse intent detection response"
            },
            "meta": result["meta"]
        }
