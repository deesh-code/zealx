# admin.py - Admin router for ZealX Backend

from fastapi import APIRouter, Depends, HTTPException, status, Request
from typing import List, Dict, Any, Optional
import time
import psutil
from datetime import datetime

from backend.core.config import settings
from backend.core.dependencies import get_current_active_user, get_storage_manager
from backend.models.user import User
from backend.models.api import SystemStatus, ADXStatus

# Create router
router = APIRouter()

# Admin access check
def check_admin_access(current_user: User = Depends(get_current_active_user)):
    """Check if user has admin access."""
    # In a real implementation, this would check if the user has admin role
    # For this demo, we'll just check if the user is premium
    if not current_user.is_premium:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    return current_user

@router.get("/system-status", response_model=SystemStatus)
async def get_system_status(
    request: Request,
    current_user: User = Depends(check_admin_access)
):
    """Get system status."""
    # Get system metrics
    cpu_percent = psutil.cpu_percent()
    memory_percent = psutil.virtual_memory().percent
    
    # Get ZealX instances
    zealx_instances = request.app.state.zealx_instances
    active_users = len(zealx_instances)
    
    # Get first ADX instance for demo
    adx_status = None
    if zealx_instances:
        first_user = next(iter(zealx_instances))
        zealx = zealx_instances[first_user]
        adx = zealx.adx
        
        adx_status = ADXStatus(
            is_sleeping=adx.is_sleeping,
            power_saving_mode=adx.power_saving_mode if hasattr(adx, "power_saving_mode") else False,
            throttling_mode=adx.throttling_mode if hasattr(adx, "throttling_mode") else False,
            monitoring_interval=adx.monitoring_interval,
            last_activity=adx.last_activity,
            stats=adx.stats
        )
    else:
        # Create default ADX status if no instances
        adx_status = ADXStatus(
            is_sleeping=False,
            power_saving_mode=False,
            throttling_mode=False,
            monitoring_interval=60,
            last_activity=datetime.now(),
            stats={}
        )
    
    # Calculate uptime (in seconds)
    # In a real implementation, this would be the actual server uptime
    uptime = 3600  # 1 hour for demo
    
    return SystemStatus(
        status="online",
        uptime=uptime,
        active_users=active_users,
        memory_usage=memory_percent,
        cpu_usage=cpu_percent,
        adx_status=adx_status
    )

@router.get("/active-users")
async def get_active_users(
    request: Request,
    current_user: User = Depends(check_admin_access)
):
    """Get active users."""
    # Get ZealX instances
    zealx_instances = request.app.state.zealx_instances
    
    # Build user list
    users = []
    for user_id, zealx in zealx_instances.items():
        users.append({
            "user_id": user_id,
            "zealx_running": zealx.running,
            "adx_sleeping": zealx.adx.is_sleeping,
            "last_activity": zealx.adx.last_activity.isoformat()
        })
    
    return {"active_users": users, "count": len(users)}

@router.get("/storage-stats")
async def get_storage_stats(
    current_user: User = Depends(check_admin_access),
    storage_manager = Depends(get_storage_manager)
):
    """Get storage statistics."""
    # Get storage stats
    stats = storage_manager.stats
    
    # Add current time
    stats["current_time"] = datetime.now().isoformat()
    
    return stats

@router.post("/maintenance")
async def run_maintenance(
    current_user: User = Depends(check_admin_access),
    storage_manager = Depends(get_storage_manager)
):
    """Run maintenance tasks."""
    # Run StorageX maintenance
    storage_manager._run_maintenance_if_needed()
    
    return {"status": "success", "message": "Maintenance tasks executed"}

@router.post("/cloudflare-accounts")
async def manage_cloudflare_accounts(
    action: str,
    account_data: Optional[Dict[str, Any]] = None,
    current_user: User = Depends(check_admin_access)
):
    """Manage Cloudflare accounts."""
    if action == "list":
        # List configured accounts
        accounts = []
        for i in range(len(settings.cloudflare.api_keys)):
            # Mask API keys for security
            masked_key = f"{settings.cloudflare.api_keys[i][:5]}...{settings.cloudflare.api_keys[i][-5:]}"
            accounts.append({
                "index": i,
                "account_id": settings.cloudflare.account_ids[i] if i < len(settings.cloudflare.account_ids) else None,
                "api_key": masked_key
            })
        
        return {"accounts": accounts, "count": len(accounts)}
    elif action == "add" and account_data:
        # In a real implementation, this would add a new account
        # For this demo, we'll just return success
        return {"status": "success", "message": "Account added successfully"}
    elif action == "remove" and account_data:
        # In a real implementation, this would remove an account
        # For this demo, we'll just return success
        return {"status": "success", "message": "Account removed successfully"}
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid action: {action}"
        )
