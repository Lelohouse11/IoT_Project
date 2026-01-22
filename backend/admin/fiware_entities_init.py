"""
Service to initialize and ensure Fiware entities exist on startup.
Creates all required entities for cameras, parking, and traffic monitoring
with the same structure as simulation-generated entities.
"""

import time
import requests
from datetime import datetime, timezone
from backend.shared import database, config
from backend.simulation.orion_helpers import OrionClient

# Use same FIWARE owner as simulations
FIWARE_OWNER = "week4_up1125093"


def ensure_fiware_entities():
    """
    Initialize all required Fiware entities.
    Creates parking, traffic, and camera-related entities if they don't exist.
    """
    print("\n" + "=" * 60)
    print("Initializing Fiware Entities...")
    print("=" * 60)
    
    orion_client = OrionClient(
        base_url=config.ORION_URL,
        service_path=config.FIWARE_SERVICE_PATH,
        request_timeout=10
    )
    
    import requests
    session = requests.Session()
    
    try:
        print("\n[FIWARE INIT] Waiting for Orion Context Broker...")
        if not _wait_for_orion(orion_client, session, timeout=30):
            print("[FIWARE INIT ERROR] Could not connect to Orion. Entities may not be initialized.")
            return False
        
        print("[FIWARE INIT] Connected to Orion Context Broker")
        now_iso = datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')
        
        # Initialize entities in sequence
        print("\n[FIWARE INIT] [1/4] Initializing parking entities...")
        _init_parking_entities(orion_client, session, now_iso)
        
        print("\n[FIWARE INIT] [2/4] Initializing camera entities...")
        _init_camera_entities(orion_client, session, now_iso)
        
        print("\n[FIWARE INIT] [3/4] Initializing camera parking entities...")
        _init_camera_parking_entities(orion_client, session, now_iso)
        
        print("\n[FIWARE INIT] [4/4] Ensuring MQTT subscription...")
        _ensure_mqtt_subscription(session)
        
        print("\n" + "=" * 60)
        print("Fiware entities initialization completed!")
        print("=" * 60 + "\n")
        return True
        
    except Exception as e:
        print(f"[FIWARE INIT ERROR] {e}")
        import traceback
        traceback.print_exc()
        return False


def _wait_for_orion(orion_client, session, timeout=30, interval=2):
    """Wait for Orion to become available."""
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            orion_client.get_entity(session, "test-connection-entity")
            return True
        except Exception:
            time.sleep(interval)
    return False


def _init_parking_entities(orion_client, session, now_iso):
    """Create OnStreetParking entities in Fiware from database."""
    try:
        query = "SELECT entity_id, name, lat, lng, total_spots FROM parking_entities LIMIT 20"
        parking_entities = database.fetch_all(query)
        print(f"[FIWARE INIT] Found {len(parking_entities)} parking entities in database")
        
        for parking in parking_entities:
            entity = {
                "id": parking.get('entity_id'),
                "type": "OnStreetParking",
                "owner": {"type": "Text", "value": FIWARE_OWNER},
                "name": {"type": "Text", "value": parking.get('name', 'Parking Zone')},
                "streetName": {"type": "Text", "value": parking.get('name', 'Parking Zone')},
                "highwayType": {"type": "Text", "value": "residential"},
                "category": {"type": "StructuredValue", "value": ["public"]},
                "allowedVehicleType": {"type": "StructuredValue", "value": ["car"]},
                "totalSpotNumber": {"type": "Number", "value": parking.get('total_spots', 10)},
                "availableSpotNumber": {"type": "Number", "value": parking.get('total_spots', 10)},
                "occupiedSpotNumber": {"type": "Number", "value": 0},
                "status": {"type": "Text", "value": "open"},
                "observationDateTime": {"type": "DateTime", "value": now_iso},
                "location": {
                    "type": "geo:json",
                    "value": {
                        "type": "Point",
                        "coordinates": [parking.get('lng', 0), parking.get('lat', 0)]
                    }
                },
                "dataModel": {
                    "type": "Text",
                    "value": "https://smart-data-models.github.io/dataModel.Parking/OnStreetParking/schema.json"
                }
            }
            
            orion_client.send_entity(session, entity, "create")
        
        print(f"[FIWARE INIT] Processed {len(parking_entities)} parking entities")
        
    except Exception as e:
        print(f"[FIWARE INIT ERROR] Error initializing parking entities: {e}")


def _init_camera_entities(orion_client, session, now_iso):
    """Create TrafficFlowObserved entities for each camera."""
    try:
        query = """
            SELECT camera_id, location_lat, location_lng, traffic_flow_entity_id
            FROM camera_devices
            WHERE traffic_flow_entity_id IS NOT NULL
        """
        cameras = database.fetch_all(query)
        print(f"[FIWARE INIT] Found {len(cameras)} camera entities to initialize")
        
        for camera in cameras:
            camera_id = camera.get('camera_id')
            lat = float(camera.get('location_lat', 0))
            lng = float(camera.get('location_lng', 0))
            traffic_flow_id = camera.get('traffic_flow_entity_id')
            
            entity = {
                "id": traffic_flow_id,
                "type": "TrafficFlowObserved",
                "owner": {"type": "Text", "value": FIWARE_OWNER},
                "cameraId": {"type": "Text", "value": camera_id},
                "dateObserved": {"type": "DateTime", "value": now_iso},
                "density": {"type": "Number", "value": 0},
                "intensity": {"type": "Number", "value": 0},
                "congestionLevel": {"type": "Text", "value": "freeFlow"},
                "congested": {"type": "Boolean", "value": False},
                "location": {
                    "type": "geo:json",
                    "value": {
                        "type": "Point",
                        "coordinates": [lng, lat]
                    }
                }
            }
            
            if orion_client.send_entity(session, entity, "create"):
                print(f"[FIWARE INIT] Created TrafficFlowObserved entity for {camera_id}")
        
        print(f"[FIWARE INIT] Processed {len(cameras)} camera/traffic flow entities")
        
    except Exception as e:
        print(f"[FIWARE INIT ERROR] Error initializing camera entities: {e}")


