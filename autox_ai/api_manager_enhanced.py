# api_manager_enhanced.py - Enhanced API management with health tracking and smart rotation

import requests
import random
import time
import math
import json
import os
from datetime import datetime, timedelta
from config import AUTOX_AI_ACCOUNTS, API_BASE_URL, RETRY_LIMIT, RATE_LIMIT_COOLDOWN, REQUEST_TIMEOUT, BACKOFF_BASE
from logger import log_error, log_warning, log_info

# Constants for enhanced health tracking
HEALTH_DECAY_RATE = 0.95  # How quickly health decays over time
MIN_HEALTH_FOR_PRIMARY = 50  # Minimum health score to be considered as primary account
HEALTH_CHECK_INTERVAL = 60 * 30  # Check account health every 30 minutes
MAX_CONSECUTIVE_FAILURES = 5  # Maximum consecutive failures before temporary blacklisting
BLACKLIST_DURATION = 30  # Minutes to blacklist an account after MAX_CONSECUTIVE_FAILURES
HEALTH_RECOVERY_RATE = 2  # Points recovered per successful call
HEALTH_PENALTY_RATE = 10  # Points deducted per failure
RESPONSE_TIME_WEIGHT = 0.3  # Weight for response time in health calculation

class EnhancedAPIManager:
    def __init__(self):
        self.accounts = AUTOX_AI_ACCOUNTS
        self.current_index = random.randint(0, len(self.accounts) - 1)  # Start from a random account
        
        # Enhanced account status tracking
        self.account_status = {}
        self.last_health_check = datetime.now()
        self.health_check_file = os.path.join("storagex_data", "api_health.json")
        
        # Initialize or load account status
        self._initialize_account_status()
        
        # Log initialization
        log_info(f"Enhanced API Manager initialized with {len(self.accounts)} accounts")
    
    def _initialize_account_status(self):
        """Initialize account status or load from storage"""
        # Try to load existing health data
        if os.path.exists(self.health_check_file):
            try:
                with open(self.health_check_file, 'r') as f:
                    saved_status = json.load(f)
                    
                # Convert string timestamps back to datetime objects
                for account_id, status in saved_status.items():
                    if "rate_limited_until" in status and status["rate_limited_until"]:
                        try:
                            status["rate_limited_until"] = datetime.fromisoformat(status["rate_limited_until"])
                        except (ValueError, TypeError):
                            status["rate_limited_until"] = None
                    
                    if "last_success" in status and status["last_success"]:
                        try:
                            status["last_success"] = datetime.fromisoformat(status["last_success"])
                        except (ValueError, TypeError):
                            status["last_success"] = None
                    
                    if "last_used" in status and status["last_used"]:
                        try:
                            status["last_used"] = datetime.fromisoformat(status["last_used"])
                        except (ValueError, TypeError):
                            status["last_used"] = None
                    
                    if "blacklisted_until" in status and status["blacklisted_until"]:
                        try:
                            status["blacklisted_until"] = datetime.fromisoformat(status["blacklisted_until"])
                        except (ValueError, TypeError):
                            status["blacklisted_until"] = None
                
                # Store the loaded status
                for i, account in enumerate(self.accounts):
                    account_id = account["account_id"]
                    if account_id in saved_status:
                        self.account_status[i] = saved_status[account_id]
                    else:
                        # Initialize new account
                        self.account_status[i] = self._create_default_status()
            except Exception as e:
                log_error(f"Error loading API health data: {str(e)}")
                # Initialize with defaults if loading fails
                self._initialize_default_status()
        else:
            # No saved data, initialize with defaults
            self._initialize_default_status()
    
    def _initialize_default_status(self):
        """Initialize all accounts with default status"""
        for i, account in enumerate(self.accounts):
            self.account_status[i] = self._create_default_status()
    
    def _create_default_status(self):
        """Create default status for a new account"""
        return {
            "failures": 0,
            "consecutive_failures": 0,
            "rate_limited_until": None,
            "blacklisted_until": None,
            "last_success": None,
            "total_requests": 0,
            "total_failures": 0,
            "health_score": 100,  # 100 = perfect health, 0 = completely unreliable
            "cooldown_multiplier": 1.0,  # Dynamic cooldown multiplier
            "last_used": None,  # Track when account was last used
            "avg_response_time": None,  # Track average response time
            "response_times": [],  # Store recent response times
            "error_types": {},  # Track types of errors
            "last_error": None,  # Last error message
            "success_streak": 0  # Track consecutive successes
        }
    
    def _save_account_status(self):
        """Save account status to persistent storage"""
        try:
            # Create a serializable copy of the status
            serializable_status = {}
            
            for i, status in self.account_status.items():
                account_id = self.accounts[i]["account_id"]
                # Create a copy to avoid modifying the original
                status_copy = status.copy()
                
                # Convert datetime objects to ISO format strings
                if "rate_limited_until" in status_copy and status_copy["rate_limited_until"]:
                    status_copy["rate_limited_until"] = status_copy["rate_limited_until"].isoformat()
                
                if "last_success" in status_copy and status_copy["last_success"]:
                    status_copy["last_success"] = status_copy["last_success"].isoformat()
                
                if "last_used" in status_copy and status_copy["last_used"]:
                    status_copy["last_used"] = status_copy["last_used"].isoformat()
                
                if "blacklisted_until" in status_copy and status_copy["blacklisted_until"]:
                    status_copy["blacklisted_until"] = status_copy["blacklisted_until"].isoformat()
                
                # Limit the size of response_times array
                if "response_times" in status_copy and len(status_copy["response_times"]) > 10:
                    status_copy["response_times"] = status_copy["response_times"][-10:]
                
                serializable_status[account_id] = status_copy
            
            # Ensure directory exists
            os.makedirs(os.path.dirname(self.health_check_file), exist_ok=True)
            
            # Save to file
            with open(self.health_check_file, 'w') as f:
                json.dump(serializable_status, f, indent=2)
                
            return True
        except Exception as e:
            log_error(f"Error saving API health data: {str(e)}")
            return False
    
    def get_active_account(self):
        """Get the currently active account"""
        return self.accounts[self.current_index]
    
    def get_account_status(self, index=None):
        """Get status for a specific account or all accounts"""
        if index is not None:
            return self.account_status[index]
        return self.account_status
    
    def is_account_available(self, index):
        """Check if an account is currently available (not rate limited or blacklisted)"""
        status = self.account_status[index]
        
        # Check if rate limited
        if status["rate_limited_until"] and status["rate_limited_until"] > datetime.now():
            return False
        
        # Check if blacklisted
        if status["blacklisted_until"] and status["blacklisted_until"] > datetime.now():
            return False
            
        return True
    
    def _update_health_score(self, index, change):
        """Update the health score of an account with decay over time"""
        status = self.account_status[index]
        
        # Apply time-based decay if last used
        if status["last_used"]:
            time_since_last_use = (datetime.now() - status["last_used"]).total_seconds() / 3600  # hours
            decay_factor = HEALTH_DECAY_RATE ** (time_since_last_use / 24)  # Decay per day
            status["health_score"] = status["health_score"] * decay_factor
        
        # Apply the change
        status["health_score"] = max(0, min(100, status["health_score"] + change))
    
    def _calculate_response_time_factor(self, index):
        """Calculate a factor based on response time compared to other accounts"""
        status = self.account_status[index]
        
        if not status["response_times"]:
            return 1.0  # Neutral factor if no data
        
        # Calculate average response time for this account
        avg_time = sum(status["response_times"]) / len(status["response_times"])
        
        # Get average response times for all accounts with data
        all_avg_times = []
        for i, s in self.account_status.items():
            if s["response_times"]:
                all_avg_times.append(sum(s["response_times"]) / len(s["response_times"]))
        
        if not all_avg_times:
            return 1.0  # Neutral factor if no data
        
        # Calculate global average
        global_avg = sum(all_avg_times) / len(all_avg_times)
        
        # Return a factor that rewards faster-than-average accounts
        if global_avg == 0:
            return 1.0
            
        return global_avg / max(0.1, avg_time)  # Avoid division by zero
    
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
        status["success_streak"] = 0  # Reset success streak
        
        # Track error type
        status["error_types"]["rate_limit"] = status["error_types"].get("rate_limit", 0) + 1
        status["last_error"] = "Rate limit exceeded"
        
        # Update health score (decrease more for rate limits)
        self._update_health_score(index, -HEALTH_PENALTY_RATE * 1.5)
        
        # Check if account should be blacklisted
        if status["consecutive_failures"] >= MAX_CONSECUTIVE_FAILURES:
            self._blacklist_account(index)
        
        # Log with dynamic cooldown information
        account = self.accounts[index]
        log_warning(f"Account {account['account_id']} rate limited for {dynamic_cooldown:.1f} minutes (health: {status['health_score']:.1f}%)")
        
        # Save status after significant change
        self._save_account_status()
    
    def _blacklist_account(self, index):
        """Temporarily blacklist an account due to excessive failures"""
        status = self.account_status[index]
        account = self.accounts[index]
        
        # Set blacklist duration
        status["blacklisted_until"] = datetime.now() + timedelta(minutes=BLACKLIST_DURATION)
        
        # Severely penalize health score
        self._update_health_score(index, -50)
        
        log_error(f"Account {account['account_id']} BLACKLISTED for {BLACKLIST_DURATION} minutes due to {status['consecutive_failures']} consecutive failures (health: {status['health_score']:.1f}%)")
    
    def mark_success(self, index, response_time=None):
        """Mark an account as having a successful API call"""
        status = self.account_status[index]
        status["last_success"] = datetime.now()
        status["last_used"] = datetime.now()
        status["failures"] = 0  # Reset consecutive failures
        status["consecutive_failures"] = 0  # Reset consecutive failures counter
        status["total_requests"] += 1
        status["success_streak"] += 1  # Increment success streak
        
        # Track response time
        if response_time:
            status["response_times"].append(response_time)
            # Keep only the last 10 response times
            if len(status["response_times"]) > 10:
                status["response_times"] = status["response_times"][-10:]
            status["avg_response_time"] = sum(status["response_times"]) / len(status["response_times"])
        
        # Gradually recover cooldown multiplier
        status["cooldown_multiplier"] = max(1.0, status["cooldown_multiplier"] * 0.8)
        
        # Calculate health improvement based on response time and success streak
        response_time_factor = self._calculate_response_time_factor(index)
        streak_bonus = min(5, status["success_streak"] / 2)  # Bonus for consecutive successes
        
        # Improve health score with each success
        health_improvement = HEALTH_RECOVERY_RATE * response_time_factor + streak_bonus
        self._update_health_score(index, health_improvement)
        
        # Clear blacklist if present
        if status["blacklisted_until"]:
            status["blacklisted_until"] = None
            log_info(f"Account {self.accounts[index]['account_id']} removed from blacklist due to successful call")
        
        # Periodically save status
        if status["success_streak"] % 5 == 0 or status["health_score"] >= 95:
            self._save_account_status()
    
    def mark_failure(self, index, is_rate_limit=False, error_type="general", error_message=None):
        """Mark an account as having a failed API call with enhanced error tracking"""
        status = self.account_status[index]
        status["failures"] += 1
        status["consecutive_failures"] += 1
        status["total_failures"] += 1
        status["last_used"] = datetime.now()
        status["success_streak"] = 0  # Reset success streak
        
        # Track error type
        status["error_types"][error_type] = status["error_types"].get(error_type, 0) + 1
        status["last_error"] = error_message or f"Error type: {error_type}"
        
        # Update health score (general failures impact less than rate limits)
        penalty = HEALTH_PENALTY_RATE
        if error_type == "auth":
            # Authentication errors are more severe
            penalty *= 2
        
        self._update_health_score(index, -penalty)
        
        if is_rate_limit:
            self.mark_rate_limited(index)
        elif status["consecutive_failures"] >= MAX_CONSECUTIVE_FAILURES:
            # After MAX_CONSECUTIVE_FAILURES consecutive failures that aren't rate limits, 
            # temporarily blacklist the account
            self._blacklist_account(index)
        elif status["consecutive_failures"] >= 3:
            # After 3 consecutive failures, apply a temporary cooldown
            cooldown_minutes = min(30, 5 * status["consecutive_failures"])
            status["rate_limited_until"] = datetime.now() + timedelta(minutes=cooldown_minutes)
            log_warning(f"Account {self.accounts[index]['account_id']} disabled for {cooldown_minutes} minutes due to {status['consecutive_failures']} consecutive failures")
        
        # Save status after significant change
        if status["consecutive_failures"] >= 2:
            self._save_account_status()
    
    def _run_health_check(self):
        """Periodically run health checks on all accounts"""
        # Check if it's time for a health check
        if (datetime.now() - self.last_health_check).total_seconds() < HEALTH_CHECK_INTERVAL:
            return
        
        log_info("Running API account health check...")
        self.last_health_check = datetime.now()
        
        # Check each account
        for i, account in enumerate(self.accounts):
            status = self.account_status[i]
            
            # Apply time-based health decay
            if status["last_used"]:
                time_since_last_use = (datetime.now() - status["last_used"]).total_seconds() / 3600  # hours
                if time_since_last_use > 24:
                    # Decay health for unused accounts
                    decay = (time_since_last_use / 24) * 5  # 5 points per day of non-use
                    self._update_health_score(i, -min(20, decay))  # Cap at 20 points
            
            # Clear expired rate limits and blacklists
            if status["rate_limited_until"] and status["rate_limited_until"] <= datetime.now():
                status["rate_limited_until"] = None
                log_info(f"Account {account['account_id']} rate limit expired")
            
            if status["blacklisted_until"] and status["blacklisted_until"] <= datetime.now():
                status["blacklisted_until"] = None
                log_info(f"Account {account['account_id']} removed from blacklist")
        
        # Save updated status
        self._save_account_status()
    
    def switch_account(self):
        """Switch to the next available account using enhanced health scores and smart selection"""
        # Run a health check if needed
        self._run_health_check()
        
        # Strategy 1: Find a healthy account that's available
        best_score = -1
        best_index = None
        
        # Find account with highest health score that's available
        for i, status in self.account_status.items():
            if self.is_account_available(i) and status["health_score"] > best_score:
                best_score = status["health_score"]
                best_index = i
        
        # If we found a healthy account, use it
        if best_index is not None and best_score > MIN_HEALTH_FOR_PRIMARY:
            self.current_index = best_index
            return self.get_active_account()
        
        # Strategy 2: Try least recently used available account
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
        
        # Strategy 3: If all accounts are rate limited or blacklisted, use the one with the earliest expiry
        earliest_expiry = None
        earliest_index = None
        
        for i, status in self.account_status.items():
            # Check rate limit expiry
            if status["rate_limited_until"]:
                if earliest_expiry is None or status["rate_limited_until"] < earliest_expiry:
                    earliest_expiry = status["rate_limited_until"]
                    earliest_index = i
            
            # Check blacklist expiry
            if status["blacklisted_until"]:
                if earliest_expiry is None or status["blacklisted_until"] < earliest_expiry:
                    earliest_expiry = status["blacklisted_until"]
                    earliest_index = i
        
        if earliest_index is not None:
            self.current_index = earliest_index
            log_warning(f"All accounts are unavailable. Using account {self.accounts[earliest_index]['account_id']} with earliest expiry at {earliest_expiry}")
        
        return self.get_active_account()

    def run(self, model, inputs):
        """Run an API call with enhanced error handling and account rotation"""
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
                request_start = time.time()
                response = requests.post(
                    url + model, 
                    headers=headers, 
                    json={"messages": inputs},
                    timeout=REQUEST_TIMEOUT
                )
                request_time = time.time() - request_start
                
                # Handle successful response
                if response.status_code == 200:
                    # Mark this account as successful with response time
                    self.mark_success(account_index, request_time)
                    
                    # Log success with timing information
                    elapsed = time.time() - start_time
                    if retries > 0:
                        log_warning(f"API call succeeded after {retries} retries in {elapsed:.2f}s using account {account_id}")
                    
                    return response.json()
                
                # Handle rate limiting (common status codes for rate limits)
                elif response.status_code in [429, 503]:
                    error_msg = f"Rate limit detected for account {account_id}: {response.status_code} - {response.text}"
                    log_error(error_msg, account_id, api_key_prefix, response.status_code)
                    
                    # Mark this account as rate limited
                    self.mark_failure(account_index, is_rate_limit=True, error_type="rate_limit", error_message=error_msg)
                
                # Handle authentication errors (likely bad API key)
                elif response.status_code in [401, 403]:
                    error_msg = f"Authentication error for account {account_id}: {response.status_code} - {response.text}"
                    log_error(error_msg, account_id, api_key_prefix, response.status_code)
                    
                    # Mark with higher penalty - this is likely a bad key
                    self.mark_failure(account_index, error_type="auth", error_message=error_msg)
                
                # Handle other API errors
                else:
                    error_msg = f"API Error for account {account_id}: {response.status_code} - {response.text}"
                    log_error(error_msg, account_id, api_key_prefix, response.status_code)
                    
                    # Mark as a general failure
                    self.mark_failure(account_index, error_type="api_error", error_message=error_msg)
            
            except requests.exceptions.Timeout:
                error_msg = f"Request timeout for account {account_id}"
                log_error(error_msg, account_id, api_key_prefix)
                self.mark_failure(account_index, error_type="timeout", error_message=error_msg)
            
            except requests.exceptions.ConnectionError as e:
                error_msg = f"Connection error for account {account_id}: {str(e)}"
                log_error(error_msg, account_id, api_key_prefix)
                self.mark_failure(account_index, error_type="connection", error_message=error_msg)
                
                # Connection errors might be temporary network issues
                # Use a shorter backoff
                time.sleep(BACKOFF_BASE)
            
            except Exception as e:
                error_msg = f"Exception for account {account_id}: {str(e)}"
                log_error(error_msg, account_id, api_key_prefix)
                self.mark_failure(account_index, error_type="unknown", error_message=error_msg)
            
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
    ai_manager = EnhancedAPIManager()
    inputs = [
        {"role": "system", "content": "You are a helpful assistant"},
        {"role": "user", "content": "Tell me a joke"}
    ]
    output = ai_manager.run("@cf/meta/mistral-7b-instruct", inputs)
    print(output)