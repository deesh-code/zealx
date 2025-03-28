# fire_evolution_demo.py - Demo for Fire Evolution AI with FireLayers X++ architecture

import os
import sys
import time
from datetime import datetime
import json
import random
sys.path.append(os.path.abspath("/Users/momo/Desktop/x"))

from brainx.fire_evolution_ai import FireEvolutionAI
from autox_ai.logger import log_info, log_warning

def demo_fire_evolution():
    """Demonstrate the Fire Evolution AI capabilities."""
    print("\n🔥 Fire Evolution AI Demo 🔥")
    print("Advanced adaptive intelligence system for BrainX with FireLayers X++\n")
    
    # Initialize Fire Evolution AI
    user_id = f"demo_user_{int(time.time())}"
    fire_evolution = FireEvolutionAI(user_id, is_premium=True)
    
    print(f"Initialized Fire Evolution AI for user: {user_id}")
    print("Starting demonstration of key features...\n")
    
    # Demonstrate adaptive real-time learning
    print("1️⃣ Demonstrating Adaptive Real-Time Learning with FireLayers X++")
    demo_adaptive_learning(fire_evolution)
    
    # Demonstrate event-driven evolution
    print("\n2️⃣ Demonstrating Event-Driven Evolution")
    demo_event_driven_evolution(fire_evolution)
    
    # Demonstrate zero-latency execution
    print("\n3️⃣ Demonstrating Zero-Latency Execution")
    demo_zero_latency(fire_evolution)
    
    # Demonstrate fire-rotation API handling
    print("\n4️⃣ Demonstrating Fire-Rotation API Handling")
    demo_api_rotation(fire_evolution)
    
    # Demonstrate seamless cloud integration
    print("\n5️⃣ Demonstrating Seamless Cloud Integration")
    demo_cloud_integration(fire_evolution)
    
    print("\n✅ Fire Evolution AI demonstration completed!")
    print("BrainX is now ready to power ZealX with advanced intelligence capabilities.")

def demo_adaptive_learning(fire_evolution):
    """Demonstrate adaptive real-time learning capabilities."""
    # Process a series of user actions to demonstrate learning
    print("Processing user interactions through FireLayers X++...")
    
    # Simulate user actions
    actions = [
        {"action": "open_app", "app_name": "messaging", "timestamp": datetime.now().isoformat()},
        {"action": "send_message", "recipient": "John", "content": "Hello, how are you?", "timestamp": datetime.now().isoformat()},
        {"action": "receive_message", "sender": "John", "content": "I'm good, thanks!", "timestamp": datetime.now().isoformat()},
        {"action": "open_link", "url": "https://example.com/meeting", "timestamp": datetime.now().isoformat()},
    ]
    
    # Process each action
    for i, action_data in enumerate(actions):
        print(f"  Processing action {i+1}/{len(actions)}: {action_data['action']}")
        result = fire_evolution.process_event("user_action", action_data)
        
        # Display layer results
        print(f"  - Perception: Processed user action data")
        print(f"  - Comprehension: Analyzed context and patterns")
        print(f"  - Decision: Generated {len(result['layer_results'].get('decision', {}).get('potential_actions', []))} potential actions")
        
        # Show enhanced layer results if available
        if "enhanced_layer_results" in result:
            print(f"  - Meta-Learning: Adjusted learning parameters")
            print(f"  - Predictive Automation: Generated future action predictions")
        
        time.sleep(0.5)  # Brief pause for readability
    
    print("Adaptive learning demonstration complete.")
    print(f"Total events processed: {fire_evolution.stats['total_events']}")

def demo_event_driven_evolution(fire_evolution):
    """Demonstrate event-driven evolution capabilities."""
    print("Triggering micro-learning sessions based on events...")
    
    # Simulate system events to trigger evolution
    events = [
        {"system": "calendar", "event": "meeting_reminder", "details": "Team meeting in 15 minutes", "timestamp": datetime.now().isoformat()},
        {"system": "email", "event": "new_email", "sender": "boss@company.com", "subject": "Quarterly Report", "timestamp": datetime.now().isoformat()},
        {"system": "device", "event": "battery_low", "level": "15%", "timestamp": datetime.now().isoformat()},
    ]
    
    # Process each event
    for i, event_data in enumerate(events):
        print(f"  Processing system event {i+1}/{len(events)}: {event_data['event']}")
        fire_evolution.process_event("system_event", event_data)
        time.sleep(0.3)  # Brief pause for readability
    
    # Force trigger evolution for demonstration
    print("  Triggering evolution process...")
    if hasattr(fire_evolution, "_check_evolution_trigger"):
        # Access private method for demonstration purposes
        fire_evolution._check_evolution_trigger(force=True)
        print("  Evolution process completed.")
        if hasattr(fire_evolution, "evolution_stats"):
            print(f"  Total evolutions: {fire_evolution.evolution_stats.get('total_evolutions', 0)}")
    else:
        print("  Evolution method not available.")