def _init_camera_parking_entities(orion_client, session, now_iso):
    """Create OnStreetParking entities for cameras with parking monitoring."""
    try:
        query = """
            SELECT camera_id, location_lat, location_lng, onstreet_parking_entity_id
            FROM camera_devices
            WHERE onstreet_parking_entity_id IS NOT NULL
        """
        cameras = database.fetch_all(query)
        print(f"[FIWARE INIT] Found {len(cameras)} camera parking entities to initialize")
        
        for camera in cameras:
            camera_id = camera.get('camera_id')
            lat = float(camera.get('location_lat', 0))
            lng = float(camera.get('location_lng', 0))
            parking_entity_id = camera.get('onstreet_parking_entity_id')
            
            # Check if entity already exists
            existing_entity = orion_client.get_entity(session, parking_entity_id)
            if existing_entity:
                print(f"[FIWARE INIT] OnStreetParking entity {parking_entity_id} already exists, skipping")
                continue
            
            entity = {
                "id": parking_entity_id,
                "type": "OnStreetParking",
                "owner": {"type": "Text", "value": FIWARE_OWNER},
                "name": {"type": "Text", "value": f"Camera Parking {camera_id}"},
                "streetName": {"type": "Text", "value": f"Street {camera_id}"},
                "highwayType": {"type": "Text", "value": "residential"},
                "category": {"type": "StructuredValue", "value": ["public"]},
                "allowedVehicleType": {"type": "StructuredValue", "value": ["car"]},
                "totalSpotNumber": {"type": "Number", "value": 10},
                "availableSpotNumber": {"type": "Number", "value": 10},
                "occupiedSpotNumber": {"type": "Number", "value": 0},
                "status": {"type": "Text", "value": "open"},
                "observationDateTime": {"type": "DateTime", "value": now_iso},
                "location": {
                    "type": "geo:json",
                    "value": {
                        "type": "Point",
                        "coordinates": [lng, lat]
                    }
                },
                "dataModel": {
                    "type": "Text",
                    "value": "https://smart-data-models.github.io/dataModel.Parking/OnStreetParking/schema.json"
                }
            }
            
            if orion_client.send_entity(session, entity, "create"):
                print(f"[FIWARE INIT] Created OnStreetParking entity {parking_entity_id} for {camera_id}")
        
        print(f"[FIWARE INIT] Processed {len(cameras)} camera parking entities")
        
    except Exception as e:
        print(f"[FIWARE INIT ERROR] Error initializing camera parking entities: {e}")


def _ensure_mqtt_subscription(session):
    """Create Fiware subscription to publish entity updates to MQTT."""
    try:
        subscription = {
            "description": "Publish all smart city entities to MQTT",
            "subject": {
                "entities": [
                    {"idPattern": ".*", "type": "OnStreetParking"},
                    {"idPattern": ".*", "type": "TrafficFlowObserved"},
                    {"idPattern": ".*", "type": "TrafficViolation"},
                    {"idPattern": ".*", "type": "TrafficAccident"}
                ],
                "condition": {
                    "attrs": [],
                    "expression": {"q": "owner==week4_up1125093"}
                }
            },
            "notification": {
                "mqtt": {
                    "url": "mqtt://150.140.186.118:1883",
                    "topic": "orion_updates"
                },
                "attrs": []
            }
        }
        
        # Check if subscription already exists
        try:
            resp = session.get(
                f"{config.ORION_URL}/v2/subscriptions",
                headers={"FIWARE-ServicePath": config.FIWARE_SERVICE_PATH},
                timeout=10
            )
            for sub in resp.json():
                if sub.get("description") == subscription["description"]:
                    print(f"[FIWARE INIT] MQTT subscription already exists: {sub['id']}")
                    return True
        except Exception as e:
            print(f"[FIWARE INIT] Could not check existing subscriptions: {e}")
        
        # Create new subscription
        resp = session.post(
            f"{config.ORION_URL}/v2/subscriptions",
            json=subscription,
            headers={
                "Content-Type": "application/json",
                "FIWARE-ServicePath": config.FIWARE_SERVICE_PATH
            },
            timeout=10
        )
        
        if resp.status_code == 201:
            sub_id = resp.headers.get("Location", "").split("/")[-1]
            print(f"[FIWARE INIT] ✅ Created MQTT subscription: {sub_id}")
            print(f"[FIWARE INIT] Fiware will now publish entity updates to MQTT (orion_updates)")
            return True
        else:
            print(f"[FIWARE INIT ERROR] Failed to create MQTT subscription: {resp.status_code}")
            print(f"[FIWARE INIT ERROR] Response: {resp.text}")
            return False
            
    except Exception as e:
        print(f"[FIWARE INIT ERROR] MQTT subscription creation failed: {e}")
        import traceback
        traceback.print_exc()
        return False
