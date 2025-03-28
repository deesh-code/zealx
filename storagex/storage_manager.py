import os
import json
from datetime import datetime, timedelta

# Constants - only used as reference for client implementations
STORAGE_DIR = "storagex_data"  # This is now a reference for client-side paths
MEMORY_RETENTION_DAYS = 7  # How long to keep memories by default

# ADX-aware file operations
def generate_file_content(filename, content, content_type="application/json"):
    """
    Generate file content for client-side storage.
    
    Args:
        filename (str): Name of the file
        content (dict or str): Content to store
        content_type (str): Content type of the file
        
    Returns:
        dict: File metadata and content for client-side storage
    """
    # Convert content to string if it's a dict
    if isinstance(content, dict) or isinstance(content, list):
        content_str = json.dumps(content, indent=2)
    else:
        content_str = str(content)
    
    # Generate file metadata
    file_data = {
        "filename": filename,
        "content": content_str,
        "timestamp": datetime.now().isoformat(),
        "content_type": content_type,
        "size": len(content_str)
    }
    
    return file_data

def store_file_data(filename, content):
    """
    Generate file data for client-side storage.
    No longer stores files on the server.
    
    Args:
        filename (str): Name of the file
        content (dict or str): Content to store
        
    Returns:
        dict: File metadata for client-side storage
    """
    return generate_file_content(filename, content)

def read_file_data(filename):
    """
    Generate instructions for client to read file data.
    
    Args:
        filename (str): Name of the file to read
        
    Returns:
        dict: File read instructions for client-side implementation
    """
    return {
        "action": "read_file",
        "filename": filename,
        "timestamp": datetime.now().isoformat()
    }

def cleanup_old_data(days=MEMORY_RETENTION_DAYS):
    """
    Generate cleanup instructions for client-side storage.
    
    Args:
        days (int): Number of days to keep data
        
    Returns:
        dict: Cleanup instructions for client-side implementation
    """
    return {
        "action": "cleanup",
        "retention_days": days,
        "timestamp": datetime.now().isoformat(),
        "cutoff_date": (datetime.now() - timedelta(days=days)).isoformat()
    }

def get_adx_optimized_file_operations(adx_mode):
    """
    Get ADX-optimized file operation settings.
    
    Args:
        adx_mode (str): ADX mode (NORMAL, OPTIMIZED, CONSERVATIVE, SUSPENDED)
        
    Returns:
        dict: ADX-optimized file operation settings
    """
    # Define ADX settings for file operations
    adx_settings = {
        "NORMAL": {
            "batch_size": 100,
            "compression_level": 0,  # No compression
            "check_interval_ms": 1000
        },
        "OPTIMIZED": {
            "batch_size": 50,
            "compression_level": 1,  # Light compression
            "check_interval_ms": 3000
        },
        "CONSERVATIVE": {
            "batch_size": 20,
            "compression_level": 6,  # Medium compression
            "check_interval_ms": 10000
        },
        "SUSPENDED": {
            "batch_size": 5,
            "compression_level": 9,  # Maximum compression
            "check_interval_ms": 30000
        }
    }
    
    # Return settings for the specified mode, or NORMAL if not found
    return adx_settings.get(adx_mode, adx_settings["NORMAL"])

def get_storage_stats():
    """
    Generate storage statistics for client-side storage.
    
    Returns:
        dict: Storage statistics for client-side implementation
    """
    return {
        "action": "get_storage_stats",
        "timestamp": datetime.now().isoformat()
    }

def get_client_storage_instructions():
    """
    Generate comprehensive instructions for client-side storage.
    
    Returns:
        dict: Client storage instructions
    """
    instructions = {
        "storage_dir": STORAGE_DIR,
        "retention_days": MEMORY_RETENTION_DAYS,
        "file_types": {
            "memory": {
                "extension": ".json",
                "content_type": "application/json",
                "description": "Memory data with embeddings"
            },
            "stats": {
                "extension": ".json",
                "content_type": "application/json",
                "description": "Statistics and metrics"
            },
            "database": {
                "extension": ".db",
                "content_type": "application/octet-stream",
                "description": "SQLite database"
            }
        },
        "adx_modes": {
            "NORMAL": {
                "description": "Full functionality, regular checking intervals",
                "recommended_for": "Plugged in or high battery"
            },
            "OPTIMIZED": {
                "description": "Slightly reduced activity to balance performance and battery",
                "recommended_for": "Normal usage"
            },
            "CONSERVATIVE": {
                "description": "Significantly reduced activity to save battery",
                "recommended_for": "Low battery"
            },
            "SUSPENDED": {
                "description": "Minimal activity, only critical tasks are processed",
                "recommended_for": "Very low battery or battery saver mode"
            }
        },
        "timestamp": datetime.now().isoformat()
    }
    
    return generate_file_content("client_storage_instructions.json", instructions)
