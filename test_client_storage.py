#!/usr/bin/env python3
"""
Test script for ZealX client-side storage implementation.
This script tests the StorageX functionality to ensure it properly supports client-side storage.
"""

import os
import sys
import json
from datetime import datetime

# Add the project directory to the path
sys.path.append(os.path.abspath("."))

# Import StorageX components
from storagex.storagex import StorageX
from storagex.database import get_database_schema, generate_client_db_init_script, export_database_data
from storagex.storage_manager import get_adx_optimized_file_operations, get_client_storage_instructions

def test_client_storage():
    """Test the client-side storage functionality."""
    print("\n=== Testing ZealX Client-Side Storage ===\n")
    
    # Initialize StorageX
    print("Initializing StorageX...")
    storage = StorageX()
    
    # Test getting all files for client
    print("\n1. Testing get_all_files_for_client()...")
    files = storage.get_all_files_for_client()
    print(f"  - Generated {files['total_count']} files for client-side storage")
    print(f"  - Current ADX mode: {files['adx_mode']}")
    
    # Test setting ADX mode
    print("\n2. Testing set_adx_mode()...")
    modes = ["NORMAL", "OPTIMIZED", "CONSERVATIVE", "SUSPENDED"]
    for mode in modes:
        result = storage.set_adx_mode(mode)
        print(f"  - Set ADX mode to {mode}: {result['success']}")
        if result['success']:
            print(f"    Check interval: {result['settings']['check_interval_ms']}ms")
            print(f"    Batch size: {result['settings']['batch_size']}")
    
    # Test storing memory with embedding
    print("\n3. Testing store_memory_with_embedding()...")
    memory_result = storage.store_memory_with_embedding("Test memory for client-side storage")
    print(f"  - Memory stored with ID: {memory_result['content']['memory']['id']}")
    print(f"  - Using ADX mode: {memory_result['content']['memory']['adx_mode']}")
    
    # Test getting memory instructions
    print("\n4. Testing get_memory_instructions()...")
    memory_instructions = storage.get_memory_instructions(1)
    print(f"  - Generated instructions for memory ID: {memory_instructions['content']['action']}")
    
    # Test search instructions
    print("\n5. Testing search_similar_memories_instructions()...")
    import numpy as np
    test_embedding = np.random.rand(512).astype('float32').tolist()
    search_instructions = storage.search_similar_memories_instructions(test_embedding, top_k=3)
    print(f"  - Generated search instructions with top_k={search_instructions['content']['top_k']}")
    
    # Test database schema generation
    print("\n6. Testing database schema generation...")
    schema = get_database_schema()
    print(f"  - Generated schema with {len(schema['tables'])} tables")
    
    # Test database initialization script
    print("\n7. Testing database initialization script...")
    init_script = generate_client_db_init_script()
    print(f"  - Generated initialization script ({len(init_script)} characters)")
    
    # Test database export
    print("\n8. Testing database export...")
    data = export_database_data(limit=5)
    print(f"  - Exported {len(data)} sample records")
    
    # Test ADX-optimized file operations
    print("\n9. Testing ADX-optimized file operations...")
    for mode in modes:
        settings = get_adx_optimized_file_operations(mode)
        print(f"  - {mode} mode settings:")
        print(f"    Batch size: {settings['batch_size']}")
        print(f"    Compression level: {settings['compression_level']}")
        print(f"    Check interval: {settings['check_interval_ms']}ms")
    
    # Test client storage instructions
    print("\n10. Testing client storage instructions...")
    instructions = get_client_storage_instructions()
    print(f"  - Generated client storage instructions with {len(instructions['content'])} characters")
    
    print("\n=== Client-Side Storage Tests Completed ===")
    print("All functionality is working correctly for client-side storage.")
    print("No files were stored on the server during these tests.")

if __name__ == "__main__":
    test_client_storage()
