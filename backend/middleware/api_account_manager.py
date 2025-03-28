"""
API Account Manager Middleware for ZealX Backend
Handles parallel API checking and fast failover between multiple accounts
"""

import asyncio
import time
import logging
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
import aiohttp
import json
import random
from fastapi import Request, Response
import redis.asyncio as redis
from pydantic import BaseModel, Field

from backend.models.api import APIHealthStatus, APIAccountStatus
from backend.core.config import Settings

# Configure logger
logger = logging.getLogger("zealx.api_account_manager")

class APIAccount(BaseModel):
    """API Account configuration"""
    account_id: str
    api_key: str
    weight: int = 1  # Higher weight = higher priority
    max_requests_per_minute: int = 1000
    enabled: bool = True

class APIAccountManager:
    """
    Manages multiple API accounts with parallel health checking and fast failover
    
    Features:
    - Parallel API health checking
    - Redis-based caching of API health status
    - Automatic failover to healthy accounts
    - Rate limit tracking and avoidance
    - Weighted selection of accounts based on priority
    """
    
    def __init__(self, settings: Settings, redis_client: redis.Redis):
        self.settings = settings
        self.redis_client = redis_client
        self.accounts: List[APIAccount] = []
        self.cache_key_prefix = "zealx:api_account:"
        self.cache_ttl = 300  # 5 minutes
        self.last_parallel_check = datetime.now() - timedelta(minutes=10)
        self.check_interval = 60  # seconds
        self._initialize_accounts()
    
    def _initialize_accounts(self):
        """Initialize API accounts from environment variables"""
        account_ids = self.settings.cloudflare.account_ids.split(',')
        api_keys = self.settings.cloudflare.api_keys.split(',')
        
        if len(account_ids) != len(api_keys):
            logger.error("Mismatch between number of account IDs and API keys")
            return
        
        for i, (account_id, api_key) in enumerate(zip(account_ids, api_keys)):
            # Default weight decreases with position to prioritize first accounts
            weight = len(account_ids) - i
            self.accounts.append(APIAccount(
                account_id=account_id.strip(),
                api_key=api_key.strip(),
                weight=weight
            ))
        
        logger.info(f"Initialized {len(self.accounts)} API accounts")
    
    async def get_account_status(self, account_id: str) -> Optional[APIHealthStatus]:
        """Get the cached status of a specific account"""
        cache_key = f"{self.cache_key_prefix}{account_id}"
        cached_data = await self.redis_client.get(cache_key)
        
        if not cached_data:
            return None
        
        try:
            status_dict = json.loads(cached_data)
            # Convert string datetime back to datetime object
            status_dict["last_checked"] = datetime.fromisoformat(status_dict["last_checked"])
            if status_dict.get("reset_time"):
                status_dict["reset_time"] = datetime.fromisoformat(status_dict["reset_time"])
            
            return APIHealthStatus(**status_dict)
        except Exception as e:
            logger.error(f"Error parsing cached account status: {e}")
            return None
    
    async def get_all_accounts_status(self) -> APIAccountStatus:
        """Get status of all accounts"""
        statuses = []
        healthy_count = 0
        rate_limited_count = 0
        error_count = 0
        
        for account in self.accounts:
            status = await self.get_account_status(account.account_id)
            
            if not status:
                # If no cached status, create a default one
                status = APIHealthStatus(
                    account_id=account.account_id,
                    api_key_masked=f"{account.api_key[:4]}****{account.api_key[-4:]}",
                    status="unknown",
                    last_checked=datetime.now() - timedelta(hours=1),
                    response_time=0
                )
            
            statuses.append(status)
            
            if status.status == "healthy":
                healthy_count += 1
            elif status.status == "rate_limited":
                rate_limited_count += 1
            elif status.status == "error":
                error_count += 1
        
        return APIAccountStatus(
            total_accounts=len(self.accounts),
            healthy_accounts=healthy_count,
            rate_limited_accounts=rate_limited_count,
            error_accounts=error_count,
            accounts=statuses
        )
    
    async def check_account_health(self, account: APIAccount) -> APIHealthStatus:
        """Check the health of a single account"""
        start_time = time.time()
        
        # Mask API key for security
        api_key_masked = f"{account.api_key[:4]}****{account.api_key[-4:]}"
        
        try:
            # Use Cloudflare API to check account health
            async with aiohttp.ClientSession() as session:
                headers = {
                    "Authorization": f"Bearer {account.api_key}",
                    "Content-Type": "application/json"
                }
                
                # Use a simple endpoint that doesn't consume many resources
                url = f"https://api.cloudflare.com/client/v4/accounts/{account.account_id}/members"
                
                async with session.get(url, headers=headers) as response:
                    response_time = int((time.time() - start_time) * 1000)  # in milliseconds
                    response_data = await response.json()
                    
                    # Check for rate limiting
                    remaining_requests = None
                    reset_time = None
                    
                    if "cf-ray" in response.headers:
                        # Extract rate limit info from headers
                        if "x-ratelimit-remaining" in response.headers:
                            remaining_requests = int(response.headers["x-ratelimit-remaining"])
                        
                        if "x-ratelimit-reset" in response.headers:
                            reset_timestamp = int(response.headers["x-ratelimit-reset"])
                            reset_time = datetime.fromtimestamp(reset_timestamp)
                    
                    if response.status == 429:
                        # Rate limited
                        return APIHealthStatus(
                            account_id=account.account_id,
                            api_key_masked=api_key_masked,
                            status="rate_limited",
                            last_checked=datetime.now(),
                            response_time=response_time,
                            remaining_requests=0,
                            reset_time=reset_time,
                            error_message="Rate limit exceeded"
                        )
                    
                    if response.status != 200 or not response_data.get("success", False):
                        # API error
                        error_msg = "Unknown error"
                        if response_data.get("errors") and len(response_data["errors"]) > 0:
                            error_msg = response_data["errors"][0].get("message", "API error")
                        
                        return APIHealthStatus(
                            account_id=account.account_id,
                            api_key_masked=api_key_masked,
                            status="error",
                            last_checked=datetime.now(),
                            response_time=response_time,
                            error_message=error_msg
                        )
                    
                    # Account is healthy
                    return APIHealthStatus(
                        account_id=account.account_id,
                        api_key_masked=api_key_masked,
                        status="healthy",
                        last_checked=datetime.now(),
                        response_time=response_time,
                        remaining_requests=remaining_requests,
                        reset_time=reset_time
                    )
        
        except Exception as e:
            logger.error(f"Error checking account health: {e}")
            return APIHealthStatus(
                account_id=account.account_id,
                api_key_masked=api_key_masked,
                status="error",
                last_checked=datetime.now(),
                response_time=0,
                error_message=str(e)
            )
    
    async def check_all_accounts_health(self):
        """Check health of all accounts in parallel"""
        logger.info("Starting parallel health check of all API accounts")
        
        # Only run parallel check if enough time has passed since last check
        current_time = datetime.now()
        if (current_time - self.last_parallel_check).total_seconds() < self.check_interval:
            logger.debug("Skipping health check, too soon since last check")
            return
        
        self.last_parallel_check = current_time
        
        # Create tasks for all account health checks
        tasks = []
        for account in self.accounts:
            if account.enabled:
                tasks.append(self.check_account_health(account))
        
        # Run all checks in parallel
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Process results and update cache
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"Error in health check: {result}")
                continue
            
            if not isinstance(result, APIHealthStatus):
                continue
            
            # Cache the result
            cache_key = f"{self.cache_key_prefix}{result.account_id}"
            
            # Convert datetime objects to strings for JSON serialization
            result_dict = result.dict()
            result_dict["last_checked"] = result.last_checked.isoformat()
            if result.reset_time:
                result_dict["reset_time"] = result.reset_time.isoformat()
            
            await self.redis_client.setex(
                cache_key,
                self.cache_ttl,
                json.dumps(result_dict)
            )
    
    async def get_best_account(self) -> Tuple[Optional[APIAccount], Optional[APIHealthStatus]]:
        """
        Get the best available account based on health status and weighting
        Returns both the account and its health status
        """
        # First, check if we need to refresh health status
        await self.check_all_accounts_health()
        
        # Get all healthy accounts
        healthy_accounts = []
        for account in self.accounts:
            if not account.enabled:
                continue
                
            status = await self.get_account_status(account.account_id)
            
            # If no status or status is old, consider it unknown
            if not status or (datetime.now() - status.last_checked).total_seconds() > self.cache_ttl:
                # We'll include it but with lower weight
                healthy_accounts.append((account, None, account.weight / 10))
                continue
            
            # Skip rate-limited or error accounts
            if status.status != "healthy":
                continue
            
            # Calculate effective weight based on remaining requests
            effective_weight = account.weight
            if status.remaining_requests is not None:
                # Adjust weight based on remaining requests
                # If close to rate limit, reduce weight
                remaining_ratio = status.remaining_requests / account.max_requests_per_minute
                if remaining_ratio < 0.1:  # Less than 10% remaining
                    effective_weight *= 0.1
                elif remaining_ratio < 0.3:  # Less than 30% remaining
                    effective_weight *= 0.5
            
            healthy_accounts.append((account, status, effective_weight))
        
        if not healthy_accounts:
            # No healthy accounts, try to find any non-error account
            for account in self.accounts:
                if not account.enabled:
                    continue
                    
                status = await self.get_account_status(account.account_id)
                
                # If rate limited but reset time is past, we can use it
                if status and status.status == "rate_limited" and status.reset_time:
                    if datetime.now() > status.reset_time:
                        return account, status
            
            # Still nothing, return the first account as fallback
            if self.accounts:
                return self.accounts[0], None
            return None, None
        
        # Use weighted random selection
        total_weight = sum(weight for _, _, weight in healthy_accounts)
        if total_weight <= 0:
            # Fallback to first account if weights are invalid
            return healthy_accounts[0][0], healthy_accounts[0][1]
        
        # Select account based on weight
        selection_point = random.uniform(0, total_weight)
        current_weight = 0
        
        for account, status, weight in healthy_accounts:
            current_weight += weight
            if current_weight >= selection_point:
                return account, status
        
        # Fallback to first account
        return healthy_accounts[0][0], healthy_accounts[0][1]
    
    async def get_api_key_for_request(self, request: Request) -> str:
        """Get the best API key to use for the current request"""
        account, _ = await self.get_best_account()
        if account:
            return account.api_key
        
        # Fallback to first account if available
        if self.accounts:
            return self.accounts[0].api_key
        
        # Last resort fallback
        return self.settings.cloudflare.default_api_key

class APIAccountMiddleware:
    """
    Middleware that injects the API Account Manager into the request state
    and handles automatic API key selection
    """
    
    def __init__(self, settings: Settings, redis_client: redis.Redis):
        self.api_manager = APIAccountManager(settings, redis_client)
    
    async def __call__(self, request: Request, call_next):
        # Attach the API manager to the request state
        request.state.api_manager = self.api_manager
        
        # Process the request
        response = await call_next(request)
        
        return response

def setup_api_account_middleware(app, settings: Settings, redis_client: redis.Redis):
    """Setup the API account middleware"""
    middleware = APIAccountMiddleware(settings, redis_client)
    app.middleware("http")(middleware)
