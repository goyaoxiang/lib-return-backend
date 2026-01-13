from fastapi import APIRouter, Depends, HTTPException, status
from app.services.mqtt_service import mqtt_service
from app.services.auth import get_current_user
from app.models.user import User

router = APIRouter(prefix="/api/mqtt", tags=["MQTT"])

@router.post("/unlock/{return_box_id}")
async def unlock_return_box(
    return_box_id: int,
    current_user: User = Depends(get_current_user)
):
    """Send unlock command to return box via MQTT."""
    if not mqtt_service.is_running():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="MQTT service is not connected"
        )
    
    mqtt_service.send_unlock_command(return_box_id)
    return {"message": f"Unlock command sent to return box {return_box_id}"}

@router.get("/status")
async def get_mqtt_status():
    """Get MQTT service connection status."""
    return {
        "connected": mqtt_service.is_connected,
        "running": mqtt_service.is_running()
    }
