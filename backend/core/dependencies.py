# dependencies.py - Dependency injection for ZealX Backend

from fastapi import Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from typing import Optional, Dict, Any
import time
from datetime import datetime, timedelta

from backend.core.config import settings
from backend.models.user import User, UserInDB
from storagex.storagex import StorageX

# OAuth2 scheme for token authentication
oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.api_prefix}/users/token")

# User database - In production, replace with actual database
# This is just a mock for demonstration
fake_users_db = {
    "user1": {
        "username": "user1",
        "email": "user1@example.com",
        "hashed_password": "$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW",  # "password"
        "is_premium": False,
        "disabled": False
    },
    "premium_user": {
        "username": "premium_user",
        "email": "premium@example.com",
        "hashed_password": "$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW",  # "password"
        "is_premium": True,
        "disabled": False
    }
}

# Account rotation state
class APIAccountManager:
    """Manages Cloudflare API account rotation for multi-account handling."""
    
    def __init__(self):
        self.api_keys = settings.cloudflare.api_keys
        self.account_ids = settings.cloudflare.account_ids
        self.current_index = 0
        self.usage_counts = {i: 0 for i in range(len(self.api_keys))}
        self.last_used = {i: 0 for i in range(len(self.api_keys))}
        self.rate_limit = settings.cloudflare.rate_limit_per_minute
        self.rotation_strategy = settings.cloudflare.rotation_strategy
    
    def get_next_account(self):
        """Get the next API account based on rotation strategy."""
        if not self.api_keys:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="No API keys configured"
            )
        
        if self.rotation_strategy == "round-robin":
            account = self._get_round_robin()
        elif self.rotation_strategy == "least-used":
            account = self._get_least_used()
        elif self.rotation_strategy == "adaptive":
            account = self._get_adaptive()
        else:
            account = self._get_round_robin()
        
        # Update usage statistics
        self.usage_counts[account["index"]] += 1
        self.last_used[account["index"]] = time.time()
        
        return account
    
    def _get_round_robin(self):
        """Simple round-robin rotation."""
        index = self.current_index
        self.current_index = (self.current_index + 1) % len(self.api_keys)
        
        return {
            "index": index,
            "api_key": self.api_keys[index],
            "account_id": self.account_ids[index] if index < len(self.account_ids) else None
        }
    
    def _get_least_used(self):
        """Get the least used account."""
        index = min(self.usage_counts, key=self.usage_counts.get)
        
        return {
            "index": index,
            "api_key": self.api_keys[index],
            "account_id": self.account_ids[index] if index < len(self.account_ids) else None
        }
    
    def _get_adaptive(self):
        """Adaptive rotation based on usage and time since last use."""
        # Find accounts that haven't been used recently
        current_time = time.time()
        cooldown_period = 60  # 1 minute cooldown
        
        # Filter accounts that are not in cooldown
        available_accounts = [
            i for i in range(len(self.api_keys)) 
            if (current_time - self.last_used[i]) > cooldown_period
        ]
        
        if not available_accounts:
            # If all accounts are in cooldown, use least recently used
            index = min(self.last_used, key=self.last_used.get)
        else:
            # Use the least used account among available ones
            index = min(available_accounts, key=lambda i: self.usage_counts[i])
        
        return {
            "index": index,
            "api_key": self.api_keys[index],
            "account_id": self.account_ids[index] if index < len(self.account_ids) else None
        }

# Create global instances
api_account_manager = APIAccountManager()
storage_instance = StorageX()

# Authentication functions
def verify_password(plain_password, hashed_password):
    """Verify password against hashed password."""
    # In production, use proper password hashing
    # from passlib.context import CryptContext
    # pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
    # return pwd_context.verify(plain_password, hashed_password)
    return plain_password == "password"  # Mock for demonstration

def get_user(username: str):
    """Get user from database."""
    if username in fake_users_db:
        user_dict = fake_users_db[username]
        return UserInDB(**user_dict)
    return None

def authenticate_user(username: str, password: str):
    """Authenticate user with username and password."""
    user = get_user(username)
    if not user:
        return False
    if not verify_password(password, user.hashed_password):
        return False
    return user

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """Create JWT access token."""
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.access_token_expire_minutes)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.secret_key, algorithm=settings.algorithm)
    
    return encoded_jwt

async def get_current_user(token: str = Depends(oauth2_scheme)):
    """Get current user from JWT token."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    
    user = get_user(username)
    if user is None:
        raise credentials_exception
    
    return user

async def get_current_active_user(current_user: User = Depends(get_current_user)):
    """Get current active user."""
    if current_user.disabled:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user

async def get_api_account_manager():
    """Get API account manager for Cloudflare account rotation."""
    return api_account_manager

async def get_storage_manager():
    """Get StorageX instance."""
    return storage_instance

def get_zealx_instance(request: Request, user: User = Depends(get_current_active_user)):
    """Get or create ZealX instance for user."""
    if user.username not in request.app.state.zealx_instances:
        # Import here to avoid circular imports
        from zealx import ZealX
        
        # Create new ZealX instance for user
        zealx = ZealX(user_id=user.username, is_premium=user.is_premium)
        zealx.start()
        request.app.state.zealx_instances[user.username] = zealx
    
    return request.app.state.zealx_instances[user.username]
