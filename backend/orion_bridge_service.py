"""HTTP bridge service that receives Orion notifications and persists them to InfluxDB."""

import json
import logging
import sys
import time
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

import httpx
from fastapi import FastAPI, HTTPException
from dateutil.parser import isoparse
from influxdb_client import InfluxDBClient, Point, WritePrecision
from influxdb_client.client.write_api import SYNCHRONOUS

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend import config

# Logging setup
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration
ORION_URL = config.ORION_URL
FIWARE_SERVICE = config.FIWARE_SERVICE
FIWARE_SERVICE_PATH = config.FIWARE_SERVICE_PATH
ORION_CALLBACK_URL = config.ORION_CALLBACK_URL
SUBSCRIPTION_ID = "orion-bridge-notifications"
SUBSCRIPTION_ENDPOINT = f"{ORION_CALLBACK_URL}/notify"

# InfluxDB configuration
INFLUX_URL = config.INFLUX_URL
INFLUX_BUCKET = config.INFLUX_BUCKET
INFLUX_ORG = config.INFLUX_ORG
INFLUX_TOKEN = config.INFLUX_TOKEN
MEASUREMENT_ACCIDENTS = config.MEASUREMENT_ACCIDENTS
MEASUREMENT_PARKING = config.MEASUREMENT_PARKING
MEASUREMENT_TRAFFIC = config.MEASUREMENT_TRAFFIC
MEASUREMENT_VIOLATIONS = config.MEASUREMENT_VIOLATIONS

# FastAPI app setup
app = FastAPI(title="Orion Bridge API", description="HTTP bridge for Orion notifications")

# InfluxDB client
influx_client = InfluxDBClient(url=INFLUX_URL, token=INFLUX_TOKEN, org=INFLUX_ORG)
write_api = influx_client.write_api(write_options=SYNCHRONOUS)

# Statistics tracking
_STATS = defaultdict(int)
_LAST_PRINT_TIME = time.time()
_PRINT_INTERVAL = 5.0


def _attr_value(entity: Dict[str, Any], key: str, default: Optional[Any] = None) -> Optional[Any]:
    """Return the NGSI attribute `value` if present, else the raw primitive."""
    attr = entity.get(key)
    if isinstance(attr, dict):
        return attr.get("value", default)
    return attr if attr is not None else default


def _extract_coords(entity: Dict[str, Any]) -> Tuple[Optional[float], Optional[float]]:
    """Parse geo:json attribute coordinates -> (lat, lng).

    Supports Point coordinates [lng, lat] and LineString coordinates [[lng, lat], ...]
    where the first point is used as a representative location.
    """
    location = entity.get("location")
    if isinstance(location, dict):
        value = location.get("value") if "value" in location else location
        if isinstance(value, dict):
            coords = value.get("coordinates")
            if isinstance(coords, (list, tuple)):
                # Point
                if len(coords) == 2 and all(isinstance(c, (int, float)) for c in coords):
                    try:
                        lng = float(coords[0])
                        lat = float(coords[1])
                        return lat, lng
                    except (TypeError, ValueError):
                        return None, None
                # LineString -> use first point
                if coords and isinstance(coords[0], (list, tuple)) and len(coords[0]) >= 2:
                    try:
                        lng = float(coords[0][0])
                        lat = float(coords[0][1])
                        return lat, lng
                    except (TypeError, ValueError):
                        return None, None
    return None, None


def _event_time_ns(entity: Dict[str, Any]) -> int:
    """Convert dateObserved/observationDateTime into nanoseconds; fallback to now."""
    observed = _attr_value(entity, "dateObserved") or _attr_value(entity, "observationDateTime")
    if isinstance(observed, str) and observed:
        try:
            cleaned = observed.replace("Z", "+00:00")
            dt = isoparse(cleaned)
            return int(dt.timestamp() * 1_000_000_000)
        except ValueError:
            pass
    return int(time.time() * 1_000_000_000)


def _accident_to_point(entity: Dict[str, Any]) -> Optional[Point]:
    """Map TrafficAccident entity attributes to an InfluxDB point."""
    entity_id = entity.get("id")
    if not entity_id:
        return None

    severity = _attr_value(entity, "severity", "minor")
    status = _attr_value(entity, "status", "active")
    event_type = _attr_value(entity, "eventType", "update")
    description = _attr_value(entity, "description", "")
    lat, lng = _extract_coords(entity)

    if lat is None or lng is None:
        logger.debug(f"[skip] accident {entity_id} missing coordinates")
        return None

    accident_id = entity_id.split(":")[-1]
    point = (
        Point(MEASUREMENT_ACCIDENTS)
        .tag("type", entity.get("type", "TrafficAccident"))
        .tag("severity", severity)
        .field("id", accident_id)
        .field("entity_id", entity_id)
        .field("desc", description)
        .field("lat", float(lat))
        .field("lng", float(lng))
        .field("event", event_type)
        .field("status", status)
        .time(_event_time_ns(entity), WritePrecision.NS)
    )
    return point


