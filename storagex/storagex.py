import os
import json
import numpy as np
import sys
sys.path.append(os.path.abspath("/Users/momo/Desktop/x"))

from datetime import datetime, timedelta
from storagex.database import get_database_schema, generate_client_db_init_script
from storagex.storage_manager import generate_file_content

# Constants - only used as reference for client implementations
STORAGE_DIR = "storagex_data"  # This is now a reference for client-side paths
MEMORY_RETENTION_DAYS = 7  # How long to keep memories by default
MAX_VECTOR_DIMENSION = 512  # Default vector dimension for embeddings
MAX_CACHE_SIZE = 100  # Maximum number of items to keep in memory cache

# ADX operation modes
ADX_MODES = {
    "NORMAL": {
        "description": "Full functionality, regular checking intervals",
        "check_interval_ms": 1000,
        "batch_size": 100
    },
    "OPTIMIZED": {
        "description": "Slightly reduced activity to balance performance and battery",
        "check_interval_ms": 3000,
        "batch_size": 50
    },
    "CONSERVATIVE": {
        "description": "Significantly reduced activity to save battery",
        "check_interval_ms": 10000,
        "batch_size": 20
    },
    "SUSPENDED": {
        "description": "Minimal activity, only critical tasks are processed",
        "check_interval_ms": 30000,
        "batch_size": 5
    }
}

