"""Fiware Entity Update Service for camera events."""

import requests
from datetime import datetime
from typing import Dict, Optional
from backend.shared import config, database
from backend.simulation.orion_helpers import OrionClient

FIWARE_OWNER = "week4_up1125093"

class CameraFiwareService:
    """Service for updating Fiware entities based on camera events."""

    def __init__(self):
        self.orion_client = OrionClient(
            base_url=config.ORION_URL,
            service_path=config.FIWARE_SERVICE_PATH,
            request_timeout=10
        )
        self.session = requests.Session()

    def update_traffic_flow(
        self, 
        camera_id: str, 
        density: float, 
        vehicle_count: int,
        timestamp: str
    ) -> bool:
        """Update TrafficFlowObserved entity with density and congestion level."""
        print(f"[FIWARE] Updating traffic flow for camera {camera_id}")
        camera_data = self._get_camera_data(camera_id)
        if not camera_data:
            print(f"[FIWARE ERROR] Camera {camera_id} not found in database")
            return False
        
        traffic_flow_id = camera_data.get('traffic_flow_entity_id')
        if not traffic_flow_id:
            print(f"[FIWARE ERROR] No traffic flow entity linked to camera {camera_id}")
            return False
        
        congestion_level = self._calculate_congestion_level(density)
        print(f"[FIWARE] Traffic entity {traffic_flow_id}, congestion: {congestion_level} (density={density})")
        
        success = True
        if traffic_flow_id:
            print(f"[FIWARE] Sending TrafficFlowObserved entity {traffic_flow_id}")
            entity = {
                "id": traffic_flow_id,
                "type": "TrafficFlowObserved",
                "owner": {"type": "Text", "value": FIWARE_OWNER},
                "dateObserved": {"type": "DateTime", "value": timestamp},
                "location": {
                    "type": "geo:json",
                    "value": {
                        "type": "Point",
                        "coordinates": [float(camera_data['location_lng']), float(camera_data['location_lat'])]
                    }
                },
                "density": {"type": "Number", "value": density},
                "intensity": {"type": "Number", "value": vehicle_count * 10},
                "congestionLevel": {"type": "Text", "value": congestion_level},
                "congested": {"type": "Boolean", "value": congestion_level in ["heavy", "severe"]}
            }
            
            success = self.orion_client.send_entity(self.session, entity, "update")
            print(f"[FIWARE] TrafficFlowObserved update {'successful' if success else 'failed'}")
        
        return success

    def create_double_parking_violation(
        self, 
        camera_id: str, 
        timestamp: str,
        license_plate: Optional[str] = None
    ) -> bool:
        """Create TrafficViolation entity for double parking incident."""
        print(f"[FIWARE] Creating double parking violation for camera {camera_id}")
        camera_data = self._get_camera_data(camera_id)
        if not camera_data:
            print(f"[FIWARE ERROR] Camera {camera_id} not found in database")
            return False
        
        violation_id = f"urn:ngsi-ld:TrafficViolation:DP-{camera_id}-{timestamp.replace(':', '').replace('-', '').replace('.', '')}"
        print(f"[FIWARE] Violation ID: {violation_id}, Plate: {license_plate}")
        
        entity = {
            "id": violation_id,
            "type": "TrafficViolation",
            "titleCode": {"type": "Text", "value": "double-parking"},
            "owner": {"type": "Text", "value": FIWARE_OWNER},
            "description": {"type": "Text", "value": f"Double parking violation detected by camera {camera_id}"},
            "observationDateTime": {"type": "DateTime", "value": timestamp},
            "equipmentId": {"type": "Text", "value": camera_id},
            "equipmentType": {"type": "Text", "value": "camera"},
            "location": {
                "type": "geo:json",
                "value": {
                    "type": "Point",
                    "coordinates": [float(camera_data['location_lng']), float(camera_data['location_lat'])]
                }
            },
            "paymentStatus": {"type": "Text", "value": "Unpaid"}
        }
        
        if license_plate:
            entity["licencePlateNumber"] = {"type": "Text", "value": license_plate}
        
        return self.orion_client.send_entity(self.session, entity, "create")

    def create_red_light_violation(
        self, 
        camera_id: str, 
        timestamp: str,
        license_plate: Optional[str] = None
    ) -> bool:
        """Create TrafficViolation entity for red light violation."""
        print(f"[FIWARE] Creating red light violation for camera {camera_id}")
        camera_data = self._get_camera_data(camera_id)
        if not camera_data:
            print(f"[FIWARE ERROR] Camera {camera_id} not found in database")
            return False
        
        violation_id = f"urn:ngsi-ld:TrafficViolation:RL-{camera_id}-{timestamp.replace(':', '').replace('-', '').replace('.', '')}"
        print(f"[FIWARE] Violation ID: {violation_id}, Plate: {license_plate}")
        
        entity = {
            "id": violation_id,
            "type": "TrafficViolation",
            "titleCode": {"type": "Text", "value": "red-light"},
            "owner": {"type": "Text", "value": FIWARE_OWNER},
            "description": {"type": "Text", "value": f"Red light violation detected by camera {camera_id}"},
            "observationDateTime": {"type": "DateTime", "value": timestamp},
            "equipmentId": {"type": "Text", "value": camera_id},
            "equipmentType": {"type": "Text", "value": "camera"},
            "location": {
                "type": "geo:json",
                "value": {
                    "type": "Point",
                    "coordinates": [float(camera_data['location_lng']), float(camera_data['location_lat'])]
                }
            },
            "paymentStatus": {"type": "Text", "value": "Unpaid"}
        }
        
        if license_plate:
            entity["licencePlateNumber"] = {"type": "Text", "value": license_plate}
        
        result = self.orion_client.send_entity(self.session, entity, "create")
        print(f"[FIWARE] Red light violation creation {'successful' if result else 'failed'}")
        return result

    def update_parking_status(
        self, 
        camera_id: str, 
        free_spots: int,
        timestamp: str
    ) -> bool:
        """Update OnStreetParking entity with spot count and availability status."""
        print(f"[FIWARE] Updating parking status for camera {camera_id}")
        camera_data = self._get_camera_data(camera_id)
        if not camera_data:
            print(f"[FIWARE ERROR] Camera {camera_id} not found in database")
            return False
        
        parking_entity_id = camera_data.get('onstreet_parking_entity_id')
        if not parking_entity_id:
            print(f"[FIWARE ERROR] No parking entity linked to camera {camera_id}")
            return False
        
        total_spots = self._get_total_parking_spots(parking_entity_id)
        occupied_spots = max(0, total_spots - free_spots)
        status = "open" if free_spots > 0 else "full"
        print(f"[FIWARE] Parking {parking_entity_id}: {free_spots}/{total_spots} free, status: {status}")
        
        entity = {
            "id": parking_entity_id,
            "type": "OnStreetParking",
            "owner": {"type": "Text", "value": FIWARE_OWNER},
            "observationDateTime": {"type": "DateTime", "value": timestamp},
            "availableSpotNumber": {"type": "Number", "value": free_spots},
            "occupiedSpotNumber": {"type": "Number", "value": occupied_spots},
            "status": {"type": "Text", "value": status},
            "location": {
                "type": "geo:json",
                "value": {
                    "type": "Point",
                    "coordinates": [float(camera_data['location_lng']), float(camera_data['location_lat'])]
                }
            }
        }
        
        result = self.orion_client.send_entity(self.session, entity, "update")
        print(f"[FIWARE] Parking status update {'successful' if result else 'failed'}")
        return result

    def _get_camera_data(self, camera_id: str) -> Optional[Dict]:
        """Get camera config and linked Fiware entity IDs from database."""
        query = """
            SELECT camera_id, location_lat, location_lng, road_segment_id,
                   traffic_flow_entity_id, onstreet_parking_entity_id
            FROM camera_devices
            WHERE camera_id = %s
        """
        results = database.fetch_all(query, (camera_id,))
        return results[0] if results else None

    def _get_total_parking_spots(self, parking_entity_id: str) -> int:
        """Get total parking spots from Orion, database, or default (10)."""
        entity = self.orion_client.get_entity(self.session, parking_entity_id)
        if entity and "totalSpotNumber" in entity:
            return entity["totalSpotNumber"].get("value", 10)
        
        query = "SELECT total_spots FROM parking_entities WHERE entity_id = %s"
        results = database.fetch_all(query, (parking_entity_id,))
        if results:
            return results[0].get('total_spots', 10)
        return 10

    def _calculate_congestion_level(self, density: float) -> str:
        """Map traffic density (vehicles/km) to congestion level: freeFlow/moderate/heavy/severe."""
        if density < 10:
            return "freeFlow"
        elif density < 25:
            return "moderate"
        elif density < 50:
            return "heavy"
        else:
            return "severe"


# Singleton instance
fiware_service = CameraFiwareService()
