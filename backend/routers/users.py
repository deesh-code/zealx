# users.py - User management router for ZealX Backend

from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordRequestForm
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta

from backend.core.config import settings
from backend.core.dependencies import (
    get_current_active_user, authenticate_user, create_access_token,
    get_user, get_zealx_instance
)
from backend.models.user import User, UserCreate, UserUpdate, Token

# Create router
router = APIRouter()

@router.post("/token", response_model=Token)
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    """Login and get access token."""
    user = authenticate_user(form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Create access token
    access_token_expires = timedelta(minutes=settings.access_token_expire_minutes)
    access_token = create_access_token(
        data={"sub": user.username},
        expires_delta=access_token_expires
    )
    
    return {"access_token": access_token, "token_type": "bearer"}

@router.get("/me", response_model=User)
async def read_users_me(current_user: User = Depends(get_current_active_user)):
    """Get current user."""
    return current_user

@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register_user(user: UserCreate):
    """Register a new user.
    
    Note: In a production system, this would store the user in a database
    and properly hash the password.
    """
    # Check if username already exists
    if get_user(user.username):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already registered"
        )
    
    # In a real implementation, this would store the user in a database
    # For this demo, we'll just return a success message
    return {"message": "User registered successfully"}

@router.put("/me", response_model=User)
async def update_user(
    user_update: UserUpdate,
    current_user: User = Depends(get_current_active_user)
):
    """Update current user."""
    # In a real implementation, this would update the user in a database
    # For this demo, we'll just return the updated user
    updated_user = current_user.copy()
    
    if user_update.email is not None:
        updated_user.email = user_update.email
    
    if user_update.is_premium is not None:
        updated_user.is_premium = user_update.is_premium
    
    return updated_user

@router.get("/zealx-status")
async def get_zealx_status(
    current_user: User = Depends(get_current_active_user),
    zealx = Depends(get_zealx_instance)
):
    """Get ZealX status for current user."""
    return {
        "user_id": current_user.username,
        "is_premium": current_user.is_premium,
        "zealx_running": zealx.running,
        "active_apps": zealx.autox.active_apps if hasattr(zealx.autox, "active_apps") else [],
        "adx_status": {
            "is_sleeping": zealx.adx.is_sleeping,
            "last_activity": zealx.adx.last_activity.isoformat()
        }
    }
