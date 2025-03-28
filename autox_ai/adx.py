# adx.py - Adaptive Execution System for ZealX

import time
import threading
from datetime import datetime, timedelta
import os
import json
import sys
sys.path.append(os.path.abspath("/Users/momo/Desktop/x"))

from autox_ai.logger import log_error

# Constants
IDLE_TIMEOUT = 300  # 5 minutes of inactivity before sleep mode
MONITORING_INTERVAL = 60  # Check system state every 60 seconds
MIN_MONITORING_INTERVAL = 5  # Minimum interval (seconds) for high activity
MAX_MONITORING_INTERVAL = 300  # Maximum interval (seconds) for low activity
ACTIVITY_THRESHOLD = 3  # Number of events to consider "active"
STATS_FILE = "adx_stats.json"

class ADX:
    """Adaptive Execution System that optimizes ZealX's performance by dynamically controlling resource usage."""
    
    def __init__(self, autox_instance):
        """Initialize ADX with an AutoX instance.
        
        Args:
            autox_instance: The AutoX instance to control
        """
        self.autox = autox_instance
        self.last_activity = datetime.now()
        self.is_sleeping = False
        self.monitoring_interval = MONITORING_INTERVAL
        self.running = False
        self.event_count = 0
        self.last_event_time = datetime.now()
        self.stats = {
            "sleep_count": 0,
            "wake_count": 0,
            "total_sleep_time": 0,
            "avg_monitoring_interval": MONITORING_INTERVAL,
            "last_updated": datetime.now().isoformat()
        }
        
        # Load previous stats if available
        self.load_stats()
    
    def load_stats(self):
        """Load ADX statistics from storage."""
        stats_path = os.path.join("storagex_data", STATS_FILE)
        if os.path.exists(stats_path):
            try:
                with open(stats_path, 'r') as f:
                    self.stats = json.load(f)
            except Exception as e:
                log_error(f"Failed to load ADX stats: {str(e)}")
    
    def save_stats(self):
        """Save ADX statistics to storage."""
        stats_path = os.path.join("storagex_data", STATS_FILE)
        self.stats["last_updated"] = datetime.now().isoformat()
        
        try:
            with open(stats_path, 'w') as f:
                json.dump(self.stats, f, indent=2)
        except Exception as e:
            log_error(f"Failed to save ADX stats: {str(e)}")
    
    def record_activity(self):
        """Record user activity to prevent sleep mode."""
        self.last_activity = datetime.now()
        self.event_count += 1
        self.last_event_time = datetime.now()
        
        # Wake up if sleeping
        if self.is_sleeping:
            self.wake()
    
    def sleep(self):
        """Put AutoX into sleep mode to save resources."""
        if not self.is_sleeping and self.autox.running:
            print(f"ADX: Putting AutoX into sleep mode due to inactivity ({IDLE_TIMEOUT} seconds)")
            self.autox.stop()
            self.is_sleeping = True
            self.stats["sleep_count"] += 1
            self.sleep_start_time = datetime.now()
            self.save_stats()
    
    def wake(self):
        """Wake AutoX from sleep mode."""
        if self.is_sleeping:
            print("ADX: Waking AutoX from sleep mode due to new activity")
            self.autox.start()
            self.is_sleeping = False
            self.stats["wake_count"] += 1
            
            # Calculate sleep duration
            sleep_duration = (datetime.now() - self.sleep_start_time).total_seconds()
            self.stats["total_sleep_time"] += sleep_duration
            self.save_stats()
    
    def adjust_monitoring_interval(self):
        """Dynamically adjust monitoring interval based on activity level."""
        # Calculate time since last event
        time_since_last_event = (datetime.now() - self.last_event_time).total_seconds()
        
        # If recent activity, decrease interval for more responsive monitoring
        if self.event_count >= ACTIVITY_THRESHOLD or time_since_last_event < 60:
            # More activity = faster monitoring
            self.monitoring_interval = max(MIN_MONITORING_INTERVAL, 
                                         self.monitoring_interval * 0.8)
        else:
            # Less activity = slower monitoring to save resources
            self.monitoring_interval = min(MAX_MONITORING_INTERVAL, 
                                          self.monitoring_interval * 1.2)
        
        # Update stats
        self.stats["avg_monitoring_interval"] = self.monitoring_interval
        
        # Reset event counter every adjustment
        self.event_count = 0
    
    def has_active_processes(self):
        """Check if there are any active processes that should prevent sleep mode.
        
        This prevents the edge case where ADX incorrectly pauses during active automation.
        Enhanced with better context awareness to prevent incorrect pausing.
        """
        # Check if there were any events in the last 2 minutes (increased from 1 minute)
        time_since_last_event = (datetime.now() - self.last_event_time).total_seconds()
        if time_since_last_event < 120:  # Increased from 60 seconds to 120 seconds
            return True
            
        # Check if there are pending tasks in AutoX
        if hasattr(self.autox, 'has_pending_tasks') and self.autox.has_pending_tasks():
            return True
            
        # Check if there are active listeners or triggers
        if hasattr(self.autox, 'has_active_listeners') and self.autox.has_active_listeners():
            return True
        
        # Check for scheduled tasks that will run soon
        if hasattr(self.autox, 'has_upcoming_tasks'):
            # If there are tasks scheduled to run in the next 5 minutes, don't sleep
            if self.autox.has_upcoming_tasks(minutes=5):
                return True
        
        # Check for active user sessions
        if hasattr(self.autox, 'has_active_user_session') and self.autox.has_active_user_session():
            return True
        
        # Check system load - don't sleep during high CPU/memory activity
        # as it might be processing something important
        try:
            import psutil
            cpu_percent = psutil.cpu_percent(interval=0.5)
            if cpu_percent > 30:  # If CPU usage is above 30%, consider system active
                return True
        except ImportError:
            # psutil not available, skip this check
            pass
            
        return False
    
    def monitor(self):
        """Monitor system state and control AutoX execution."""
        while self.running:
            # Check if system has been idle
            idle_time = (datetime.now() - self.last_activity).total_seconds()
            
            # Only sleep if system is idle AND there are no active processes
            if idle_time > IDLE_TIMEOUT and not self.is_sleeping and not self.has_active_processes():
                self.sleep()
            elif (idle_time <= IDLE_TIMEOUT or self.has_active_processes()) and self.is_sleeping:
                self.wake()
            
            # Adjust monitoring interval based on activity
            self.adjust_monitoring_interval()
            
            # Sleep for the current monitoring interval
            time.sleep(self.monitoring_interval)
    
    def start(self):
        """Start the ADX monitoring system."""
        if not self.running:
            self.running = True
            self.last_activity = datetime.now()
            
            # Start monitoring thread
            self.monitor_thread = threading.Thread(target=self.monitor)
            self.monitor_thread.daemon = True
            self.monitor_thread.start()
            
            print("ADX: Adaptive Execution System started")
    
    def stop(self):
        """Stop the ADX monitoring system."""
        if self.running:
            self.running = False
            
            # Wait for monitoring thread to finish
            if hasattr(self, 'monitor_thread') and self.monitor_thread.is_alive():
                self.monitor_thread.join(timeout=1.0)
            
            # Wake AutoX if it's sleeping
            if self.is_sleeping:
                self.wake()
            
            # Save final stats
            self.save_stats()
            
            print("ADX: Adaptive Execution System stopped")

# Example usage
if __name__ == "__main__":
    # This would normally be imported from autox_core
    class MockAutoX:
        def __init__(self):
            self.running = False
        
        def start(self):
            self.running = True
            print("MockAutoX: Started")
        
        def stop(self):
            self.running = False
            print("MockAutoX: Stopped")
    
    # Create mock AutoX instance
    mock_autox = MockAutoX()
    
    # Create ADX instance
    adx = ADX(mock_autox)
    
    # Start ADX and AutoX
    mock_autox.start()
    adx.start()
    
    # Simulate activity
    print("Simulating activity...")
    for i in range(5):
        adx.record_activity()
        time.sleep(1)
    
    # Wait for idle timeout
    print(f"Waiting for idle timeout ({IDLE_TIMEOUT} seconds)...")
    time.sleep(IDLE_TIMEOUT + 5)
    
    # Simulate new activity to wake up
    print("Simulating new activity...")
    adx.record_activity()
    
    # Stop ADX
    time.sleep(5)
    adx.stop()