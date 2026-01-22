"""Camera Event Router for receiving and processing camera events."""

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from datetime import datetime
from backend.shared import database
from backend.admin.processing_service import processing_service
from backend.admin.camera_fiware_service import fiware_service

router = APIRouter(prefix="/api/camera", tags=["camera"])


class CameraEventMetadata(BaseModel):
    """Optional metadata attached to camera events."""
    bbox: Optional[Dict[str, float]] = Field(None, description="Bounding box coordinates {x, y, w, h}")
    zone_coordinates: Optional[list] = Field(None, description="Zone polygon coordinates")
    confidence: Optional[float] = Field(None, description="YOLO detection confidence")
    vehicle_count: Optional[int] = Field(None, description="Vehicle count from YOLO tracking")
    zone_name: Optional[str] = Field(None, description="Zone name for the event")
    frame_number: Optional[int] = Field(None, description="Frame number in video")
    class Config:
        extra = "allow"


class CameraEventRequest(BaseModel):
    """Request model for camera event submission."""
    camera_id: str = Field(..., description="Unique camera identifier (e.g., CAM-01)")
    timestamp: str = Field(..., description="Event timestamp in ISO 8601 format")
    event_type: str = Field(
        ..., 
        description="Event type: traffic_monitoring, double_parking, red_light_violation, parking_status"
    )
    image: str = Field(..., description="Base64-encoded image data")
    metadata: Optional[CameraEventMetadata] = Field(None, description="Additional event metadata")


class CameraEventResponse(BaseModel):
    """Response model for camera event processing."""
    success: bool
    event_id: Optional[int] = None
    message: str
    vlm_result: Optional[Dict[str, Any]] = None
    fiware_updated: bool = False


@router.post("/event", response_model=CameraEventResponse)
def receive_camera_event(event: CameraEventRequest):
    """Receive and process camera event: validate, store, analyze with VLM, update Fiware."""
    print(f"[CAMERA EVENT] Received event from camera {event.camera_id}, type: {event.event_type}")
    print(f"[CAMERA EVENT] Timestamp: {event.timestamp}")
    
    valid_event_types = [
        "traffic_monitoring", 
        "double_parking", 
        "red_light_violation", 
        "parking_status"
    ]
    if event.event_type not in valid_event_types:
        print(f"[CAMERA EVENT ERROR] Invalid event type: {event.event_type}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid event_type. Must be one of: {', '.join(valid_event_types)}"
        )
    
    print(f"[CAMERA EVENT] Validating camera {event.camera_id} in database...")
    camera_query = "SELECT camera_id FROM camera_devices WHERE camera_id = %s"
    camera_result = database.fetch_all(camera_query, (event.camera_id,))
    
    if not camera_result:
        print(f"[CAMERA EVENT ERROR] Camera {event.camera_id} not found in database")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Camera {event.camera_id} not found in system"
        )
    print(f"[CAMERA EVENT] Camera {event.camera_id} validated successfully")
    
    vlm_result = None
    fiware_updated = False
    metadata_dict = event.metadata.dict() if event.metadata else {}
    
    try:
        if event.event_type == "traffic_monitoring":
            print(f"[CAMERA EVENT] Processing traffic monitoring...")
            vlm_result = processing_service.process_traffic_monitoring(event.image, metadata_dict)
            print(f"[CAMERA EVENT] VLM Result: {vlm_result}")
            if "error" not in vlm_result:
                print(f"[CAMERA EVENT] Updating Fiware with traffic data: density={vlm_result['density']}, vehicles={vlm_result['vehicle_count']}")
                fiware_updated = fiware_service.update_traffic_flow(
                    camera_id=event.camera_id,
                    density=vlm_result["density"],
                    vehicle_count=vlm_result["vehicle_count"],
                    timestamp=event.timestamp
                )
                print(f"[CAMERA EVENT] Fiware update {'successful' if fiware_updated else 'failed'}")
        
        elif event.event_type == "double_parking":
            print(f"[CAMERA EVENT] Processing double parking violation...")
            vlm_result = processing_service.process_double_parking(event.image, metadata_dict)
            print(f"[CAMERA EVENT] VLM Result: {vlm_result}")
            if "error" not in vlm_result:
                print(f"[CAMERA EVENT] Creating double parking violation in Fiware, plate: {vlm_result.get('license_plate')}")
                fiware_updated = fiware_service.create_double_parking_violation(
                    camera_id=event.camera_id,
                    timestamp=event.timestamp,
                    license_plate=vlm_result.get("license_plate")
                )
                print(f"[CAMERA EVENT] Fiware update {'successful' if fiware_updated else 'failed'}")
        
        elif event.event_type == "red_light_violation":
            print(f"[CAMERA EVENT] Processing red light violation...")
            vlm_result = processing_service.process_red_light_violation(event.image, metadata_dict)
            print(f"[CAMERA EVENT] VLM Result: {vlm_result}")
            if "error" not in vlm_result:
                print(f"[CAMERA EVENT] Creating red light violation in Fiware, plate: {vlm_result.get('license_plate')}")
                fiware_updated = fiware_service.create_red_light_violation(
                    camera_id=event.camera_id,
                    timestamp=event.timestamp,
                    license_plate=vlm_result.get("license_plate")
                )
                print(f"[CAMERA EVENT] Fiware update {'successful' if fiware_updated else 'failed'}")
        
        elif event.event_type == "parking_status":
            print(f"[CAMERA EVENT] Processing parking status...")
            vlm_result = processing_service.process_parking_status(event.image, metadata_dict)
            print(f"[CAMERA EVENT] VLM Result: {vlm_result}")
            if "error" not in vlm_result:
                print(f"[CAMERA EVENT] Updating Fiware with parking status: free_spots={vlm_result['free_spots']}")
                fiware_updated = fiware_service.update_parking_status(
                    camera_id=event.camera_id,
                    free_spots=vlm_result["free_spots"],
                    timestamp=event.timestamp
                )
                print(f"[CAMERA EVENT] Fiware update {'successful' if fiware_updated else 'failed'}")
        
    except Exception as e:
        print(f"[CAMERA EVENT ERROR] Event processing failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Event processing failed: {str(e)}"
        )
    
    print(f"[CAMERA EVENT] Processing complete for camera {event.camera_id}, fiware_updated={fiware_updated}")
    return CameraEventResponse(
        success=fiware_updated,
        event_id=None,
        message="Event processed and sent to Fiware" if fiware_updated else "Event processing failed",
        vlm_result=vlm_result,
        fiware_updated=fiware_updated
    )


@router.get("/health")
def camera_health():
    """Service health status endpoint."""
    return {
        "status": "healthy",
        "service": "camera_event_processor",
        "timestamp": datetime.utcnow().isoformat()
    }
