import os
import sys
import time
from datetime import datetime

# Add project root to path
sys.path.append(os.path.abspath("/Users/momo/Desktop/x"))

# Import ZealX components
from zealx import ZealX, demo_zealx
from storagex.storagex import StorageX
from autox_ai.autox_core import AutoX
from autox_ai.autox_ai import AutoXAI
from autox_ai.adx_enhanced import ADXEnhanced
from brainx.fire_evolution_demo import demo_fire_evolution

def test_storage_system():
    """Test the StorageX component."""
    print("\n🔍 Testing StorageX System...")
    storage = StorageX()
    
    # Test storing and retrieving memory
    print("Testing memory storage and retrieval...")
    test_text = "This is a test memory for ZealX"
    storage.store_memory_with_embedding(test_text)
    
    # Test storing and retrieving structured data
    print("Testing structured data storage and retrieval...")
    test_data = {"test": "data", "timestamp": datetime.now().isoformat()}
    storage.store_structured_data("test_data.json", test_data)
    retrieved_data = storage.retrieve_structured_data("test_data.json")
    print(f"Retrieved data: {retrieved_data}")
    
    print("✅ StorageX tests completed")

def test_autox_ai():
    """Test the AutoX AI component."""
    print("\n🔍 Testing AutoX AI System...")
    autox_ai = AutoXAI()
    
    # Test processing a trigger
    print("Testing trigger processing...")
    task = autox_ai.process_trigger(
        app_id="whatsapp",
        trigger_type="message",
        trigger_data={
            "chat_id": "test_chat",
            "sender": "Test User",
            "text": "Hello ZealX, can you help me?"
        }
    )
    print(f"Generated task: {task}")
    
    print("✅ AutoX AI tests completed")

def test_adx():
    """Test the ADX (Adaptive Execution) component."""
    print("\n🔍 Testing ADX System...")
    
    # Create a mock AutoX instance
    class MockAutoX:
        def __init__(self):
            self.running = False
        
        def start(self):
            self.running = True
            print("MockAutoX: Started")
        
        def stop(self):
            self.running = False
            print("MockAutoX: Stopped")
    
    # Create ADX instance with mock AutoX
    mock_autox = MockAutoX()
    adx = ADXEnhanced(mock_autox)
    
    # Test ADX functionality
    print("Starting ADX...")
    adx.start()
    
    print("Simulating user activity...")
    adx.record_activity()
    
    print("Checking system resources...")
    adx.check_system_resources()
    
    print("Stopping ADX...")
    adx.stop()
    
    print("✅ ADX tests completed")

def main():
    """Main function to run ZealX system tests."""
    print("🔥 ZealX Automation System 🔥")
    print("A futuristic AI-powered automation system designed to act as a digital twin for users.\n")
    
    # Run component tests
    test_storage_system()
    test_autox_ai()
    test_adx()
    
    # Run full system demo
    print("\n🚀 Running ZealX System Demo...")
    demo_zealx()
    
    # Run BrainX Fire Evolution AI demo
    print("\n🚀 Running BrainX Fire Evolution AI Demo...")
    demo_fire_evolution()
    
    print("\n✅ All tests completed successfully!")
    print("ZealX system is ready for use with advanced BrainX intelligence.")

if __name__ == "__main__":
    main()
