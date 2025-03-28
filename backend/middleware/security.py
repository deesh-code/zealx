"""
Security middleware for ZealX Backend
Provides API security, rate limiting, and authentication
"""

import time
import logging
from typing import List, Dict, Any, Optional, Callable
from fastapi import Request, Response, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.status import HTTP_429_TOO_MANY_REQUESTS, HTTP_401_UNAUTHORIZED
import redis.asyncio as redis
import json
import hashlib
import jwt
from datetime import datetime, timedelta
import secrets

from backend.core.config import Settings

# Configure logger
logger = logging.getLogger("zealx.security")

# Security token handling
security = HTTPBearer()

class RateLimiter:
    """
    Redis-based rate limiter for API endpoints
    Supports different rate limits based on user role and endpoint
    """
    
    def __init__(self, redis_client: redis.Redis, settings: Settings):
        self.redis = redis_client
        self.settings = settings
        self.default_rate_limit = 100  # requests per minute
        self.default_burst_limit = 5   # concurrent requests
        
        # Rate limit configuration by endpoint and role
        self.rate_limits = {
            # Format: "endpoint_prefix": {"role": limit_per_minute}
            "/api/brainx": {
                "anonymous": 10,
                "user": 60,
                "premium": 200,
                "admin": 0  # 0 means no limit
            },
            "/api/autox": {
                "anonymous": 5,
                "user": 30,
                "premium": 100,
                "admin": 0
            },
            "/api/zealx": {
                "anonymous": 10,
                "user": 50,
                "premium": 150,
                "admin": 0
            }
        }
        
        # Burst limit configuration by endpoint and role
        self.burst_limits = {
            # Format: "endpoint_prefix": {"role": concurrent_requests}
            "/api/brainx": {
                "anonymous": 2,
                "user": 3,
                "premium": 5,
                "admin": 0  # 0 means no limit
            },
            "/api/autox": {
                "anonymous": 1,
                "user": 2,
                "premium": 3,
                "admin": 0
            }
        }
    
    def _get_rate_limit(self, endpoint: str, role: str) -> int:
        """Get rate limit for endpoint and role"""
        # Find matching endpoint prefix
        for prefix, limits in self.rate_limits.items():
            if endpoint.startswith(prefix):
                return limits.get(role, limits.get("user", self.default_rate_limit))
        
        # Default limit
        return self.default_rate_limit
    
    def _get_burst_limit(self, endpoint: str, role: str) -> int:
        """Get burst limit for endpoint and role"""
        # Find matching endpoint prefix
        for prefix, limits in self.burst_limits.items():
            if endpoint.startswith(prefix):
                return limits.get(role, limits.get("user", self.default_burst_limit))
        
        # Default limit
        return self.default_burst_limit
    
    async def is_rate_limited(self, identifier: str, endpoint: str, role: str = "user") -> bool:
        """
        Check if request is rate limited
        Returns True if request should be blocked, False otherwise
        """
        rate_limit = self._get_rate_limit(endpoint, role)
        burst_limit = self._get_burst_limit(endpoint, role)
        
        # No limits for certain roles
        if rate_limit == 0 or burst_limit == 0:
            return False
        
        # Create Redis keys
        rate_key = f"zealx:ratelimit:{identifier}:{endpoint}:rate"
        burst_key = f"zealx:ratelimit:{identifier}:{endpoint}:burst"
        
        # Check burst limit (concurrent requests)
        current_burst = await self.redis.get(burst_key)
        current_burst = int(current_burst) if current_burst else 0
        
        if current_burst >= burst_limit:
            logger.warning(f"Burst limit exceeded for {identifier} on {endpoint}")
            return True
        
        # Increment burst counter with 10 second expiry
        await self.redis.setex(burst_key, 10, current_burst + 1)
        
        # Check rate limit using sorted set
        current_time = time.time()
        window_start = current_time - 60  # 1 minute window
        
        # Add current request to sorted set
        await self.redis.zadd(rate_key, {str(current_time): current_time})
        
        # Set expiry for the sorted set (2 minutes to be safe)
        await self.redis.expire(rate_key, 120)
        
        # Remove old requests from window
        await self.redis.zremrangebyscore(rate_key, 0, window_start)
        
        # Count requests in current window
        request_count = await self.redis.zcard(rate_key)
        
        # Check if rate limit exceeded
        if request_count > rate_limit:
            logger.warning(f"Rate limit exceeded for {identifier} on {endpoint}: {request_count}/{rate_limit}")
            return True
        
        return False
    
    async def complete_request(self, identifier: str, endpoint: str):
        """Mark request as completed (decrement burst counter)"""
        burst_key = f"zealx:ratelimit:{identifier}:{endpoint}:burst"
        
        # Decrement burst counter
        current_burst = await self.redis.get(burst_key)
        if current_burst and int(current_burst) > 0:
            await self.redis.decr(burst_key)

