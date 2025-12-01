"""MQTT bridge that listens to Orion notifications and stores them in InfluxDB.

The Orion instance already forwards every change to the public MQTT broker
(`mqtt://150.140.186.118:1883`, topic `orion_updates`). This service subscribes
to that feed, extracts the NGSI entities (same payload shape as HTTP
notifications), and writes them into the InfluxDB bucket reused from
`mqtt_to_influx_connector.py`.
"""

import argparse
import json
import random
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
from debug import print_context  # noqa: F401

import paho.mqtt.client as mqtt
from influxdb_client import InfluxDBClient, Point, WritePrecision
from influxdb_client.client.write_api import SYNCHRONOUS

# MQTT setup (mirrors the admin-made subscription visible in subscriptions.json)
MQTT_BROKER = "150.140.186.118"
MQTT_PORT = 1883
MQTT_TOPIC = "orion_updates"
FILTER_ATTRIBUTE = "owner"
FILTER_VALUE = "week4_up1125093"

# InfluxDB configuration reused from mqtt_to_influx_connector.py
INFLUX_URL = "http://150.140.186.118:8086"
INFLUX_BUCKET = "LeandersDB"
INFLUX_ORG = "students"
INFLUX_TOKEN = "8fyeafMyUOuvA5sKqGO4YSRFJX5SjdLvbJKqE2jfQ3PFY9cWkeQxQgpiMXV4J_BAWqSzAnI2eckYOsbYQqICeA=="
MEASUREMENT_ACCIDENTS = "accidents"
MEASUREMENT_PARKING = "parking_zones"

client = InfluxDBClient(url=INFLUX_URL, token=INFLUX_TOKEN, org=INFLUX_ORG)
write_api = client.write_api(write_options=SYNCHRONOUS)


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
            dt = datetime.fromisoformat(cleaned)
            return int(dt.timestamp() * 1_000_000_000)
        except ValueError:
            pass
    return time.time_ns()


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
        print(f"[skip] accident {entity_id} missing coordinates")
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
        print(f"[skip] parking {entity_id} invalid counts")
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
        print(f"[skip] parking {entity_id} missing coordinates")
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


def _entity_to_point(entity: Dict[str, Any]) -> Optional[Point]:
    """Dispatch entity to the correct InfluxDB measurement."""
    etype = entity.get("type")
    if etype == "OnStreetParking":
        return _parking_to_point(entity)
    return _accident_to_point(entity)


def _is_allowed_entity(entity: Dict[str, Any]) -> bool:
    """Return True if the entity belongs to our faker (owner attribute)."""
    owner = _attr_value(entity, FILTER_ATTRIBUTE)
    if owner is None:
        print(f"[skip] {entity.get('id')} missing '{FILTER_ATTRIBUTE}' attribute")
        return False
    if owner != FILTER_VALUE:
        print(f"[skip] {entity.get('id')} owner '{owner}' != '{FILTER_VALUE}'")
        return False
    return True


def _process_notification(message: str) -> None:
    """Handle a single MQTT payload (JSON with `data` array)."""
    try:
        payload = json.loads(message)
    except json.JSONDecodeError:
        print(f"[error] process_notification Invalid JSON: {message[:80]}")
        return

    entities = payload.get("data")
    if not isinstance(entities, list):
        print("[error] process_notification Notification missing 'data' array")
        return

    print(f"[notify]  {len(entities)} entities from MQTT")
    stored = 0
    for entity in entities:
        if not isinstance(entity, dict):
            print("[warn] process_notification Skipping non-dict entity")
            continue
        if not _is_allowed_entity(entity):
            continue
        point = _entity_to_point(entity)
        if point is None:
            continue
        try:
            write_api.write(bucket=INFLUX_BUCKET, org=INFLUX_ORG, record=point)
            stored += 1
            print(f"[store] {entity.get('id')} written to Influx")
        except Exception as exc:  # pragma: no cover - log and continue
            print(f"[error] Failed to write {entity.get('id')}: {exc}")
    if stored == 0:
        print("[warn] No entities stored for this notification")


def _on_connect(mqtt_client: mqtt.Client, userdata, flags, rc):
    if rc == 0:
        print(f"[mqtt] Connected to {userdata['host']}:{userdata['port']}, subscribing to {userdata['topic']}")
        mqtt_client.subscribe(userdata["topic"])
    else:
        print(f"[mqtt] Connection failed with code {rc}")


def _on_message(_client, _userdata, msg: mqtt.MQTTMessage):
    payload = msg.payload.decode("utf-8", errors="ignore")
    _process_notification(payload)


def main():
    parser = argparse.ArgumentParser(description="Orion MQTT -> Influx bridge")
    parser.add_argument("--mqtt-host", default=MQTT_BROKER, help="MQTT broker hostname")
    parser.add_argument("--mqtt-port", type=int, default=MQTT_PORT, help="MQTT broker port")
    parser.add_argument("--mqtt-topic", default=MQTT_TOPIC, help="MQTT topic carrying Orion notifications")
    parser.add_argument("--client-id", help="Custom MQTT client id")
    args = parser.parse_args()

    userdata = {"host": args.mqtt_host, "port": args.mqtt_port, "topic": args.mqtt_topic}
    client_id = args.client_id or f"orion-bridge-{random.randint(0, 9999)}"
    mqtt_client = mqtt.Client(client_id=client_id, userdata=userdata)
    mqtt_client.on_connect = _on_connect
    mqtt_client.on_message = _on_message

    print(f"[mqtt] Connecting as {client_id} to {args.mqtt_host}:{args.mqtt_port}, topic {args.mqtt_topic}")
    mqtt_client.connect(args.mqtt_host, args.mqtt_port)
    mqtt_client.loop_forever()


if __name__ == "__main__":
    main()