def _parking_to_point(entity: Dict[str, Any]) -> Optional[Point]:
    """Map OnStreetParking entity attributes to an InfluxDB point."""
    entity_id = entity.get("id")
    if not entity_id:
        return None

    total = _attr_value(entity, "totalSpotNumber") or 0
    occupied = _attr_value(entity, "occupiedSpotNumber") or 0
    available = _attr_value(entity, "availableSpotNumber")
    try:
        total = int(total)
        occupied = int(occupied)
    except (TypeError, ValueError):
        logger.debug(f"[skip] parking {entity_id} invalid counts")
        return None
    if available is None:
        available = max(0, total - occupied)
    else:
        try:
            available = int(available)
        except (TypeError, ValueError):
            available = max(0, total - occupied)

    status = _attr_value(entity, "status", "open")
    street = _attr_value(entity, "streetName", "")
    lat, lng = _extract_coords(entity)

    if lat is None or lng is None:
        logger.debug(f"[skip] parking {entity_id} missing coordinates")
        return None

    point = (
        Point(MEASUREMENT_PARKING)
        .tag("type", entity.get("type", "OnStreetParking"))
        .tag("street", street)
        .field("entity_id", entity_id)
        .field("total_spots", total)
        .field("occupied_spots", occupied)
        .field("available_spots", available)
        .field("status", status)
        .field("lat", float(lat))
        .field("lng", float(lng))
        .time(_event_time_ns(entity), WritePrecision.NS)
    )
    return point


def _traffic_to_point(entity: Dict[str, Any]) -> Optional[Point]:
    """Map TrafficFlowObserved entity attributes to an InfluxDB point."""
    entity_id = entity.get("id")
    if not entity_id:
        return None

    ref_segment = _attr_value(entity, "refRoadSegment", "")
    intensity = _attr_value(entity, "intensity") or 0
    avg_speed = _attr_value(entity, "averageVehicleSpeed") or _attr_value(entity, "averageSpeed") or 0
    density = _attr_value(entity, "density") or 0
    occupancy = _attr_value(entity, "occupancy") or 0
    congestion_level = _attr_value(entity, "congestionLevel", "")
    congested = bool(_attr_value(entity, "congested", False))
    lat, lng = _extract_coords(entity)

    try:
        intensity = float(intensity)
        avg_speed = float(avg_speed)
        density = float(density)
        occupancy = float(occupancy)
    except (TypeError, ValueError):
        logger.debug(f"[skip] traffic {entity_id} invalid numeric values")
        return None

    if lat is None or lng is None:
        logger.debug(f"[skip] traffic {entity_id} missing coordinates")
        return None

    point = (
        Point(MEASUREMENT_TRAFFIC)
        .tag("type", entity.get("type", "TrafficFlowObserved"))
        .tag("congestion", congestion_level)
        .field("entity_id", entity_id)
        .field("ref_segment", ref_segment)
        .field("intensity", intensity)
        .field("avg_speed", avg_speed)
        .field("density", density)
        .field("occupancy", occupancy)
        .field("congested", congested)
        .field("lat", float(lat))
        .field("lng", float(lng))
        .time(_event_time_ns(entity), WritePrecision.NS)
    )
    return point


def _violation_to_point(entity: Dict[str, Any]) -> Optional[Point]:
    """Map TrafficViolation entity attributes to an InfluxDB point."""
    entity_id = entity.get("id")
    if not entity_id:
        return None

    violation_code = _attr_value(entity, "titleCode", "")
    description = _attr_value(entity, "description", "")
    payment_status = _attr_value(entity, "paymentStatus", "")
    equipment_id = _attr_value(entity, "equipmentId", "")
    equipment_type = _attr_value(entity, "equipmentType", "")
    lat, lng = _extract_coords(entity)

    if lat is None or lng is None:
        logger.debug(f"[skip] violation {entity_id} missing coordinates")
        return None

    point = (
        Point(MEASUREMENT_VIOLATIONS)
        .tag("type", entity.get("type", "TrafficViolation"))
        .tag("violation", violation_code)
        .field("entity_id", entity_id)
        .field("description", description)
        .field("payment_status", payment_status)
        .field("equipment_id", equipment_id)
        .field("equipment_type", equipment_type)
        .field("lat", float(lat))
        .field("lng", float(lng))
        .time(_event_time_ns(entity), WritePrecision.NS)
    )
    return point


