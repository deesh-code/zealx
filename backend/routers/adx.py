# adx.py - Adaptive Execution Mode router for ZealX Backend

from fastapi import APIRouter, Depends, HTTPException, status, Request
from typing import List, Dict, Any, Optional, Union
from enum import Enum
import time
from datetime import datetime

from backend.core.config import settings
from backend.core.dependencies import get_current_active_user, get_zealx_instance
from backend.models.user import User

# Create router
router = APIRouter()

class ADXState(str, Enum):
    """ADX execution states."""
    NORMAL = "normal"  # Full functionality, regular checking intervals
    OPTIMIZED = "optimized"  # Slightly reduced activity to balance performance and battery
    CONSERVATIVE = "conservative"  # Significantly reduced activity to save battery
    SUSPENDED = "suspended"  # Minimal activity, only critical tasks are processed

class ADXManager:
    """Manages ADX state transitions and configurations."""
    
    def __init__(self, adx_instance):
        self.adx = adx_instance
        self.current_state = ADXState.NORMAL
    
    def get_current_state(self) -> ADXState:
        """Get current ADX state based on system conditions."""
        # Check if sleeping
        if self.adx.is_sleeping:
            return ADXState.SUSPENDED
        
        # Check power saving mode
        if hasattr(self.adx, "power_saving_mode") and self.adx.power_saving_mode:
            return ADXState.CONSERVATIVE
        
        # Check throttling mode
        if hasattr(self.adx, "throttling_mode") and self.adx.throttling_mode:
            return ADXState.OPTIMIZED
        
        # Default state
        return ADXState.NORMAL
    
    def set_state(self, state: ADXState) -> bool:
        """Set ADX state."""
        try:
            if state == ADXState.NORMAL:
                # Reset to normal operation
                if self.adx.is_sleeping:
                    self.adx.wake()
                
                # Reset power saving and throttling if available
                if hasattr(self.adx, "power_saving_mode"):
                    self.adx.power_saving_mode = False
                
                if hasattr(self.adx, "throttling_mode"):
                    self.adx.throttling_mode = False
                
                # Reset monitoring interval
                self.adx.monitoring_interval = settings.adx.monitoring_interval
            
            elif state == ADXState.OPTIMIZED:
                # Wake up if sleeping
                if self.adx.is_sleeping:
                    self.adx.wake()
                
                # Set throttling mode if available
                if hasattr(self.adx, "throttling_mode"):
                    self.adx.throttling_mode = True
                
                if hasattr(self.adx, "power_saving_mode"):
                    self.adx.power_saving_mode = False
                
                # Adjust monitoring interval
                self.adx.monitoring_interval = int(settings.adx.monitoring_interval * 1.5)
            
            elif state == ADXState.CONSERVATIVE:
                # Wake up if sleeping
                if self.adx.is_sleeping:
                    self.adx.wake()
                
                # Set power saving mode if available
                if hasattr(self.adx, "power_saving_mode"):
                    self.adx.power_saving_mode = True
                
                if hasattr(self.adx, "throttling_mode"):
                    self.adx.throttling_mode = True
                
                # Adjust monitoring interval
                self.adx.monitoring_interval = settings.adx.max_monitoring_interval
            
            elif state == ADXState.SUSPENDED:
                # Put to sleep if not already sleeping
                if not self.adx.is_sleeping:
                    self.adx.sleep()
            
            # Update current state
            self.current_state = state
            
            return True
        except Exception as e:
            print(f"Error setting ADX state: {str(e)}")
            return False
    
    def get_state_config(self, state: ADXState) -> Dict[str, Any]:
        """Get configuration for a specific ADX state."""
        if state == ADXState.NORMAL:
            return {
                "monitoring_interval": settings.adx.monitoring_interval,
                "idle_timeout": settings.adx.idle_timeout,
                "power_saving": False,
                "throttling": False,
                "description": "Full functionality, regular checking intervals"
            }
        elif state == ADXState.OPTIMIZED:
            return {
                "monitoring_interval": int(settings.adx.monitoring_interval * 1.5),
                "idle_timeout": int(settings.adx.idle_timeout * 0.8),
                "power_saving": False,
                "throttling": True,
                "description": "Slightly reduced activity to balance performance and battery"
            }
        elif state == ADXState.CONSERVATIVE:
            return {
                "monitoring_interval": settings.adx.max_monitoring_interval,
                "idle_timeout": int(settings.adx.idle_timeout * 0.5),
                "power_saving": True,
                "throttling": True,
                "description": "Significantly reduced activity to save battery"
            }
        elif state == ADXState.SUSPENDED:
            return {
                "monitoring_interval": settings.adx.max_monitoring_interval,
                "idle_timeout": 0,  # Immediate sleep
                "power_saving": True,
                "throttling": True,
                "description": "Minimal activity, only critical tasks are processed"
            }
        else:
            return {}

