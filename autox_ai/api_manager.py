# api_manager.py - Manages API calls & rotates accounts on failure

import requests
import random
import time
import math
from datetime import datetime, timedelta
from .config import AUTOX_AI_ACCOUNTS, API_BASE_URL, RETRY_LIMIT, RATE_LIMIT_COOLDOWN, REQUEST_TIMEOUT, BACKOFF_BASE
from .logger import log_error, log_warning

class AutoXAIManager:
    def __init__(self):
        self.accounts = AUTOX_AI_ACCOUNTS
        self.current_index = random.randint(0, len(self.accounts) - 1)  # Start from a random account
        
        # Track account status and rate limits
        self.account_status = {}
        for i, account in enumerate(self.accounts):
            self.account_status[i] = {
                "failures": 0,
                "consecutive_failures": 0,
                "rate_limited_until": None,
                "last_success": None,
                "total_requests": 0,
                "total_failures": 0,
                "health_score": 100,  # 100 = perfect health, 0 = completely unreliable
                "cooldown_multiplier": 1.0,  # Dynamic cooldown multiplier
                "last_used": None  # Track when account was last used
            }
    
    def get_active_account(self):
        """Get the currently active account"""
        return self.accounts[self.current_index]
    
    def get_account_status(self, index=None):
        """Get status for a specific account or all accounts"""
        if index is not None:
            return self.account_status[index]
        return self.account_status
    
    def is_account_available(self, index):
        """Check if an account is currently available (not rate limited)"""
        status = self.account_status[index]
        if status["rate_limited_until"] and status["rate_limited_until"] > datetime.now():
            return False
        return True
    
    def mark_rate_limited(self, index, minutes=None):
        """Mark an account as rate limited for a specified time with dynamic cooldown"""
        status = self.account_status[index]
        
        # Increase cooldown multiplier based on consecutive failures
        status["consecutive_failures"] += 1
        status["cooldown_multiplier"] = min(5.0, status["cooldown_multiplier"] * 1.5)  # Cap at 5x
        
        # Calculate dynamic cooldown based on failure history
        base_cooldown = minutes or RATE_LIMIT_COOLDOWN
        dynamic_cooldown = base_cooldown * status["cooldown_multiplier"]
        
        # Update rate limit expiry
        status["rate_limited_until"] = datetime.now() + timedelta(minutes=dynamic_cooldown)
        status["failures"] += 1
        status["total_failures"] += 1
        
        # Update health score (decrease more for rate limits)
        self._update_health_score(index, -15)
        
        # Log with dynamic cooldown information
        account = self.accounts[index]
        log_warning(f"Account {account['account_id']} rate limited for {dynamic_cooldown:.1f} minutes (health: {status['health_score']}%)")
    
    def mark_success(self, index):
        """Mark an account as having a successful API call"""
        status = self.account_status[index]
        status["last_success"] = datetime.now()
        status["last_used"] = datetime.now()
        status["failures"] = 0  # Reset consecutive failures
        status["consecutive_failures"] = 0  # Reset consecutive failures counter
        status["total_requests"] += 1
        
        # Gradually recover cooldown multiplier
        status["cooldown_multiplier"] = max(1.0, status["cooldown_multiplier"] * 0.8)
        
        # Improve health score slightly with each success
        self._update_health_score(index, 5)
    
    def mark_failure(self, index, is_rate_limit=False):
        """Mark an account as having a failed API call"""
        status = self.account_status[index]
        status["failures"] += 1
        status["consecutive_failures"] += 1
        status["total_failures"] += 1
        status["last_used"] = datetime.now()
        
        # Update health score (general failures impact less than rate limits)
        self._update_health_score(index, -10)
        
        if is_rate_limit:
            self.mark_rate_limited(index)
        elif status["consecutive_failures"] >= 3:
            # After 3 consecutive failures that aren't rate limits, 
            # temporarily disable the account as it might have other issues
            cooldown_minutes = min(30, 5 * status["consecutive_failures"])
            status["rate_limited_until"] = datetime.now() + timedelta(minutes=cooldown_minutes)
            log_warning(f"Account {self.accounts[index]['account_id']} disabled for {cooldown_minutes} minutes due to {status['consecutive_failures']} consecutive failures")
    
    def _update_health_score(self, index, change):
        """Update the health score of an account"""
        status = self.account_status[index]
        status["health_score"] = max(0, min(100, status["health_score"] + change))
    
    def switch_account(self):
        """Switch to the next available account using health scores and smart selection"""
        # First try to find a healthy account that's available
        best_score = -1
        best_index = None
        
        # Find account with highest health score that's available
        for i, status in self.account_status.items():
            if self.is_account_available(i) and status["health_score"] > best_score:
                best_score = status["health_score"]
                best_index = i
        
        # If we found a healthy account with good health, use it immediately
        if best_index is not None and best_score > 70:  # Increased threshold for higher quality
            self.current_index = best_index
            return self.get_active_account()
        
        # If no healthy account found or all have low scores, try least recently used available account
        least_recent_time = None
        least_recent_index = None
        
        for i, status in self.account_status.items():
            if self.is_account_available(i):
                if status["last_used"] is None or (least_recent_time is None or status["last_used"] < least_recent_time):
                    least_recent_time = status["last_used"]
                    least_recent_index = i
        
        if least_recent_index is not None:
            self.current_index = least_recent_index
            return self.get_active_account()
        
        # If all accounts are rate limited, use the one with the earliest expiry
        earliest_expiry = None
        earliest_index = None
        
        for i, status in self.account_status.items():
            if status["rate_limited_until"]:
                if earliest_expiry is None or status["rate_limited_until"] < earliest_expiry:
                    earliest_expiry = status["rate_limited_until"]
                    earliest_index = i
        
        if earliest_index is not None:
            self.current_index = earliest_index
        
        return self.get_active_account()

    def run(self, model, inputs):
        retries = 0
        tried_accounts = set()  # Track which accounts we've already tried
        start_time = time.time()
        
        while retries < RETRY_LIMIT:
            account = self.get_active_account()
            account_index = self.current_index
            account_id = account["account_id"]
            
            # Skip if we've already tried this account in this run (unless we've tried all accounts)
            if account_id in tried_accounts and len(tried_accounts) < len(self.accounts):
                self.switch_account()
                continue
                
            tried_accounts.add(account_id)
            api_key = account["api_key"]
            url = API_BASE_URL.format(account_id)
            headers = {"Authorization": f"Bearer {api_key}"}
            
            # For security, only show first few chars of API key in logs
            api_key_prefix = api_key[:4] + "..." if len(api_key) > 4 else "***"
            
            try:
                # Add timeout to prevent hanging requests
                response = requests.post(
                    url + model, 
                    headers=headers, 
                    json={"messages": inputs},
                    timeout=REQUEST_TIMEOUT
                )
                
                # Handle successful response
                if response.status_code == 200:
                    # Mark this account as successful
                    self.mark_success(account_index)
                    
                    # Log success with timing information
                    elapsed = time.time() - start_time
                    if retries > 0:
                        log_warning(f"API call succeeded after {retries} retries in {elapsed:.2f}s using account {account_id}")
                    
                    return response.json()
                
                # Handle rate limiting (common status codes for rate limits)
                elif response.status_code in [429, 403, 503]:
                    error_msg = f"Rate limit detected for account {account_id}: {response.status_code} - {response.text}"
                    log_error(error_msg, account_id, api_key_prefix, response.status_code)
                    
                    # Mark this account as rate limited
                    self.mark_failure(account_index, is_rate_limit=True)
                
                # Handle authentication errors (likely bad API key)
                elif response.status_code in [401, 403]:
                    error_msg = f"Authentication error for account {account_id}: {response.status_code} - {response.text}"
                    log_error(error_msg, account_id, api_key_prefix, response.status_code)
                    
                    # Mark with higher penalty - this is likely a bad key
                    status = self.account_status[account_index]
                    status["consecutive_failures"] += 2  # Count as multiple failures
                    self.mark_failure(account_index)
                    self._update_health_score(account_index, -25)  # Larger health penalty
                
                # Handle other API errors
                else:
                    error_msg = f"API Error for account {account_id}: {response.status_code} - {response.text}"
                    log_error(error_msg, account_id, api_key_prefix, response.status_code)
                    
                    # Mark as a general failure
                    self.mark_failure(account_index)
            
            except requests.exceptions.Timeout:
                error_msg = f"Request timeout for account {account_id}"
                log_error(error_msg, account_id, api_key_prefix)
                self.mark_failure(account_index)
            
            except requests.exceptions.ConnectionError as e:
                error_msg = f"Connection error for account {account_id}: {str(e)}"
                log_error(error_msg, account_id, api_key_prefix)
                self.mark_failure(account_index)
                
                # Connection errors might be temporary network issues
                # Use a shorter backoff
                time.sleep(BACKOFF_BASE)
            
            except Exception as e:
                error_msg = f"Exception for account {account_id}: {str(e)}"
                log_error(error_msg, account_id, api_key_prefix)
                self.mark_failure(account_index)
            
            # Switch to the next account on failure - use smart selection
            self.switch_account()
            retries += 1
            
            # Implement smarter backoff - shorter for first retry, longer for subsequent
            if retries < RETRY_LIMIT:
                # Use a smaller backoff for the first retry to fail fast
                if retries == 1:
                    backoff_time = BACKOFF_BASE
                else:
                    backoff_time = BACKOFF_BASE * (2 ** (retries - 1))  # Exponential backoff
                
                time.sleep(backoff_time)

        # All retries failed
        elapsed = time.time() - start_time
        log_error(f"All API accounts failed after {elapsed:.2f}s and {retries} retries")
        return {"error": "All API accounts failed", "retry_after": 60, "accounts_tried": list(tried_accounts)}

# Example usage:
if __name__ == "__main__":
    ai_manager = AutoXAIManager()
    inputs = [
        {"role": "system", "content": "You are a helpful assistant"},
        {"role": "user", "content": "Tell me a joke"}
    ]
    output = ai_manager.run("@cf/meta/mistral-7b-instruct", inputs)
    print(output)
