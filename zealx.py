# zealx.py - Main integration file for ZealX Automation System

import os
import json
import time
import threading
from datetime import datetime
import sys
sys.path.append(os.path.abspath("/Users/momo/Desktop/x"))

from autox_ai.autox_core import AutoX
from autox_ai.autox_ai import AutoXAI
from autox_ai.adx_enhanced import ADXEnhanced
from storagex.storagex import StorageX

class ZealX:
    """ZealX - Futuristic AI-powered automation system designed to act as a digital twin for users."""
    
    def __init__(self, user_id, is_premium=False):
        """Initialize ZealX with user information.
        
        Args:
            user_id (str): Unique identifier for the user
            is_premium (bool): Whether the user has premium access
        """
        print(f"Initializing ZealX for user {user_id}...")
        
        # Initialize core components
        self.autox = AutoX(user_id, is_premium)
        self.autox_ai = AutoXAI()
        self.storage = StorageX()
        self.adx = ADXEnhanced(self.autox)
        
        self.user_id = user_id
        self.is_premium = is_premium
        self.running = False
    
    def start(self):
        """Start the ZealX system."""
        if not self.running:
            print(f"Starting ZealX for user {self.user_id}...")
            
            # Start AutoX core
            self.autox.start()
            
            # Start ADX for resource management
            self.adx.start()
            
            self.running = True
            print(f"ZealX started successfully for user {self.user_id}")
            
            # Log startup
            self._log_event("system_start", {"timestamp": datetime.now().isoformat()})
    
    def stop(self):
        """Stop the ZealX system."""
        if self.running:
            print(f"Stopping ZealX for user {self.user_id}...")
            
            # Stop ADX first
            self.adx.stop()
            
            # Stop AutoX core
            self.autox.stop()
            
            self.running = False
            print(f"ZealX stopped successfully for user {self.user_id}")
            
            # Log shutdown
            self._log_event("system_stop", {"timestamp": datetime.now().isoformat()})
    
    def add_app(self, app_id):
        """Add an app to automate.
        
        Args:
            app_id (str): Identifier for the app to automate
            
        Returns:
            bool: True if successful, False otherwise
        """
        # Check if free user already has an app
        if not self.is_premium and len(self.autox.active_apps) >= 1:
            print(f"Free users can only automate one app. Upgrade to premium for more.")
            return False
        
        result = self.autox.add_app(app_id)
        
        if result:
            print(f"Added app {app_id} for automation")
            
            # Record activity in ADX
            self.adx.record_activity()
            
            # Log app addition
            self._log_event("app_added", {"app_id": app_id, "timestamp": datetime.now().isoformat()})
        
        return result
    
    def remove_app(self, app_id):
        """Remove an app from automation.
        
        Args:
            app_id (str): Identifier for the app to remove
            
        Returns:
            bool: True if successful, False otherwise
        """
        result = self.autox.remove_app(app_id)
        
        if result:
            print(f"Removed app {app_id} from automation")
            
            # Record activity in ADX
            self.adx.record_activity()
            
            # Log app removal
            self._log_event("app_removed", {"app_id": app_id, "timestamp": datetime.now().isoformat()})
        
        return result
    
    def trigger_event(self, app_id, event_type, event_data):
        """Trigger an event for processing.
        
        Args:
            app_id (str): Identifier for the app
            event_type (str): Type of event
            event_data (dict): Data associated with the event
            
        Returns:
            bool: True if event was triggered successfully
        """
        try:
            # Record activity in ADX
            self.adx.record_activity()
            
            # Trigger event in AutoX
            self.autox.trigger_event(app_id, event_type, event_data)
            
            # Log event
            self._log_event("event_triggered", {
                "app_id": app_id,
                "event_type": event_type,
                "timestamp": datetime.now().isoformat()
            })
            
            return True
        except Exception as e:
            print(f"Error triggering event: {str(e)}")
            return False
    
    def _log_event(self, event_type, event_data):
        """Log system events for monitoring.
        
        Args:
            event_type (str): Type of event
            event_data (dict): Data associated with the event
        """
        try:
            log_entry = {
                "event_type": event_type,
                "event_data": event_data,
                "user_id": self.user_id,
                "timestamp": datetime.now().isoformat()
            }
            
            # Store log in StorageX
            self.storage.store_structured_data(f"zealx_logs_{datetime.now().strftime('%Y%m%d')}.json", log_entry)
        except Exception as e:
            print(f"Error logging event: {str(e)}")

# Example usage
def demo_zealx():
    # Create ZealX instance for a free user
    zealx = ZealX(user_id="demo_user_123", is_premium=False)
    
    # Start ZealX
    zealx.start()
    
    # Add an app to automate
    zealx.add_app("whatsapp")
    
    # Simulate some events
    print("\nSimulating a WhatsApp message event...")
    zealx.trigger_event(
        app_id="whatsapp",
        event_type="message",
        event_data={
            "chat_id": "123456",
            "sender": "John Doe",
            "text": "Hello, can you help me with something?"
        }
    )
    
    # Wait for events to be processed
    time.sleep(2)
    
    print("\nSimulating a WhatsApp notification event...")
    zealx.trigger_event(
        app_id="whatsapp",
        event_type="notification",
        event_data={
            "notification_id": "notif_789",
            "title": "New message",
            "text": "You have 3 new messages"
        }
    )
    
    # Wait for events to be processed
    time.sleep(2)
    
    # Stop ZealX
    zealx.stop()

if __name__ == "__main__":
    print("🔥 ZealX Automation System 🔥")
    print("A futuristic AI-powered automation system designed to act as a digital twin for users.\n")
    
    demo_zealx()