"""Map data API for the dashboard.

Exposes lightweight endpoints that read accidents and parking occupancy from
InfluxDB, and provides simple geometries (with road snapping for parking) for
the frontend map overlays.
"""

import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
from debug import print_context  # noqa: F401

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from influxdb_client import InfluxDBClient
import json
import math

# Reuse InfluxDB settings from sensor_faker.py
#from sensor_faker import influxdb_url, bucket, org, token

influxdb_url = "http://150.140.186.118:8086"
bucket = "LeandersDB"
org = "students"
token = "8fyeafMyUOuvA5sKqGO4YSRFJX5SjdLvbJKqE2jfQ3PFY9cWkeQxQgpiMXV4J_BAWqSzAnI2eckYOsbYQqICeA=="

ROADS_PATH = PROJECT_ROOT / "data_faker" / "patras_roads.geojson"

app = FastAPI(title="Accidents API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

client = InfluxDBClient(url=influxdb_url, token=token, org=org)
query_api = client.query_api()
_road_segments: list = []


def _haversine_distance_m(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """Approximate great-circle distance between two points (meters)."""
    r = 6371000.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = phi2 - phi1
    dlambda = math.radians(lng2 - lng1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return 2 * r * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def _load_roads() -> None:
    """Load road segments from Patras GeoJSON for snapping parking lines."""
    global _road_segments
    if _road_segments:
        return
    try:
        data = json.loads(Path(ROADS_PATH).read_text())
    except Exception:
        return
    segments = []
    for feature in data.get("features", []):
        geom = feature.get("geometry") or {}
        if geom.get("type") != "LineString":
            continue
        coords = geom.get("coordinates") or []
        for i in range(len(coords) - 1):
            try:
                lng1, lat1 = coords[i]
                lng2, lat2 = coords[i + 1]
                segments.append(((lat1, lng1), (lat2, lng2)))
            except Exception:
                continue
    _road_segments = segments


def _nearest_road_segment(lat: float, lng: float) -> Optional[list]:
    """Return the closest road segment to a point as GeoJSON coords [[lng,lat],[lng,lat]]."""
    _load_roads()
    best = None
    best_dist = float("inf")
    for (lat1, lng1), (lat2, lng2) in _road_segments:
        # midpoint distance heuristic
        mid_lat = (lat1 + lat2) / 2
        mid_lng = (lng1 + lng2) / 2
        d = _haversine_distance_m(lat, lng, mid_lat, mid_lng)
        if d < best_dist:
            best_dist = d
            best = [[lng1, lat1], [lng2, lat2]]
    return best


def _flux_recent_active(window: str = "15m") -> str:
    """Flux to retrieve the latest active record per accident id in a window.

    Steps
    - filter fields we need
    - pivot field names to columns for easier JSON mapping
    - group by id and keep the newest record per id
    - filter to active only
    """
    return f'''
from(bucket: "{bucket}")
  |> range(start: -{window})
  |> filter(fn: (r) => r._measurement == "accidents")
  |> filter(fn: (r) => r._field == "id" or r._field == "entity_id" or r._field == "desc" or r._field == "lat" or r._field == "lng" or r._field == "status" or r._field == "event")
  |> pivot(rowKey: ["_time"], columnKey: ["_field"], valueColumn: "_value")
  |> group(columns: ["id"])
  |> sort(columns: ["_time"], desc: true)
  |> unique(column: "id")
  |> filter(fn: (r) => r.status == "active")
  |> keep(columns: ["_time", "id", "entity_id", "lat", "lng", "desc", "severity", "event", "status"])  // severity/tag included
'''


def _flux_recent_parking(window: str = "15m") -> str:
    """Flux to retrieve the latest record per parking entity within a window."""
    return f'''
from(bucket: "{bucket}")
  |> range(start: -{window})
  |> filter(fn: (r) => r._measurement == "parking_zones")
  |> filter(fn: (r) => r._field == "entity_id" or r._field == "total_spots" or r._field == "occupied_spots" or r._field == "available_spots" or r._field == "status" or r._field == "lat" or r._field == "lng" or r._field == "street")
  |> pivot(rowKey: ["_time"], columnKey: ["_field"], valueColumn: "_value")
  |> group(columns: ["entity_id"])
  |> sort(columns: ["_time"], desc: true)
  |> unique(column: "entity_id")
  |> keep(columns: ["_time", "entity_id", "total_spots", "occupied_spots", "available_spots", "status", "lat", "lng", "street"])
'''


@app.get("/api/accidents/recent")
def recent_accidents(window: str = "15m") -> List[Dict[str, Any]]:
    """Return latest active accidents within the given time window.

    Response schema: [{ id, lat, lng, severity, desc, ts }]
    """
    flux = _flux_recent_active(window)
    tables = query_api.query(org=org, query=flux)

    items: List[Dict[str, Any]] = []
    for table in tables:
        for record in table.records:
            v = record.values
            try:
                entity_id = v.get("entity_id")
                accident_id = v.get("id") or entity_id
                if accident_id is None:
                    continue
                accident_id = str(accident_id)
                if entity_id:
                    entity_id = str(entity_id)
                if accident_id.startswith("urn:"):
                    simple_id = accident_id.split(":")[-1]
                else:
                    simple_id = accident_id
                status = str(v.get("status")) if v.get("status") is not None else ""
                event_type = str(v.get("event")) if v.get("event") is not None else ""
                if status and status.lower() != "active":
                    continue
                if event_type and event_type.lower() == "clear":
                    continue
                items.append({
                    "id": simple_id,
                    "lat": float(v.get("lat")),
                    "lng": float(v.get("lng")),
                    "severity": str(v.get("severity")) if v.get("severity") is not None else "minor",
                    "desc": str(v.get("desc")) if v.get("desc") is not None else "",
                    "ts": str(v.get("_time")),
                })
            except (TypeError, ValueError):
                # Skip malformed rows (e.g., missing lat/lng)
                continue
    return items


@app.get("/api/parking/recent")
def recent_parking(window: str = "15m") -> List[Dict[str, Any]]:
    """Return latest parking occupancy points within the given time window.

    Response schema: [{ id, entity_id, lat, lng, total_spots, occupied_spots, available_spots, status, street, ts, geometry }]
    """
    flux = _flux_recent_parking(window)
    tables = query_api.query(org=org, query=flux)

    items: List[Dict[str, Any]] = []
    for table in tables:
        for record in table.records:
            v = record.values
            try:
                entity_id = v.get("entity_id")
                if not entity_id:
                    continue
                entity_id = str(entity_id)
                total = int(v.get("total_spots"))
                occupied = int(v.get("occupied_spots"))
                available_raw = v.get("available_spots")
                try:
                    available = int(available_raw) if available_raw is not None else max(0, total - occupied)
                except (TypeError, ValueError):
                    available = max(0, total - occupied)
                geometry = None
                snapped = _nearest_road_segment(float(v.get("lat")), float(v.get("lng")))
                if snapped:
                    geometry = {"type": "LineString", "coordinates": snapped}
                else:
                    geometry = {"type": "Point", "coordinates": [float(v.get("lng")), float(v.get("lat"))]}
                items.append({
                    "id": entity_id.split(":")[-1],
                    "entity_id": entity_id,
                    "lat": float(v.get("lat")),
                    "lng": float(v.get("lng")),
                    "total_spots": total,
                    "occupied_spots": max(0, min(occupied, total)),
                    "available_spots": available,
                    "status": str(v.get("status")) if v.get("status") is not None else "",
                    "street": str(v.get("street")) if v.get("street") is not None else "",
                    "ts": str(v.get("_time")),
                    "geometry": geometry,
                })
            except (TypeError, ValueError):
                continue
    return items


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
