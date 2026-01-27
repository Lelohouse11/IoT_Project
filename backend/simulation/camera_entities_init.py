"""Initialization script to seed camera-related Fiware entities in Orion."""

import argparse
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

import requests

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.simulation.orion_helpers import OrionClient
from backend.shared import database
from backend.shared import config

# Orion / FIWARE settings
ORION_BASE_URL = config.ORION_URL
FIWARE_SERVICE_PATH = config.FIWARE_SERVICE_PATH
FIWARE_OWNER = "week4_up1125093"
REQUEST_TIMEOUT = 5

ORION = OrionClient(
    base_url=ORION_BASE_URL,
    service_path=FIWARE_SERVICE_PATH,
    request_timeout=REQUEST_TIMEOUT,
)


@dataclass
class CameraDevice:
    """Representation of a camera device with location and linked entities."""
    camera_id: str
    lat: float
    lng: float
    road_segment_id: str
    street_name: str = ""


def _build_traffic_flow_entity(camera: CameraDevice, now_iso: str) -> Dict[str, Dict[str, Any]]:
    """Build TrafficFlowObserved entity for camera location."""
    entity_id = camera.road_segment_id.replace("SEG-", "")
    return {
        "id": f"urn:ngsi-ld:TrafficFlowObserved:{entity_id}",
        "type": "TrafficFlowObserved",
        "owner": {"type": "Text", "value": FIWARE_OWNER},
        "name": {"type": "Text", "value": f"Traffic Flow {entity_id}"},
        "streetName": {"type": "Text", "value": camera.street_name or f"Street {entity_id}"},
        "dateObserved": {"type": "DateTime", "value": now_iso},
        "location": {
            "type": "geo:json",
            "value": {
                "type": "Point",
                "coordinates": [camera.lng, camera.lat]
            }
        },
        "intensity": {"type": "Number", "value": 0},
        "averageVehicleSpeed": {"type": "Number", "value": 0},
        "occupancy": {"type": "Number", "value": 0},
        "density": {"type": "Number", "value": 0},
        "congestionLevel": {"type": "Text", "value": "freeFlow"},
        "congested": {"type": "Boolean", "value": False},
        "dataModel": {
            "type": "Text",
            "value": "https://smart-data-models.github.io/dataModel.Transportation/TrafficFlowObserved/schema.json"
        },
    }


def _build_traffic_entity(camera: CameraDevice, now_iso: str) -> Dict[str, Dict[str, Any]]:
    """Build Traffic entity for camera location."""
    entity_id = camera.road_segment_id.replace("SEG-", "")
    return {
        "id": f"urn:ngsi-ld:Traffic:{entity_id}",
        "type": "Traffic",
        "owner": {"type": "Text", "value": FIWARE_OWNER},
        "dateObserved": {"type": "DateTime", "value": now_iso},
        "location": {
            "type": "geo:json",
            "value": {
                "type": "Point",
                "coordinates": [camera.lng, camera.lat]
            }
        },
        "density": {"type": "Number", "value": 0},
        "dataModel": {
            "type": "Text",
            "value": "https://smart-data-models.github.io/dataModel.Transportation/Traffic/schema.json"
        },
    }


def _build_parking_entity(camera: CameraDevice, now_iso: str) -> Dict[str, Dict[str, Any]]:
    """Build OnStreetParking entity for camera location (if applicable)."""
    entity_id = camera.road_segment_id.replace("SEG-", "")
    return {
        "id": f"urn:ngsi-ld:OnStreetParking:{entity_id}",
        "type": "OnStreetParking",
        "owner": {"type": "Text", "value": FIWARE_OWNER},
        "name": {"type": "Text", "value": f"Parking Zone {entity_id}"},
        "streetName": {"type": "Text", "value": camera.street_name or f"Street {entity_id}"},
        "dateModified": {"type": "DateTime", "value": now_iso},
        "location": {
            "type": "geo:json",
            "value": {
                "type": "Point",
                "coordinates": [camera.lng, camera.lat]
            }
        },
        "totalSpotNumber": {"type": "Number", "value": 10},
        "availableSpotNumber": {"type": "Number", "value": 10},
        "occupiedSpotNumber": {"type": "Number", "value": 0},
        "status": {"type": "Text", "value": "open"},
        "dataModel": {
            "type": "Text",
            "value": "https://smart-data-models.github.io/dataModel.Parking/OnStreetParking/schema.json"
        },
    }


