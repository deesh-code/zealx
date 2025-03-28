# api.py - API models for ZealX Backend

from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict, Any, Union, Literal
from datetime import datetime
from enum import Enum
import uuid

class ActionType(str, Enum):
    """Type of action to perform."""
    BRAINX = "brainx"
    AUTOX = "autox"
    STORAGE = "storage"
    SYSTEM = "system"

class MessageRole(str, Enum):
    """Role in a conversation."""
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    FUNCTION = "function"

class Message(BaseModel):
    """Message model for conversations."""
    role: MessageRole
    content: str
    name: Optional[str] = None
    function_call: Optional[Dict[str, Any]] = None

class ZealXRequest(BaseModel):
    """Base request model for ZealX API."""
    user_id: str
    action: ActionType
    data: Union[List[Message], Dict[str, Any]]
    request_id: Optional[str] = Field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: Optional[datetime] = Field(default_factory=datetime.now)
    
    class Config:
        json_schema_extra = {
            "example": {
                "user_id": "12345",
                "action": "brainx",
                "data": [{"role": "user", "content": "Hello, BrainX!"}],
                "request_id": "550e8400-e29b-41d4-a716-446655440000"
            }
        }

class ErrorDetail(BaseModel):
    """Detailed error information."""
    code: str
    message: str
    details: Optional[Dict[str, Any]] = None
    suggestion: Optional[str] = None

class ZealXResponse(BaseModel):
    """Base response model for ZealX API."""
    response: Union[str, Dict[str, Any]]
    meta: Dict[str, Any]
    request_id: Optional[str] = None
    success: bool = True
    error: Optional[ErrorDetail] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "response": "Hello! How can I assist you?",
                "meta": {
                    "ai_engine": "BrainX",
                    "processing_time": "120ms",
                    "model": "mistral-7b"
                },
                "request_id": "550e8400-e29b-41d4-a716-446655440000",
                "success": True
            }
        }

class FireLayersConfig(BaseModel):
    """Configuration for FireLayers system."""
    enabled: bool
    protection_level: str
    auto_update: bool
    last_updated: str

class ADXStatus(BaseModel):
    """Status of the Adaptive Execution Mode (ADX) system."""
    mode: str
    description: str
    check_interval_ms: int
    batch_size: int
    compression_level: Optional[int] = None
    recommended_for: Optional[str] = None
    timestamp: str

class BrainXRequest(BaseModel):
    """Request model for BrainX AI."""
    messages: List[Message]
    stream: bool = False
    temperature: Optional[float] = 0.7
    max_tokens: Optional[int] = 1024
    fire_layers: Optional[FireLayersConfig] = None
    user_context: Optional[Dict[str, Any]] = None
    
    @validator('messages')
    def validate_messages(cls, v):
        if not v:
            raise ValueError("At least one message is required")
        return v
    
    class Config:
        json_schema_extra = {
            "example": {
                "messages": [
                    {"role": "system", "content": "You are BrainX, a helpful AI assistant."},
                    {"role": "user", "content": "Hello, BrainX!"}
                ],
                "stream": False,
                "temperature": 0.7,
                "max_tokens": 1024,
                "fire_layers": {
                    "enabled": True,
                    "protection_level": "high",
                    "auto_update": True,
                    "last_updated": "2023-01-01T12:00:00"
                }
            }
        }

class BrainXResponse(BaseModel):
    """Response model for BrainX AI."""
    content: str
    usage: Dict[str, int]
    fire_layers_stats: Optional[Dict[str, Any]] = None
    processing_time: str
    model: str = "mistral-7b"
    
    class Config:
        json_schema_extra = {
            "example": {
                "content": "Hello! How can I assist you today?",
                "usage": {
                    "prompt_tokens": 20,
                    "completion_tokens": 10,
                    "total_tokens": 30
                },
                "fire_layers_stats": {
                    "compression_ratio": 0.8,
                    "adaptive_temp": 0.65,
                    "inference_time": 120
                },
                "processing_time": "120ms",
                "model": "mistral-7b"
            }
        }

class AutoXRequest(BaseModel):
    """Request model for AutoX AI."""
    app_id: str
    trigger_type: str
    trigger_data: Dict[str, Any]
    priority: int = 1
    execution_mode: Literal["sync", "async"] = "async"
    
    @validator('app_id')
    def validate_app_id(cls, v):
        allowed_apps = ["whatsapp", "instagram", "gmail", "calendar", "system"]
        if v not in allowed_apps:
            raise ValueError(f"app_id must be one of: {', '.join(allowed_apps)}")
        return v
    
    class Config:
        json_schema_extra = {
            "example": {
                "app_id": "whatsapp",
                "trigger_type": "message",
                "trigger_data": {
                    "chat_id": "test_chat",
                    "sender": "Test User",
                    "text": "Hello ZealX, can you help me?"
                },
                "priority": 1,
                "execution_mode": "async"
            }
        }

