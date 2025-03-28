import sqlite3
import json
import os
import time
import numpy as np
from datetime import datetime, timedelta

# Keep this as reference only, no actual files will be created
STORAGE_DIR = "storagex_data"
DB_PATH = os.path.join(STORAGE_DIR, "memory.db")

def init_db():
    """
    Generate database initialization instructions for client.
    No longer initializes a server-side database.
    
    Returns:
        dict: Database initialization instructions
    """
    return {
        "action": "init_db",
        "schema_version": 1,
        "timestamp": json.dumps({"$date": {"$numberLong": str(int(time.time() * 1000))}})
    }

def store_memory(text, vector):
    """
    Generate memory storage instructions for client.
    No longer stores in server-side SQLite.
    
    Returns:
        dict: Memory data for client-side storage
    """
    return {
        "action": "store_memory",
        "text": text,
        "vector": vector,
        "timestamp": json.dumps({"$date": {"$numberLong": str(int(time.time() * 1000))}})
    }

def fetch_recent_memory(limit=5):
    """
    Generate memory fetch instructions for client.
    No longer fetches from server-side SQLite.
    
    Returns:
        dict: Instructions for client to fetch recent memories
    """
    return {
        "action": "fetch_recent_memory",
        "limit": limit,
        "timestamp": json.dumps({"$date": {"$numberLong": str(int(time.time() * 1000))}})
    }

def get_database_schema():
    """
    Generate database schema for client-side storage.
    
    Returns:
        dict: Database schema for client-side storage
    """
    schema = {
        "tables": [
            {
                "name": "memory",
                "columns": [
                    {"name": "id", "type": "INTEGER", "primary_key": True, "autoincrement": True},
                    {"name": "text", "type": "TEXT"},
                    {"name": "vector", "type": "BLOB"},
                    {"name": "timestamp", "type": "DATETIME", "default": "CURRENT_TIMESTAMP"}
                ],
                "indices": [
                    {"name": "idx_memory_timestamp", "columns": ["timestamp"]}
                ]
            }
        ],
        "version": 1
    }
    return schema

def generate_client_db_init_script():
    """
    Generate SQLite initialization script for client-side storage.
    
    Returns:
        str: SQLite initialization script
    """
    script = """
    CREATE TABLE IF NOT EXISTS memory (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        text TEXT,
        vector BLOB,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
    );
    CREATE INDEX IF NOT EXISTS idx_memory_timestamp ON memory(timestamp);
    """
    return script

def export_database_data(limit=100):
    """
    Generate sample database data for client-side storage.
    No longer exports from server-side database.
    
    Args:
        limit (int): Maximum number of records to generate
        
    Returns:
        list: Sample database records for client-side storage
    """
    # Generate sample records
    records = []
    for i in range(min(10, limit)):  # Generate at most 10 sample records
        records.append({
            "id": i + 1,
            "text": f"Sample memory {i + 1}",
            "vector": np.random.rand(512).astype('float32').tolist(),
            "timestamp": (datetime.now() - timedelta(days=i)).isoformat()
        })
    
    return records