@router.get("/status")
async def get_adx_status(
    current_user: User = Depends(get_current_active_user),
    zealx = Depends(get_zealx_instance)
):
    """Get detailed ADX status."""
    # Create ADX manager
    adx_manager = ADXManager(zealx.adx)
    
    # Get current state
    current_state = adx_manager.get_current_state()
    
    # Get state config
    state_config = adx_manager.get_state_config(current_state)
    
    # Get ADX stats
    adx_stats = zealx.adx.stats.copy() if hasattr(zealx.adx, "stats") else {}
    
    # Add battery information if available
    battery_info = {}
    try:
        import psutil
        if hasattr(psutil, "sensors_battery"):
            battery = psutil.sensors_battery()
            if battery:
                battery_info = {
                    "percent": battery.percent,
                    "power_plugged": battery.power_plugged,
                    "secsleft": battery.secsleft
                }
    except ImportError:
        pass
    
    # Add system resource information
    system_resources = {}
    try:
        import psutil
        system_resources = {
            "cpu_percent": psutil.cpu_percent(),
            "memory_percent": psutil.virtual_memory().percent,
            "disk_percent": psutil.disk_usage('/').percent
        }
    except ImportError:
        pass
    
    return {
        "state": current_state,
        "config": state_config,
        "is_sleeping": zealx.adx.is_sleeping,
        "power_saving_mode": zealx.adx.power_saving_mode if hasattr(zealx.adx, "power_saving_mode") else False,
        "throttling_mode": zealx.adx.throttling_mode if hasattr(zealx.adx, "throttling_mode") else False,
        "monitoring_interval": zealx.adx.monitoring_interval,
        "last_activity": zealx.adx.last_activity.isoformat(),
        "stats": adx_stats,
        "battery": battery_info,
        "system_resources": system_resources
    }

@router.post("/set-state")
async def set_adx_state(
    state: ADXState,
    current_user: User = Depends(get_current_active_user),
    zealx = Depends(get_zealx_instance)
):
    """Set ADX state."""
    # Create ADX manager
    adx_manager = ADXManager(zealx.adx)
    
    # Set state
    success = adx_manager.set_state(state)
    
    if success:
        return {
            "status": "success",
            "message": f"ADX state set to {state}",
            "state": state,
            "config": adx_manager.get_state_config(state)
        }
    else:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to set ADX state"
        )

@router.post("/record-activity")
async def record_activity(
    current_user: User = Depends(get_current_active_user),
    zealx = Depends(get_zealx_instance)
):
    """Record user activity to prevent sleep mode."""
    zealx.adx.record_activity()
    
    return {
        "status": "success",
        "message": "Activity recorded",
        "last_activity": zealx.adx.last_activity.isoformat()
    }

@router.post("/check-resources")
async def check_system_resources(
    current_user: User = Depends(get_current_active_user),
    zealx = Depends(get_zealx_instance)
):
    """Check system resources and adjust execution accordingly."""
    result = zealx.adx.check_system_resources()
    
    # Get current state after resource check
    adx_manager = ADXManager(zealx.adx)
    current_state = adx_manager.get_current_state()
    
    return {
        "status": "success" if result else "error",
        "message": "System resources checked",
        "current_state": current_state,
        "is_sleeping": zealx.adx.is_sleeping,
        "power_saving_mode": zealx.adx.power_saving_mode if hasattr(zealx.adx, "power_saving_mode") else False,
        "throttling_mode": zealx.adx.throttling_mode if hasattr(zealx.adx, "throttling_mode") else False
    }

@router.get("/available-states")
async def get_available_states(
    current_user: User = Depends(get_current_active_user),
    zealx = Depends(get_zealx_instance)
):
    """Get available ADX states and their configurations."""
    # Create ADX manager
    adx_manager = ADXManager(zealx.adx)
    
    # Get configurations for all states
    states = {}
    for state in ADXState:
        states[state] = adx_manager.get_state_config(state)
    
    return {
        "current_state": adx_manager.get_current_state(),
        "available_states": states
    }