def _entity_to_point(entity: Dict[str, Any]) -> Optional[Point]:
    """Dispatch entity to the correct InfluxDB measurement."""
    etype = entity.get("type")
    if etype == "OnStreetParking":
        return _parking_to_point(entity)
    if etype == "TrafficFlowObserved":
        return _traffic_to_point(entity)
    if etype == "TrafficViolation":
        return _violation_to_point(entity)
    return _accident_to_point(entity)


def _process_notification(payload: Dict[str, Any]) -> None:
    """Handle a notification payload (JSON with `data` array)."""
    global _LAST_PRINT_TIME
    
    entities = payload.get("data")
    if not isinstance(entities, list):
        logger.warning("Notification missing 'data' array")
        return

    stored = 0
    for entity in entities:
        if not isinstance(entity, dict):
            logger.warning("Skipping non-dict entity")
            continue
        
        point = _entity_to_point(entity)
        if point is None:
            continue
        
        try:
            write_api.write(bucket=INFLUX_BUCKET, org=INFLUX_ORG, record=point)
            stored += 1
            entity_type = entity.get("type", "Unknown")
            _STATS[entity_type] += 1
            logger.debug(f"[store] {entity.get('id')} written to Influx")
        except Exception as exc:
            logger.error(f"Failed to write {entity.get('id')}: {exc}")

    now = time.time()
    if now - _LAST_PRINT_TIME > _PRINT_INTERVAL:
        if _STATS:
            summary = ", ".join(f"{count} {etype}" for etype, count in _STATS.items())
            logger.info(f"Stored in last {int(_PRINT_INTERVAL)}s: {summary}")
            _STATS.clear()
        _LAST_PRINT_TIME = now


async def _ensure_subscription_exists() -> None:
    """Check if the subscription exists; create it if not."""
    async with httpx.AsyncClient() as client:
        headers = {
            "Content-Type": "application/json"
        }
        
        # List all subscriptions to check if ours exists
        list_url = f"{ORION_URL}/v2/subscriptions"
        try:
            response = await client.get(list_url, headers=headers, timeout=10.0)
            if response.status_code == 200:
                subscriptions = response.json()
                # Check if our subscription already exists
                for sub in subscriptions:
                    if sub.get("description") == "Automatic notifications to Orion bridge service":
                        logger.info(f"[subscription] Found existing subscription: {sub.get('id')}")
                        return
        except Exception as e:
            logger.warning(f"[subscription] Error checking subscriptions: {e}")

        # Create subscription if it doesn't exist
        logger.info(f"[subscription] Creating subscription with callback URL: {SUBSCRIPTION_ENDPOINT}")
        subscription_payload = {
            "description": "Automatic notifications to Orion bridge service",
            "subject": {
                "entities": [{"idPattern": ".*"}]
            },
            "notification": {
                "http": {
                    "url": SUBSCRIPTION_ENDPOINT
                }
            }
        }
        
        post_url = f"{ORION_URL}/v2/subscriptions"
        try:
            response = await client.post(
                post_url,
                json=subscription_payload,
                headers=headers,
                timeout=10.0
            )
            if response.status_code in (201, 200):
                logger.info(f"[subscription] Created subscription successfully")
            else:
                logger.error(
                    f"[subscription] Failed to create subscription. "
                    f"Status: {response.status_code}, Response: {response.text}"
                )
                logger.error(f"[subscription] Payload sent: {subscription_payload}")
        except Exception as e:
            logger.error(f"[subscription] Error creating subscription: {e}")


@app.on_event("startup")
async def startup_event():
    """Initialize subscription on startup."""
    logger.info("[startup] Ensuring Orion subscription exists...")
    await _ensure_subscription_exists()
    logger.info("[startup] Orion bridge service ready")


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown."""
    logger.info("[shutdown] Orion bridge service shutting down")
    influx_client.close()


@app.post("/notify")
async def receive_notification(payload: Dict[str, Any]):
    """Receive HTTP POST notifications from Orion Context Broker."""
    try:
        _process_notification(payload)
        return {"status": "ok"}
    except Exception as e:
        logger.error(f"Error processing notification: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        app,
        host=config.BRIDGE_BIND_HOST,
        port=config.BRIDGE_BIND_PORT,
    )
