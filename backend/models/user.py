# user.py - User models for ZealX Backend

from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List, Dict, Any
from datetime import datetime

class User(BaseModel):
    """Base user model."""
    username: str
    email: Optional[EmailStr] = None
    is_premium: bool = False
    disabled: Optional[bool] = None

class UserInDB(User):
    """User model with password hash."""
    hashed_password: str

class Token(BaseModel):
    """Token model for authentication."""
    access_token: str
    token_type: str

class TokenData(BaseModel):
    """Token data model."""
    username: Optional[str] = None

class UserCreate(BaseModel):
    """User creation model."""
    username: str
    email: EmailStr
    password: str
    is_premium: bool = False

class UserUpdate(BaseModel):
    """User update model."""
    email: Optional[EmailStr] = None
    password: Optional[str] = None
    is_premium: Optional[bool] = None
    disabled: Optional[bool] = None
