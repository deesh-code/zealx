# adx_enhanced.py - Enhanced Adaptive Execution System for ZealX

import time
import threading
from datetime import datetime, timedelta
import os
import json
import sys
import psutil
sys.path.append(os.path.abspath("/Users/momo/Desktop/x"))

from autox_ai.logger import log_error

# Constants
IDLE_TIMEOUT = 300  # 5 minutes of inactivity before sleep mode
MONITORING_INTERVAL = 60  # Check system state every 60 seconds
MIN_MONITORING_INTERVAL = 5  # Minimum interval (seconds) for high activity
MAX_MONITORING_INTERVAL = 300  # Maximum interval (seconds) for low activity
ACTIVITY_THRESHOLD = 3  # Number of events to consider "active"
STATS_FILE = "adx_stats.json"
BATTERY_THRESHOLD = 20  # Battery percentage threshold for power saving mode
CPU_THRESHOLD = 80  # CPU usage threshold for throttling
MEMORY_THRESHOLD = 80  # Memory usage threshold for optimization

class ADXEnhanced:
    """Enhanced Adaptive Execution System that optimizes ZealX's performance by dynamically controlling resource usage."""
    
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
        self.power_saving_mode = False
        self.throttling_mode = False
        self.stats = {
            "sleep_count": 0,
            "wake_count": 0,
            "total_sleep_time": 0,
            "avg_monitoring_interval": MONITORING_INTERVAL,
            "power_saving_activations": 0,
            "throttling_activations": 0,
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
        
        # Adjust monitoring interval based on activity level
        self._adjust_monitoring_interval()
    
    def _adjust_monitoring_interval(self):
        """Dynamically adjust monitoring interval based on activity level."""
        # Calculate time since last event
        time_since_last_event = (datetime.now() - self.last_event_time).total_seconds()
        
        # If recent activity, decrease interval for more responsive monitoring
        if time_since_last_event < 60 and self.event_count > ACTIVITY_THRESHOLD:
            # More frequent monitoring during high activity
            new_interval = max(MIN_MONITORING_INTERVAL, self.monitoring_interval * 0.8)
        else:
            # Less frequent monitoring during low activity to save resources
            new_interval = min(MAX_MONITORING_INTERVAL, self.monitoring_interval * 1.2)
        
        # Update monitoring interval
        self.monitoring_interval = int(new_interval)
        
        # Update stats
        self.stats["avg_monitoring_interval"] = self.monitoring_interval
    
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
    
    def check_system_resources(self):
        """Check system resources and adjust execution accordingly."""
        try:
            # Check CPU usage
            cpu_percent = psutil.cpu_percent(interval=1)
            
            # Check memory usage
            memory_percent = psutil.virtual_memory().percent
            
            # Check battery if available
            battery_percent = 100  # Default to 100% if battery info not available
            if hasattr(psutil, 'sensors_battery'):
                battery = psutil.sensors_battery()
                if battery:
                    battery_percent = battery.percent
            
            # Log resource usage
            print(f"ADX: System resources - CPU: {cpu_percent}%, Memory: {memory_percent}%, Battery: {battery_percent}%")
            
            # Apply resource optimization strategies
            self._optimize_for_resources(cpu_percent, memory_percent, battery_percent)
            
            return True
        except Exception as e:
            log_error(f"Error checking system resources: {str(e)}")
            return False
    
    def _optimize_for_resources(self, cpu_percent, memory_percent, battery_percent):
        """Apply optimization strategies based on resource usage."""
        # Battery optimization
        if battery_percent <= BATTERY_THRESHOLD and not self.power_saving_mode:
            print(f"ADX: Activating power saving mode (Battery: {battery_percent}%)")
            self.power_saving_mode = True
            self.stats["power_saving_activations"] += 1
            self.monitoring_interval = MAX_MONITORING_INTERVAL  # Reduce monitoring frequency
            self.save_stats()
        elif battery_percent > BATTERY_THRESHOLD + 10 and self.power_saving_mode:
            print(f"ADX: Deactivating power saving mode (Battery: {battery_percent}%)")
            self.power_saving_mode = False
            self._adjust_monitoring_interval()  # Reset monitoring interval
        
        # CPU optimization
        if cpu_percent >= CPU_THRESHOLD and not self.throttling_mode:
            print(f"ADX: Activating CPU throttling mode (CPU: {cpu_percent}%)")
            self.throttling_mode = True
            self.stats["throttling_activations"] += 1
            self.save_stats()
        elif cpu_percent < CPU_THRESHOLD - 20 and self.throttling_mode:
            print(f"ADX: Deactivating CPU throttling mode (CPU: {cpu_percent}%)")
            self.throttling_mode = False
        
        # Memory optimization
        if memory_percent >= MEMORY_THRESHOLD:
            print(f"ADX: High memory usage detected (Memory: {memory_percent}%), optimizing...")
            # In a real implementation, we would trigger memory optimization
            # For example, clearing caches or reducing buffer sizes
    
    def monitor(self):
        """Monitor system state and adjust execution accordingly."""
        while self.running:
            try:
                # Check if system is idle
                idle_time = (datetime.now() - self.last_activity).total_seconds()
                
                if idle_time >= IDLE_TIMEOUT and not self.is_sleeping:
                    self.sleep()
                
                # Check system resources
                self.check_system_resources()
                
                # Reset event count periodically
                if (datetime.now() - self.last_event_time).total_seconds() > 300:  # 5 minutes
                    self.event_count = 0
                
                # Sleep for the monitoring interval
                # Use adaptive interval based on system state
                actual_interval = self.monitoring_interval
                if self.power_saving_mode:
                    actual_interval = MAX_MONITORING_INTERVAL  # Maximum interval in power saving mode
                elif self.throttling_mode:
                    actual_interval = int(self.monitoring_interval * 1.5)  # Increased interval in throttling mode
                
                time.sleep(actual_interval)
            except Exception as e:
                log_error(f"Error in ADX monitoring: {str(e)}")
                time.sleep(MONITORING_INTERVAL)  # Default interval on error
    
    def start(self):
        """Start the ADX monitoring system."""
        if not self.running:
            self.running = True
            
            # Start monitoring thread
            self.monitor_thread = threading.Thread(target=self.monitor)
            self.monitor_thread.daemon = True
            self.monitor_thread.start()
            
            # Start AutoX if not already running
            if not self.autox.running:
                self.autox.start()
            
            print("ADX: Enhanced Adaptive Execution System started")
    
    def stop(self):
        """Stop the ADX monitoring system."""
        if self.running:
            self.running = False
            
            # Wait for monitoring thread to finish
            if hasattr(self, 'monitor_thread') and self.monitor_thread.is_alive():
                self.monitor_thread.join(timeout=1.0)
            
            # Stop AutoX if running and in sleep mode
            if self.is_sleeping and self.autox.running:
                self.autox.stop()
            
            # Save final stats
            self.save_stats()
            
            print("ADX: Enhanced Adaptive Execution System stopped")

# Example usage
if __name__ == "__main__":
    # Create a mock AutoX instance for testing
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
    adx = ADXEnhanced(mock_autox)
    
    # Start ADX and AutoX
    print("Starting ADX...")
    adx.start()
    
    # Simulate some activity
    print("Simulating activity...")
    adx.record_activity()
    
    # Wait for a while
    time.sleep(5)
    
    # Simulate more activity
    print("Simulating more activity...")
    adx.record_activity()
    
    # Stop ADX
    print("Stopping ADX...")
    adx.stop()