class StorageX:
    """AI-Powered Storage & Retrieval System for ZealX - Client-side implementation."""
    
    def __init__(self):
        """Initialize StorageX for client-side operation."""
        # Statistics for optimization
        self.stats = {
            "total_memories": 0,
            "total_searches": 0,
            "cache_hits": 0,
            "last_cleanup": datetime.now().isoformat(),
            "adx_mode": "NORMAL"  # Default ADX mode
        }
        
        # In-memory cache for frequently accessed data (temporary, for demo only)
        self.memory_cache = {}
        self.cache_access_count = {}
    
    def get_stats(self):
        """
        Generate statistics for client-side storage.
        
        Returns:
            dict: Statistics for client-side storage
        """
        self.stats["last_updated"] = datetime.now().isoformat()
        return generate_file_content("storagex_stats.json", self.stats)
    
    def get_maintenance_instructions(self):
        """
        Generate maintenance instructions for client-side storage.
        
        Returns:
            dict: Maintenance instructions for client-side storage
        """
        maintenance = {
            "action": "maintenance",
            "retention_days": MEMORY_RETENTION_DAYS,
            "max_cache_size": MAX_CACHE_SIZE,
            "timestamp": datetime.now().isoformat(),
            "adx_settings": ADX_MODES[self.stats["adx_mode"]]
        }
        
        return generate_file_content("maintenance_instructions.json", maintenance)
    
    def store_memory_with_embedding(self, text, embedding=None):
        """
        Generate memory data with embedding for client-side storage.
        
        Args:
            text (str): Text to store
            embedding (list, optional): Vector embedding for the text
            
        Returns:
            dict: Memory data for client-side storage
        """
        # Generate a random embedding if none provided
        if embedding is None:
            embedding = np.random.rand(MAX_VECTOR_DIMENSION).astype('float32').tolist()
        
        # Update statistics
        self.stats["total_memories"] += 1
        stats_file = self.get_stats()
        
        # Create memory data for client-side storage
        memory_data = {
            "text": text,
            "embedding": embedding,
            "timestamp": datetime.now().isoformat(),
            "id": self.stats["total_memories"],
            "adx_mode": self.stats["adx_mode"]
        }
        
        # Return memory data and any maintenance reports
        result = {
            "memory": memory_data,
            "stats": stats_file["content"],
            "adx_settings": ADX_MODES[self.stats["adx_mode"]]
        }
        
        return generate_file_content(f"memory_{self.stats['total_memories']}.json", result)
    
    def search_similar_memories_instructions(self, query_embedding, top_k=5):
        """
        Generate instructions for client to search similar memories.
        
        Args:
            query_embedding (list): Vector embedding to search for
            top_k (int): Number of results to return
            
        Returns:
            dict: Search instructions for client-side implementation
        """
        # Update statistics
        self.stats["total_searches"] += 1
        
        # Create search instructions
        search_instructions = {
            "action": "search_similar_memories",
            "query_embedding": query_embedding,
            "top_k": top_k,
            "timestamp": datetime.now().isoformat(),
            "adx_settings": ADX_MODES[self.stats["adx_mode"]]
        }
        
        return generate_file_content("search_instructions.json", search_instructions)
    
    def get_memory_instructions(self, memory_id):
        """
        Generate instructions for client to get memory by ID.
        
        Args:
            memory_id (int): ID of the memory to retrieve
            
        Returns:
            dict: Memory retrieval instructions for client-side implementation
        """
        # Update statistics
        self.stats["cache_hits"] += 1
        
        # Create memory retrieval instructions
        retrieval_instructions = {
            "action": "get_memory",
            "memory_id": memory_id,
            "timestamp": datetime.now().isoformat(),
            "adx_settings": ADX_MODES[self.stats["adx_mode"]]
        }
        
        return generate_file_content(f"get_memory_{memory_id}.json", retrieval_instructions)
    
    def get_cleanup_instructions(self):
        """
        Generate cleanup instructions for client-side storage.
        
        Returns:
            dict: Cleanup instructions for client-side implementation
        """
        # Create cleanup instructions
        cleanup_instructions = {
            "action": "cleanup",
            "retention_days": MEMORY_RETENTION_DAYS,
            "max_cache_size": MAX_CACHE_SIZE,
            "timestamp": datetime.now().isoformat(),
            "adx_settings": ADX_MODES[self.stats["adx_mode"]]
        }
        
        # Update statistics
        self.stats["last_cleanup"] = datetime.now().isoformat()
        
        return generate_file_content("cleanup_instructions.json", cleanup_instructions)
    
    def set_adx_mode(self, mode):
        """
        Set the ADX mode for StorageX operations.
        
        Args:
            mode (str): ADX mode (NORMAL, OPTIMIZED, CONSERVATIVE, SUSPENDED)
            
        Returns:
            dict: Updated ADX settings
        """
        if mode in ADX_MODES:
            self.stats["adx_mode"] = mode
            
            # Update statistics
            stats_file = self.get_stats()
            
            return {
                "success": True,
                "adx_mode": mode,
                "settings": ADX_MODES[mode],
                "stats": stats_file["content"]
            }
        else:
            return {
                "success": False,
                "error": f"Invalid ADX mode: {mode}",
                "valid_modes": list(ADX_MODES.keys())
            }
    
    def get_all_files_for_client(self):
        """
        Generate a list of all StorageX files for client-side storage.
        
        Returns:
            dict: List of files and their metadata for client-side storage
        """
        files = []
        
        # Add stats file
        stats_file = self.get_stats()
        files.append(stats_file)
        
        # Add database schema
        schema = get_database_schema()
        schema_file = generate_file_content("database_schema.json", schema)
        files.append(schema_file)
        
        # Add database initialization script
        init_script = generate_client_db_init_script()
        init_script_file = generate_file_content("db_init_script.sql", init_script, "text/plain")
        files.append(init_script_file)
        
        # Add ADX settings
        adx_settings_file = generate_file_content("adx_settings.json", ADX_MODES)
        files.append(adx_settings_file)
        
        # Add maintenance instructions
        maintenance_file = self.get_maintenance_instructions()
        files.append(maintenance_file)
        
        # For demo purposes, generate some sample memory files
        for i in range(1, 5):
            memory_data = {
                "text": f"Sample memory {i}",
                "embedding": np.random.rand(MAX_VECTOR_DIMENSION).astype('float32').tolist(),
                "timestamp": datetime.now().isoformat(),
                "id": i,
                "adx_mode": self.stats["adx_mode"]
            }
            memory_file = generate_file_content(f"memory_{i}.json", memory_data)
            files.append(memory_file)
        
        return {
            "files": files,
            "total_count": len(files),
            "timestamp": datetime.now().isoformat(),
            "adx_mode": self.stats["adx_mode"],
            "adx_settings": ADX_MODES[self.stats["adx_mode"]]
        }

# Example usage
if __name__ == "__main__":
    # Create StorageX instance
    storage = StorageX()
    
    # Get all files for client
    files = storage.get_all_files_for_client()
    print(f"Generated {files['total_count']} files for client-side storage")
    
    # Set ADX mode
    storage.set_adx_mode("OPTIMIZED")
    print(f"Set ADX mode to OPTIMIZED with settings: {ADX_MODES['OPTIMIZED']}")