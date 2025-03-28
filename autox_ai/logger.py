# logger.py - Handles logging for AutoX AI

import os
import json
from datetime import datetime, date

LOG_DIR = "storagex_data"
LOG_FILE = os.path.join(LOG_DIR, f"autox_logs_{datetime.now().strftime('%Y%m%d')}.json")
USAGE_FILE = os.path.join(LOG_DIR, f"usage_logs_{datetime.now().strftime('%Y%m%d')}.json")

os.makedirs(LOG_DIR, exist_ok=True)

def log_error(error_message, account_id=None, api_key_prefix=None, status_code=None):
    """
    Log API errors with detailed information for better debugging and monitoring.
    
    Args:
        error_message (str): The error message to log
        account_id (str, optional): The account ID that experienced the error
        api_key_prefix (str, optional): First few characters of the API key for identification
        status_code (int, optional): HTTP status code if applicable
    """
    timestamp = datetime.now().isoformat()
    
    log_entry = {
        "timestamp": timestamp,
        "type": "error",
        "message": error_message,
        "account_info": {
            "account_id": account_id,
            "api_key_prefix": api_key_prefix
        },
        "status_code": status_code
    }
    
    # Load existing logs if file exists
    logs = []
    if os.path.exists(LOG_FILE):
        try:
            with open(LOG_FILE, 'r') as f:
                logs = json.load(f)
        except json.JSONDecodeError:
            # Handle corrupted log file
            pass
    
    # Append new log entry
    logs.append(log_entry)
    
    # Write updated logs
    with open(LOG_FILE, 'w') as f:
        json.dump(logs, f, indent=2)
    
    return log_entry

def log_warning(warning_message, account_id=None, api_key_prefix=None, details=None):
    """
    Log warning messages with detailed information for monitoring.
    
    Args:
        warning_message (str): The warning message to log
        account_id (str, optional): The account ID related to the warning
        api_key_prefix (str, optional): First few characters of the API key for identification
        details (dict, optional): Additional details about the warning
    """
    timestamp = datetime.now().isoformat()
    
    log_entry = {
        "timestamp": timestamp,
        "type": "warning",
        "message": warning_message,
        "account_info": {
            "account_id": account_id,
            "api_key_prefix": api_key_prefix
        },
        "details": details
    }
    
    # Load existing logs if file exists
    logs = []
    if os.path.exists(LOG_FILE):
        try:
            with open(LOG_FILE, 'r') as f:
                logs = json.load(f)
        except json.JSONDecodeError:
            # Handle corrupted log file
            pass
    
    # Append new log entry
    logs.append(log_entry)
    
    # Write updated logs
    with open(LOG_FILE, 'w') as f:
        json.dump(logs, f, indent=2)
    
    return log_entry

def get_recent_errors(hours=24):
    """
    Retrieve recent errors from the log file.
    
    Args:
        hours (int): Number of hours to look back
        
    Returns:
        list: List of recent error log entries
    """
    if not os.path.exists(LOG_FILE):
        return []
    
    try:
        with open(LOG_FILE, 'r') as f:
            logs = json.load(f)
        
        # Filter logs by time
        cutoff_time = (datetime.now() - datetime.timedelta(hours=hours)).isoformat()
        recent_errors = [log for log in logs if log["type"] == "error" and log["timestamp"] >= cutoff_time]
        
        return recent_errors
    except Exception as e:
        print(f"Error reading logs: {str(e)}")
        return []