def demo_zero_latency(fire_evolution):
    """Demonstrate zero-latency execution capabilities."""
    print("Testing response time with optimization...")
    
    # Measure execution time for a series of actions
    latencies = []
    
    # Simulate user actions that require quick responses
    quick_actions = [
        {"action": "tap_notification", "app": "messaging", "timestamp": datetime.now().isoformat()},
        {"action": "voice_command", "command": "set alarm for 7am", "timestamp": datetime.now().isoformat()},
        {"action": "gesture", "type": "swipe_up", "app": "camera", "timestamp": datetime.now().isoformat()},
    ]
    
    # Process each action and measure latency
    for i, action_data in enumerate(quick_actions):
        print(f"  Processing quick action {i+1}/{len(quick_actions)}: {action_data['action']}")
        
        # Measure execution time
        start_time = time.time()
        fire_evolution.process_event("user_action", action_data)
        latency = time.time() - start_time
        latencies.append(latency)
        
        print(f"  - Response time: {latency:.4f} seconds")
        time.sleep(0.2)  # Brief pause for readability
    
    # Calculate average latency
    avg_latency = sum(latencies) / len(latencies)
    print(f"Average response time: {avg_latency:.4f} seconds")
    
    # Check if latency is within threshold
    threshold = fire_evolution.evolution_config.get("zero_latency", {}).get("threshold", 0.5)
    if avg_latency <= threshold:
        print(f"✅ Zero-latency execution achieved (below threshold of {threshold} seconds)")
    else:
        print(f"⚠️ Response time above threshold ({threshold} seconds)")

def demo_api_rotation(fire_evolution):
    """Demonstrate fire-rotation API handling capabilities."""
    print("Demonstrating API rotation to prevent throttling...")
    
    # Get current API account
    current_account = fire_evolution.ai_manager.get_active_account()
    print(f"  Current API account: {current_account['account_id']}")
    
    # Simulate multiple API calls that would normally cause throttling
    print("  Simulating high-frequency API calls...")
    for i in range(5):
        print(f"  - API call {i+1}/5")
        
        # Force API rotation for demonstration
        if hasattr(fire_evolution, "_rotate_apis"):
            fire_evolution._rotate_apis()
            new_account = fire_evolution.ai_manager.get_active_account()
            print(f"  - Rotated to API account: {new_account['account_id']}")
        
        time.sleep(0.3)  # Brief pause for readability
    
    # Show rotation statistics
    if hasattr(fire_evolution, "evolution_stats"):
        print(f"Total API rotations: {fire_evolution.evolution_stats.get('api_rotations', 0)}")

def demo_cloud_integration(fire_evolution):
    """Demonstrate seamless cloud integration capabilities."""
    print("Testing cloud storage and synchronization...")
    
    # Simulate data generation that would be stored in cloud
    print("  Generating and storing user data...")
    
    # Create test data
    test_data = {
        "user_id": fire_evolution.user_id,
        "preferences": {
            "theme": "dark",
            "notifications": "enabled",
            "language": "english"
        },
        "usage_stats": {
            "daily_actions": random.randint(50, 200),
            "favorite_apps": ["messaging", "calendar", "notes"],
            "active_hours": [9, 10, 11, 14, 15, 16, 20, 21]
        },
        "timestamp": datetime.now().isoformat()
    }
    
    # Store test data
    data_path = os.path.join("storagex_data", "brainx_data", f"{fire_evolution.user_id}_preferences.json")
    try:
        with open(data_path, 'w') as f:
            json.dump(test_data, f, indent=2)
        print(f"  ✅ Data successfully stored at: {data_path}")
    except Exception as e:
        print(f"  ❌ Failed to store data: {str(e)}")
    
    # Trigger cloud sync
    print("  Triggering cloud synchronization...")
    if hasattr(fire_evolution, "_trigger_cloud_sync"):
        fire_evolution._trigger_cloud_sync()
        print("  ✅ Cloud synchronization initiated")
        
        # Show sync statistics
        if hasattr(fire_evolution, "evolution_stats"):
            print(f"  Total cloud syncs: {fire_evolution.evolution_stats.get('cloud_syncs', 0)}")
    else:
        print("  ❌ Cloud sync method not available")

if __name__ == "__main__":
    demo_fire_evolution()