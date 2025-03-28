# brainx.py - BrainX AI router for ZealX Backend

from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks, Request
from typing import List, Dict, Any, Optional
import time
import json
import requests
import asyncio
from datetime import datetime

from backend.core.config import settings
from backend.core.dependencies import get_current_active_user, get_api_account_manager, get_storage_manager
from backend.models.user import User
from backend.models.api import BrainXRequest, ZealXResponse, Message, MessageRole

# Create router
router = APIRouter()

class BrainXAI:
    """BrainX AI implementation using Cloudflare Workers AI with FireLayers X++."""
    
    def __init__(self, api_account_manager):
        self.api_account_manager = api_account_manager
        self.model = "mistral-7b"
        self.base_url = "https://api.cloudflare.com/client/v4/accounts/{account_id}/ai/run/{model}"
        self.fire_layers_enabled = settings.cloudflare.fire_layers_enabled
        self.adaptive_processing = settings.cloudflare.adaptive_processing
        self.min_inference_time = settings.cloudflare.min_inference_time
        self.max_inference_time = settings.cloudflare.max_inference_time
    
    async def generate_response(self, messages: List[Message], temperature: float = 0.7, max_tokens: int = 1024):
        """Generate response from BrainX AI.
        
        Args:
            messages: List of messages in the conversation
            temperature: Temperature for response generation
            max_tokens: Maximum tokens to generate
            
        Returns:
            dict: Response from BrainX AI
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
        
        # Convert messages to format expected by Cloudflare
        cf_messages = []
        for msg in messages:
            cf_message = {
                "role": msg.role,
                "content": msg.content
            }
            if msg.name:
                cf_message["name"] = msg.name
            if msg.function_call:
                cf_message["function_call"] = msg.function_call
            cf_messages.append(cf_message)
        
        # Prepare payload
        payload = {
            "messages": cf_messages,
            "temperature": temperature,
            "max_tokens": max_tokens
        }
        
        # Apply FireLayers X++ if enabled
        if self.fire_layers_enabled:
            payload = self._apply_fire_layers(payload)
        
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
                response_text = "Error: Invalid response format from BrainX AI"
            
            # Calculate processing time
            processing_time = time.time() - start_time
            
            # Apply adaptive processing if enabled
            if self.adaptive_processing:
                self._adapt_processing(processing_time)
            
            # Return response
            return {
                "response": response_text,
                "meta": {
                    "ai_engine": "BrainX",
                    "model": self.model,
                    "processing_time": f"{int(processing_time * 1000)}ms",
                    "account_index": account["index"],
                    "fire_layers": self.fire_layers_enabled
                }
            }
        except requests.exceptions.RequestException as e:
            # Handle API errors
            error_message = f"BrainX API error: {str(e)}"
            
            # Try with another account if possible
            if len(settings.cloudflare.api_keys) > 1:
                print(f"Error with account {account['index']}, trying another account...")
                return await self.generate_response(messages, temperature, max_tokens)
            
            return {
                "response": "I'm sorry, I'm having trouble connecting to my brain right now. Please try again later.",
                "meta": {
                    "ai_engine": "BrainX",
                    "error": error_message,
                    "processing_time": f"{int((time.time() - start_time) * 1000)}ms"
                }
            }
    
    def _apply_fire_layers(self, payload):
        """Apply FireLayers X++ optimizations to the request payload.
        
        This enhances the request with:
        1. Adaptive prompt optimization
        2. Context compression
        3. Inference optimization parameters
        
        Args:
            payload: Original request payload
            
        Returns:
            dict: Enhanced payload with FireLayers X++
        """
        # In a real implementation, this would apply sophisticated optimizations
        # For demonstration, we'll just add some FireLayers X++ parameters
        
        # Add FireLayers X++ parameters
        payload["fire_layers"] = {
            "version": "x++",
            "optimize_context": True,
            "compress_history": True,
            "adaptive_inference": True,
            "min_inference_time": self.min_inference_time,
            "max_inference_time": self.max_inference_time
        }
        
        return payload
    
    def _adapt_processing(self, processing_time):
        """Adapt processing parameters based on observed performance.
        
        Args:
            processing_time: Time taken to process the request in seconds
        """
        processing_time_ms = processing_time * 1000
        
        # Adjust inference time parameters based on observed performance
        if processing_time_ms < self.min_inference_time:
            # Too fast, increase quality
            self.min_inference_time = max(50, self.min_inference_time * 0.9)
            self.max_inference_time = max(100, self.max_inference_time * 0.9)
        elif processing_time_ms > self.max_inference_time:
            # Too slow, decrease quality
            self.min_inference_time = min(200, self.min_inference_time * 1.1)
            self.max_inference_time = min(1000, self.max_inference_time * 1.1)

@router.post("/generate", response_model=ZealXResponse)
async def generate_response(
    request: BrainXRequest,
    current_user: User = Depends(get_current_active_user),
    api_account_manager = Depends(get_api_account_manager),
    storage_manager = Depends(get_storage_manager)
):
    """Generate a response from BrainX AI."""
    # Create BrainX instance
    brainx = BrainXAI(api_account_manager)
    
    # Generate response
    response = await brainx.generate_response(
        messages=request.messages,
        temperature=request.temperature,
        max_tokens=request.max_tokens
    )
    
    # Store conversation in StorageX if it's a user message
    if request.messages and request.messages[-1].role == MessageRole.USER:
        # Store the conversation
        conversation_text = "\n".join([f"{msg.role}: {msg.content}" for msg in request.messages])
        storage_manager.store_memory_with_embedding(conversation_text)
    
    return ZealXResponse(
        response=response["response"],
        meta=response["meta"]
    )

@router.post("/chat", response_model=ZealXResponse)
async def chat(
    request: BrainXRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_active_user),
    api_account_manager = Depends(get_api_account_manager),
    storage_manager = Depends(get_storage_manager)
):
    """Chat with BrainX AI with background processing."""
    # Create BrainX instance
    brainx = BrainXAI(api_account_manager)
    
    # Generate response
    response = await brainx.generate_response(
        messages=request.messages,
        temperature=request.temperature,
        max_tokens=request.max_tokens
    )
    
    # Store conversation in background
    def store_conversation():
        if request.messages and request.messages[-1].role == MessageRole.USER:
            conversation_text = "\n".join([f"{msg.role}: {msg.content}" for msg in request.messages])
            storage_manager.store_memory_with_embedding(conversation_text)
    
    background_tasks.add_task(store_conversation)
    
    return ZealXResponse(
        response=response["response"],
        meta=response["meta"]
    )

@router.get("/status")
async def get_status(
    current_user: User = Depends(get_current_active_user),
    api_account_manager = Depends(get_api_account_manager)
):
    """Get BrainX AI status."""
    # Get API accounts status
    accounts = []
    for i in range(len(api_account_manager.api_keys)):
        accounts.append({
            "index": i,
            "usage_count": api_account_manager.usage_counts[i],
            "last_used": datetime.fromtimestamp(api_account_manager.last_used[i]).isoformat() if api_account_manager.last_used[i] > 0 else None
        })
    
    return {
        "status": "online",
        "accounts": accounts,
        "rotation_strategy": api_account_manager.rotation_strategy,
        "fire_layers_enabled": settings.cloudflare.fire_layers_enabled,
        "adaptive_processing": settings.cloudflare.adaptive_processing
    }
