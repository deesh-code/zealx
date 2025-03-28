# autox_core.py - Core automation engine for ZealX

import os
import json
import time
import threading
from datetime import datetime
import sys
sys.path.append(os.path.abspath("/Users/momo/Desktop/x"))

from autox_ai.api_manager import AutoXAIManager
from autox_ai.logger import log_error
from autox_ai.autox_ai import AutoXAI
from storagex.storage_manager import store_file_data, read_file_data
from storagex.database import store_memory, fetch_recent_memory
from storagex.storagex import StorageX

# Constants
AUTOMATION_DIR = "automation_files"
USER_CONFIG_FILE = "user_config.json"

# Ensure automation directory exists
os.makedirs(AUTOMATION_DIR, exist_ok=True)

class AutoX:
    """Core automation engine for ZealX, designed to interact with any app dynamically."""
    
    def __init__(self, user_id, is_premium=False):
        """Initialize AutoX with user information.
        
        Args:
            user_id (str): Unique identifier for the user
            is_premium (bool): Whether the user has premium access (multiple apps)
        """
        self.user_id = user_id
        self.is_premium = is_premium
        self.ai_manager = AutoXAIManager()
        self.autox_ai = AutoXAI()  # Initialize AutoX AI for decision-making
        self.storage = StorageX()  # Initialize StorageX for efficient data storage
        self.active_apps = []
        self.event_listeners = {}
        self.running = False
        self.event_queue = []
        self.lock = threading.Lock()
        
        # Load user configuration
        self.load_user_config()
    
    def load_user_config(self):
        """Load user configuration from storage."""
        config_path = os.path.join(AUTOMATION_DIR, f"{self.user_id}_{USER_CONFIG_FILE}")
        
        if os.path.exists(config_path):
            with open(config_path, 'r') as f:
                config = json.load(f)
                self.active_apps = config.get('active_apps', [])
                self.is_premium = config.get('is_premium', self.is_premium)
        else:
            # Create default config
            self.save_user_config()
    
    def save_user_config(self):
        """Save user configuration to storage."""
        config = {
            'user_id': self.user_id,
            'is_premium': self.is_premium,
            'active_apps': self.active_apps,
            'last_updated': datetime.now().isoformat()
        }
        
        config_path = os.path.join(AUTOMATION_DIR, f"{self.user_id}_{USER_CONFIG_FILE}")
        with open(config_path, 'w') as f:
            json.dump(config, f, indent=2)
    
    def add_app(self, app_id):
        """Add an app to the active apps list.
        
        Args:
            app_id (str): Identifier for the app to automate
            
        Returns:
            bool: True if successful, False otherwise
        """
        # Check if free user already has an app
        if not self.is_premium and len(self.active_apps) >= 1:
            return False
        
        # Add app if not already active
        if app_id not in self.active_apps:
            self.active_apps.append(app_id)
            self.save_user_config()
            
            # Fetch app automation files
            self.fetch_app_automation(app_id)
            return True
        
        return False
    
    def remove_app(self, app_id):
        """Remove an app from the active apps list.
        
        Args:
            app_id (str): Identifier for the app to remove
            
        Returns:
            bool: True if successful, False otherwise
        """
        if app_id in self.active_apps:
            self.active_apps.remove(app_id)
            self.save_user_config()
            return True
        return False
    
    def fetch_app_automation(self, app_id):
        """Fetch app-specific automation files from backend.
        
        Args:
            app_id (str): Identifier for the app
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # In a real implementation, this would make an API call to fetch
            # app-specific automation files from the backend
            # For now, we'll simulate this with a local file
            
            # Create app directory if it doesn't exist
            app_dir = os.path.join(AUTOMATION_DIR, app_id)
            os.makedirs(app_dir, exist_ok=True)
            
            # Create a placeholder automation file
            automation_file = os.path.join(app_dir, "automation.json")
            if not os.path.exists(automation_file):
                default_automation = {
                    "app_id": app_id,
                    "events": ["notification", "message", "ui_change"],
                    "actions": ["reply", "click", "swipe", "type"],
                    "last_updated": datetime.now().isoformat()
                }
                
                with open(automation_file, 'w') as f:
                    json.dump(default_automation, f, indent=2)
            
            return True
        except Exception as e:
            log_error(f"Failed to fetch automation for app {app_id}: {str(e)}", self.user_id)
            return False
    
    def register_event_listener(self, app_id, event_type, callback):
        """Register an event listener for a specific app and event type.
        
        Args:
            app_id (str): Identifier for the app
            event_type (str): Type of event to listen for
            callback (function): Function to call when event occurs
        """
        if app_id not in self.event_listeners:
            self.event_listeners[app_id] = {}
        
        if event_type not in self.event_listeners[app_id]:
            self.event_listeners[app_id][event_type] = []
        
        self.event_listeners[app_id][event_type].append(callback)
    
    def trigger_event(self, app_id, event_type, event_data):
        """Trigger an event for a specific app.
        
        Args:
            app_id (str): Identifier for the app
            event_type (str): Type of event
            event_data (dict): Data associated with the event
        """
        # Add event to queue for processing
        with self.lock:
            self.event_queue.append({
                "app_id": app_id,
                "event_type": event_type,
                "event_data": event_data,
                "timestamp": datetime.now().isoformat()
            })
    
    def process_events(self):
        """Process events in the queue."""
        while self.running:
            # Get events from queue
            events_to_process = []
            with self.lock:
                if self.event_queue:
                    events_to_process = self.event_queue.copy()
                    self.event_queue = []
            
            # Process each event
            for event in events_to_process:
                app_id = event["app_id"]
                event_type = event["event_type"]
                event_data = event["event_data"]
                
                # Check if we have listeners for this app and event
                if app_id in self.event_listeners and event_type in self.event_listeners[app_id]:
                    for callback in self.event_listeners[app_id][event_type]:
                        try:
                            callback(event_data)
                        except Exception as e:
                            log_error(f"Error in event callback: {str(e)}", self.user_id)
                
                # Generate and execute task based on event
                self.generate_task(app_id, event_type, event_data)
            
            # Sleep to prevent high CPU usage
            time.sleep(0.1)
    
    def generate_task(self, app_id, event_type, event_data):
        """Generate a task based on an event using AutoX AI.
        
        Args:
            app_id (str): Identifier for the app
            event_type (str): Type of event
            event_data (dict): Data associated with the event
            
        Returns:
            dict: Task to execute
        """
        # Use AutoX AI to generate an intelligent task based on the event
        task = self.autox_ai.process_trigger(app_id, event_type, event_data)
        
        # If we generated a task, execute it
        if task:
            self.execute_task(task)
            
            # Store task in memory for learning with proper embedding
            # Convert task to JSON string for storage
            task_json = json.dumps(task)
            
            # In a real implementation, we would generate a proper embedding
            # For now, we'll use a random embedding as a placeholder
            embedding = np.random.rand(512).astype('float32').tolist()
            
            # Store in StorageX for efficient retrieval
            self.storage.store_memory_with_embedding(task_json, embedding)
        
        return task
    
    def execute_task(self, task):
        """Execute a task.
        
        Args:
            task (dict): Task to execute
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            action = task.get("action")
            app_id = task.get("app_id")
            data = task.get("data", {})
            
            # In a real implementation, this would execute the task on the device
            # For now, we'll just log it
            print(f"Executing task: {action} on {app_id} with data {data}")
            
            # Store task execution in storage
            store_file_data(f"{app_id}_tasks.json", {
                "task": task,
                "executed_at": datetime.now().isoformat(),
                "status": "success"
            })
            
            return True
        except Exception as e:
            log_error(f"Failed to execute task: {str(e)}", self.user_id)
            return False
    
    def start(self):
        """Start the AutoX engine."""
        if not self.running:
            self.running = True
            
            # Start event processing thread
            self.event_thread = threading.Thread(target=self.process_events)
            self.event_thread.daemon = True
            self.event_thread.start()
            
            print(f"AutoX started for user {self.user_id}")
    
    def stop(self):
        """Stop the AutoX engine."""
        if self.running:
            self.running = False
            
            # Wait for event thread to finish
            if hasattr(self, 'event_thread') and self.event_thread.is_alive():
                self.event_thread.join(timeout=1.0)
            
            print(f"AutoX stopped for user {self.user_id}")

# Example usage
if __name__ == "__main__":
    # Create AutoX instance for a free user
    autox = AutoX(user_id="test_user_123", is_premium=False)
    
    # Add an app to automate
    autox.add_app("whatsapp")
    
    # Start the AutoX engine
    autox.start()
    
    # Simulate some events
    autox.trigger_event("whatsapp", "message", {"chat_id": "123", "text": "Hello"})
    
    # Wait for events to be processed
    time.sleep(2)
    
    # Stop the AutoX engine
    autox.stop()