class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Middleware for rate limiting API requests
    Uses Redis to track request counts
    """
    
    def __init__(self, app, redis_client: redis.Redis, settings: Settings):
        super().__init__(app)
        self.rate_limiter = RateLimiter(redis_client, settings)
    
    async def dispatch(self, request: Request, call_next):
        # Skip rate limiting for non-API endpoints
        if not request.url.path.startswith("/api"):
            return await call_next(request)
        
        # Get client identifier (IP address or user ID if authenticated)
        identifier = self._get_client_identifier(request)
        endpoint = request.url.path
        
        # Get user role (default to "anonymous")
        role = await self._get_user_role(request)
        
        # Check rate limit
        is_limited = await self.rate_limiter.is_rate_limited(identifier, endpoint, role)
        
        if is_limited:
            # Return rate limit exceeded response
            return Response(
                content=json.dumps({
                    "detail": "Rate limit exceeded. Please try again later.",
                    "error_code": "RATE_LIMIT_EXCEEDED"
                }),
                status_code=HTTP_429_TOO_MANY_REQUESTS,
                media_type="application/json"
            )
        
        # Process request
        response = await call_next(request)
        
        # Mark request as completed
        await self.rate_limiter.complete_request(identifier, endpoint)
        
        return response
    
    def _get_client_identifier(self, request: Request) -> str:
        """Get client identifier from request"""
        # Try to get user ID from authorization header
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            # Extract user ID from token if possible
            try:
                token = auth_header.replace("Bearer ", "")
                payload = jwt.decode(
                    token, 
                    self.rate_limiter.settings.security.secret_key,
                    algorithms=["HS256"]
                )
                if "sub" in payload:
                    return f"user:{payload['sub']}"
            except:
                pass
        
        # Fall back to IP address
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            # Get the first IP in the chain
            client_ip = forwarded_for.split(",")[0].strip()
        else:
            client_ip = request.client.host
        
        return f"ip:{client_ip}"
    
    async def _get_user_role(self, request: Request) -> str:
        """Get user role from request"""
        # Try to get role from authorization header
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            try:
                token = auth_header.replace("Bearer ", "")
                payload = jwt.decode(
                    token, 
                    self.rate_limiter.settings.security.secret_key,
                    algorithms=["HS256"]
                )
                if "role" in payload:
                    return payload["role"]
            except:
                pass
        
        # Default to anonymous
        return "anonymous"

class APIKeyMiddleware(BaseHTTPMiddleware):
    """
    Middleware for API key authentication
    Validates API keys for protected endpoints
    """
    
    def __init__(self, app, settings: Settings):
        super().__init__(app)
        self.settings = settings
        self.api_key_header = "X-API-Key"
        self.protected_paths = ["/api/brainx", "/api/autox", "/api/zealx"]
        
        # In production, API keys would be stored in a database
        # For now, use the one from settings
        self.valid_api_keys = {
            self.settings.security.api_key: {
                "client_id": "default",
                "role": "admin"
            }
        }
    
    async def dispatch(self, request: Request, call_next):
        # Skip API key check for non-protected endpoints
        path = request.url.path
        if not any(path.startswith(p) for p in self.protected_paths):
            return await call_next(request)
        
        # Check for API key in header
        api_key = request.headers.get(self.api_key_header)
        
        # Skip check if not in production
        if not self.settings.environment == "production":
            # In development, only log missing API key
            if not api_key:
                logger.warning(f"Missing API key for {path}")
            return await call_next(request)
        
        # In production, enforce API key
        if not api_key or api_key not in self.valid_api_keys:
            logger.warning(f"Invalid API key for {path}")
            return Response(
                content=json.dumps({
                    "detail": "Invalid or missing API key",
                    "error_code": "INVALID_API_KEY"
                }),
                status_code=HTTP_401_UNAUTHORIZED,
                media_type="application/json"
            )
        
        # Add client info to request state
        request.state.client_id = self.valid_api_keys[api_key]["client_id"]
        request.state.client_role = self.valid_api_keys[api_key]["role"]
        
        return await call_next(request)

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Middleware to add security headers to responses
    """
    
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        
        # Add security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["Content-Security-Policy"] = "default-src 'self'; script-src 'self'; object-src 'none'"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        
        return response

# Auth utilities

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    settings: Settings = Depends(lambda: Settings())
):
    """
    Validate JWT token and return user information
    """
    try:
        payload = jwt.decode(
            credentials.credentials, 
            settings.security.secret_key,
            algorithms=["HS256"]
        )
        
        # Check if token is expired
        if "exp" in payload and payload["exp"] < time.time():
            raise HTTPException(
                status_code=HTTP_401_UNAUTHORIZED,
                detail="Token expired"
            )
        
        # Return user information
        return {
            "user_id": payload.get("sub"),
            "role": payload.get("role", "user"),
            "email": payload.get("email")
        }
    except jwt.PyJWTError:
        raise HTTPException(
            status_code=HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials"
        )

def create_access_token(
    data: dict,
    settings: Settings,
    expires_delta: Optional[timedelta] = None
):
    """
    Create a JWT access token
    """
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    
    to_encode.update({"exp": expire})
    
    return jwt.encode(
        to_encode, 
        settings.security.secret_key,
        algorithm="HS256"
    )

def setup_security_middleware(app, settings: Settings, redis_client: redis.Redis):
    """
    Setup all security middleware for the application
    """
    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.security.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Add trusted host middleware in production
    if settings.environment == "production":
        app.add_middleware(
            TrustedHostMiddleware,
            allowed_hosts=settings.security.allowed_hosts,
        )
    
    # Add security headers middleware
    app.add_middleware(SecurityHeadersMiddleware)
    
    # Add API key middleware
    app.add_middleware(APIKeyMiddleware, settings=settings)
    
    # Add rate limit middleware
    app.add_middleware(RateLimitMiddleware, redis_client=redis_client, settings=settings)