class AutoXResponse(BaseModel):
    """Response model for AutoX AI."""
    task_id: str
    status: Literal["queued", "processing", "completed", "failed"]
    result: Optional[Dict[str, Any]] = None
    error: Optional[ErrorDetail] = None
    execution_time: Optional[str] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "task_id": "task_12345",
                "status": "queued",
                "result": None,
                "execution_time": None
            }
        }

class AutoXTask(BaseModel):
    """Task model for AutoX AI."""
    task_id: str
    app_id: str
    action_type: str
    action_data: Dict[str, Any]
    priority: int = 1
    created_at: datetime
    status: Literal["queued", "processing", "completed", "failed"] = "queued"
    execution_log: List[Dict[str, Any]] = Field(default_factory=list)
    
    class Config:
        json_schema_extra = {
            "example": {
                "task_id": "task_12345",
                "app_id": "whatsapp",
                "action_type": "send_message",
                "action_data": {
                    "chat_id": "test_chat",
                    "text": "Hello! I'm ZealX, how can I help you?"
                },
                "priority": 1,
                "created_at": "2023-01-01T12:00:00",
                "status": "queued",
                "execution_log": []
            }
        }

class AutoXLog(BaseModel):
    """Log entry for AutoX execution."""
    timestamp: datetime = Field(default_factory=datetime.now)
    task_id: str
    action: str
    status: str
    details: Dict[str, Any] = Field(default_factory=dict)
    
    class Config:
        json_schema_extra = {
            "example": {
                "timestamp": "2023-01-01T12:00:00",
                "task_id": "task_12345",
                "action": "send_message",
                "status": "success",
                "details": {
                    "chat_id": "test_chat",
                    "message_id": "msg_67890"
                }
            }
        }

class StorageRequest(BaseModel):
    """Request model for StorageX."""
    operation: str
    data: Dict[str, Any]
    
    class Config:
        json_schema_extra = {
            "example": {
                "operation": "store_memory",
                "data": {
                    "text": "This is a test memory for ZealX",
                    "embedding": None
                }
            }
        }

class SystemStatus(BaseModel):
    """System status model."""
    status: str
    uptime: float
    active_users: int
    memory_usage: float
    cpu_usage: float
    adx_status: ADXStatus
    api_status: Dict[str, Any] = Field(default_factory=dict)
    
    class Config:
        json_schema_extra = {
            "example": {
                "status": "online",
                "uptime": 3600,
                "active_users": 10,
                "memory_usage": 50.5,
                "cpu_usage": 30.2,
                "adx_status": {
                    "mode": "active",
                    "description": "Adaptive Execution Mode",
                    "check_interval_ms": 1000,
                    "batch_size": 10,
                    "compression_level": 5,
                    "recommended_for": "high-performance",
                    "timestamp": "2023-01-01T12:00:00"
                },
                "api_status": {
                    "cloudflare_accounts": {
                        "active": 3,
                        "healthy": 2,
                        "rate_limited": 1
                    },
                    "response_times": {
                        "brainx": "150ms",
                        "autox": "80ms"
                    }
                }
            }
        }

class APIHealthStatus(BaseModel):
    """API health status model for multi-account monitoring."""
    account_id: str
    api_key_masked: str  # Masked API key for security
    status: Literal["healthy", "rate_limited", "error"]
    last_checked: datetime
    response_time: int  # milliseconds
    remaining_requests: Optional[int] = None
    reset_time: Optional[datetime] = None
    error_message: Optional[str] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "account_id": "account_123",
                "api_key_masked": "cf_key_****abcd",
                "status": "healthy",
                "last_checked": "2023-01-01T12:00:00",
                "response_time": 120,
                "remaining_requests": 950,
                "reset_time": "2023-01-01T13:00:00"
            }
        }

class APIAccountStatus(BaseModel):
    """Overall API account status for multi-account management."""
    total_accounts: int
    healthy_accounts: int
    rate_limited_accounts: int
    error_accounts: int
    accounts: List[APIHealthStatus]
    
    class Config:
        json_schema_extra = {
            "example": {
                "total_accounts": 3,
                "healthy_accounts": 2,
                "rate_limited_accounts": 1,
                "error_accounts": 0,
                "accounts": [
                    {
                        "account_id": "account_123",
                        "api_key_masked": "cf_key_****abcd",
                        "status": "healthy",
                        "last_checked": "2023-01-01T12:00:00",
                        "response_time": 120,
                        "remaining_requests": 950,
                        "reset_time": "2023-01-01T13:00:00"
                    }
                ]
            }
        }
