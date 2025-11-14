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
import time
from datetime import datetime
from typing import Any, Dict, Optional, Tuple

import paho.mqtt.client as mqtt
from influxdb_client import InfluxDBClient, Point, WritePrecision
from influxdb_client.client.write_api import SYNCHRONOUS

# MQTT setup (mirrors the admin-made subscription visible in subscriptions.json)
MQTT_BROKER = "150.140.186.118"
MQTT_PORT = 1883
MQTT_TOPIC = "orion_updates"

# InfluxDB configuration reused from mqtt_to_influx_connector.py
INFLUX_URL = "http://150.140.186.118:8086"
INFLUX_BUCKET = "LeandersDB"
INFLUX_ORG = "students"
INFLUX_TOKEN = "8fyeafMyUOuvA5sKqGO4YSRFJX5SjdLvbJKqE2jfQ3PFY9cWkeQxQgpiMXV4J_BAWqSzAnI2eckYOsbYQqICeA=="
MEASUREMENT = "accidents"

client = InfluxDBClient(url=INFLUX_URL, token=INFLUX_TOKEN, org=INFLUX_ORG)
write_api = client.write_api(write_options=SYNCHRONOUS)


def _attr_value(entity: Dict[str, Any], key: str, default: Optional[Any] = None) -> Optional[Any]:
    """Return the NGSI attribute `value` if present."""
    attr = entity.get(key)
    if isinstance(attr, dict):
        return attr.get("value", default)
    return default


def _extract_coords(entity: Dict[str, Any]) -> Tuple[Optional[float], Optional[float]]:
    """Parse geo:json attribute coordinates -> (lat, lng)."""
    location = entity.get("location")
    if isinstance(location, dict):
        value = location.get("value")
        if isinstance(value, dict):
            coords = value.get("coordinates")
            if isinstance(coords, (list, tuple)) and len(coords) == 2:
                try:
                    lng = float(coords[0])
                    lat = float(coords[1])
                    return lat, lng
                except (TypeError, ValueError):
                    return None, None
    return None, None


def _event_time_ns(entity: Dict[str, Any]) -> int:
    """Convert dateObserved into nanoseconds; fallback to current time."""
    observed = _attr_value(entity, "dateObserved")
    if isinstance(observed, str) and observed:
        try:
            cleaned = observed.replace("Z", "+00:00")
            dt = datetime.fromisoformat(cleaned)
            return int(dt.timestamp() * 1_000_000_000)
        except ValueError:
            pass
    return time.time_ns()


def _entity_to_point(entity: Dict[str, Any]) -> Optional[Point]:
    """Map Orion entity attributes to an InfluxDB point."""
    entity_id = entity.get("id")
    if not entity_id:
        return None

    severity = _attr_value(entity, "severity", "minor")
    status = _attr_value(entity, "status", "active")
    event_type = _attr_value(entity, "eventType", "update")
    description = _attr_value(entity, "description", "")
    lat, lng = _extract_coords(entity)

    if lat is None or lng is None:
        print(f"[skip] entity_to_point {entity_id} missing coordinates")
        return None

    accident_id = entity_id.split(":")[-1]
    point = (
        Point(MEASUREMENT)
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