def _get_cameras_from_db() -> List[CameraDevice]:
    """Fetch camera devices from database."""
    query = """
        SELECT camera_id, location_lat, location_lng, road_segment_id,
               traffic_flow_entity_id, onstreet_parking_entity_id
        FROM camera_devices
    """
    results = database.fetch_all(query)
    
    cameras = []
    for row in results:
        cameras.append(CameraDevice(
            camera_id=row['camera_id'],
            lat=float(row['location_lat']),
            lng=float(row['location_lng']),
            road_segment_id=row['road_segment_id'],
            street_name=f"Vrachnaiika Street {row['camera_id']}"
        ))
    
    return cameras


def seed_camera_entities(cameras: List[CameraDevice]) -> None:
    """Create Fiware entities for all cameras."""
    if not cameras:
        print("[warn] no cameras found in database")
        return

    now_iso = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    
    with requests.Session() as session:
        for camera in cameras:
            print(f"\n[info] Processing camera {camera.camera_id}")
            
            # Create TrafficFlowObserved entity
            traffic_flow_entity = _build_traffic_flow_entity(camera, now_iso)
            if ORION.send_entity(session, traffic_flow_entity, "create"):
                print(f"[create] {traffic_flow_entity['id']}")
            
            # Create Traffic entity
            traffic_entity = _build_traffic_entity(camera, now_iso)
            if ORION.send_entity(session, traffic_entity, "create"):
                print(f"[create] {traffic_entity['id']}")
            
            # Check if camera has parking monitoring (CAM-VRACH-02)
            if "02" in camera.camera_id:
                parking_entity = _build_parking_entity(camera, now_iso)
                if ORION.send_entity(session, parking_entity, "create"):
                    print(f"[create] {parking_entity['id']}")
                
                # Update parking_entities table for dashboard
                try:
                    query = """
                        INSERT INTO parking_entities (entity_id, name, lat, lng, total_spots, url)
                        VALUES (%s, %s, %s, %s, %s, %s)
                        ON DUPLICATE KEY UPDATE
                            name = VALUES(name),
                            lat = VALUES(lat),
                            lng = VALUES(lng),
                            total_spots = VALUES(total_spots)
                    """
                    database.execute_query(
                        query,
                        (
                            parking_entity["id"],
                            parking_entity["name"]["value"],
                            camera.lat,
                            camera.lng,
                            10,
                            ""
                        )
                    )
                    print(f"[info] persisted {parking_entity['id']} to parking_entities table")
                except Exception as exc:
                    print(f"[warn] failed to persist parking entity to db: {exc}")
            
            # Update traffic_entities table for dashboard
            try:
                query = """
                    INSERT INTO traffic_entities (entity_id, name, lat, lng)
                    VALUES (%s, %s, %s, %s)
                    ON DUPLICATE KEY UPDATE
                        name = VALUES(name),
                        lat = VALUES(lat),
                        lng = VALUES(lng)
                """
                database.execute_query(
                    query,
                    (
                        traffic_flow_entity["id"],
                        traffic_flow_entity["name"]["value"],
                        camera.lat,
                        camera.lng
                    )
                )
                print(f"[info] persisted {traffic_flow_entity['id']} to traffic_entities table")
            except Exception as exc:
                print(f"[warn] failed to persist traffic entity to db: {exc}")


def main() -> None:
    """Main entry point for camera entities initialization."""
    parser = argparse.ArgumentParser(
        description="Initialize Fiware entities for camera devices"
    )
    args = parser.parse_args()

    print("[info] Fetching cameras from database...")
    cameras = _get_cameras_from_db()
    print(f"[info] Found {len(cameras)} camera(s)")
    
    print("[info] Creating Fiware entities...")
    seed_camera_entities(cameras)
    print("[info] Camera entity initialization complete")


if __name__ == "__main__":
    main()
