"""Map data API serving geo-snapped accidents, parking, and traffic data to the dashboard."""

import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from influxdb_client import InfluxDBClient

from backend.shared import config
from backend.public import reward_router
from backend.simulation import geo_helpers

influxdb_url = config.INFLUX_URL
bucket = config.INFLUX_BUCKET
org = config.INFLUX_ORG
token = config.INFLUX_TOKEN

app = FastAPI(title="Accidents API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include reward router for driver reward endpoints
app.include_router(reward_router.router)

client = InfluxDBClient(url=influxdb_url, token=token, org=org)
query_api = client.query_api()
_road_segments: list = []

MEASUREMENT_ACCIDENTS = config.MEASUREMENT_ACCIDENTS
MEASUREMENT_PARKING = config.MEASUREMENT_PARKING
MEASUREMENT_TRAFFIC = config.MEASUREMENT_TRAFFIC
MEASUREMENT_VIOLATIONS = config.MEASUREMENT_VIOLATIONS


def _load_roads() -> None:
    """Load road segments from Patras GeoJSON for snapping parking lines."""
    global _road_segments
    if _road_segments:
        return
    
    segments, _ = geo_helpers.load_road_segments()
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
        d = geo_helpers.haversine_distance_m(lat, lng, mid_lat, mid_lng)
        if d < best_dist:
            best_dist = d
            best = [[lng1, lat1], [lng2, lat2]]
    return best


def _flux_recent_active(window: str = "15m", start: Optional[str] = None, stop: Optional[str] = None,
                        lat_min: Optional[float] = None, lat_max: Optional[float] = None,
                        lng_min: Optional[float] = None, lng_max: Optional[float] = None) -> str:
    """Flux to retrieve the latest active record per accident id in a window."""
    range_clause = f'range(start: -{window})'
    if start and stop:
        range_clause = f'range(start: time(v: "{start}"), stop: time(v: "{stop}"))'

    loc_filter = ""
    if lat_min is not None and lat_max is not None and lng_min is not None and lng_max is not None:
        loc_filter = f'|> filter(fn: (r) => r.lat >= {lat_min} and r.lat <= {lat_max} and r.lng >= {lng_min} and r.lng <= {lng_max})'

    return f'''
from(bucket: "{bucket}")
  |> {range_clause}
  |> filter(fn: (r) => r._measurement == "{MEASUREMENT_ACCIDENTS}")
  |> filter(fn: (r) => r._field == "id" or r._field == "entity_id" or r._field == "desc" or r._field == "lat" or r._field == "lng" or r._field == "status" or r._field == "event")
  |> pivot(rowKey: ["_time"], columnKey: ["_field"], valueColumn: "_value")
  {loc_filter}
  |> group(columns: ["id"])
  |> sort(columns: ["_time"], desc: true)
  |> unique(column: "id")
  |> filter(fn: (r) => r.status == "active")
  |> keep(columns: ["_time", "id", "entity_id", "lat", "lng", "desc", "severity", "event", "status"])
'''


def _flux_recent_parking(window: str = "15m", start: Optional[str] = None, stop: Optional[str] = None,
                         lat_min: Optional[float] = None, lat_max: Optional[float] = None,
                         lng_min: Optional[float] = None, lng_max: Optional[float] = None) -> str:
    """Flux to retrieve the latest record per parking entity within a window."""
    range_clause = f'range(start: -{window})'
    if start and stop:
        range_clause = f'range(start: time(v: "{start}"), stop: time(v: "{stop}"))'

    loc_filter = ""
    if lat_min is not None and lat_max is not None and lng_min is not None and lng_max is not None:
        loc_filter = f'|> filter(fn: (r) => r.lat >= {lat_min} and r.lat <= {lat_max} and r.lng >= {lng_min} and r.lng <= {lng_max})'

    return f'''
from(bucket: "{bucket}")
  |> {range_clause}
  |> filter(fn: (r) => r._measurement == "{MEASUREMENT_PARKING}")
  |> filter(fn: (r) => r._field == "entity_id" or r._field == "total_spots" or r._field == "occupied_spots" or r._field == "available_spots" or r._field == "status" or r._field == "lat" or r._field == "lng")
  |> pivot(rowKey: ["_time"], columnKey: ["_field"], valueColumn: "_value")
  {loc_filter}
  |> group(columns: ["entity_id"])
  |> sort(columns: ["_time"], desc: true)
  |> unique(column: "entity_id")
  |> keep(columns: ["_time", "entity_id", "total_spots", "occupied_spots", "available_spots", "status", "lat", "lng", "street"])
'''


def _flux_recent_traffic(window: str = "15m", start: Optional[str] = None, stop: Optional[str] = None,
                         lat_min: Optional[float] = None, lat_max: Optional[float] = None,
                         lng_min: Optional[float] = None, lng_max: Optional[float] = None) -> str:
    """Flux to retrieve the latest traffic observations per segment within a window."""
    range_clause = f'range(start: -{window})'
    if start and stop:
        range_clause = f'range(start: time(v: "{start}"), stop: time(v: "{stop}"))'

    loc_filter = ""
    if lat_min is not None and lat_max is not None and lng_min is not None and lng_max is not None:
        loc_filter = f'|> filter(fn: (r) => r.lat >= {lat_min} and r.lat <= {lat_max} and r.lng >= {lng_min} and r.lng <= {lng_max})'

    return f'''
from(bucket: "{bucket}")
  |> {range_clause}
  |> filter(fn: (r) => r._measurement == "{MEASUREMENT_TRAFFIC}")
  |> filter(fn: (r) => r._field == "entity_id" or r._field == "ref_segment" or r._field == "intensity" or r._field == "avg_speed" or r._field == "density" or r._field == "occupancy" or r._field == "congested" or r._field == "lat" or r._field == "lng")
  |> pivot(rowKey: ["_time"], columnKey: ["_field"], valueColumn: "_value")
  {loc_filter}
  |> group(columns: ["entity_id"])
  |> sort(columns: ["_time"], desc: true)
  |> unique(column: "entity_id")
  |> keep(columns: ["_time", "entity_id", "ref_segment", "intensity", "avg_speed", "density", "occupancy", "congested", "lat", "lng", "congestion"])
'''


def _flux_recent_violations(window: str = "5m", start: Optional[str] = None, stop: Optional[str] = None,
                            lat_min: Optional[float] = None, lat_max: Optional[float] = None,
                            lng_min: Optional[float] = None, lng_max: Optional[float] = None) -> str:
    """Flux to retrieve the latest traffic violation detections within a window."""
    range_clause = f'range(start: -{window})'
    if start and stop:
        range_clause = f'range(start: time(v: "{start}"), stop: time(v: "{stop}"))'

    loc_filter = ""
    if lat_min is not None and lat_max is not None and lng_min is not None and lng_max is not None:
        loc_filter = f'|> filter(fn: (r) => r.lat >= {lat_min} and r.lat <= {lat_max} and r.lng >= {lng_min} and r.lng <= {lng_max})'

    return f'''
from(bucket: "{bucket}")
  |> {range_clause}
  |> filter(fn: (r) => r._measurement == "{MEASUREMENT_VIOLATIONS}")
  |> filter(fn: (r) => r._field == "entity_id" or r._field == "description" or r._field == "payment_status" or r._field == "equipment_id" or r._field == "equipment_type" or r._field == "lat" or r._field == "lng")
  |> pivot(rowKey: ["_time"], columnKey: ["_field"], valueColumn: "_value")
  {loc_filter}
  |> group(columns: ["entity_id"])
  |> sort(columns: ["_time"], desc: true)
  |> unique(column: "entity_id")
  |> keep(columns: ["_time", "entity_id", "description", "payment_status", "equipment_id", "equipment_type", "lat", "lng", "violation"])
'''


@app.get("/api/accidents/recent")
def recent_accidents(window: str = "15m", start_time: Optional[str] = None, end_time: Optional[str] = None,
                     lat_min: Optional[float] = None, lat_max: Optional[float] = None,
                     lng_min: Optional[float] = None, lng_max: Optional[float] = None) -> List[Dict[str, Any]]:
    """Return latest active accidents within the given time window.

    Response schema: [{ id, lat, lng, severity, desc, ts }]
    """
    flux = _flux_recent_active(window, start_time, end_time, lat_min, lat_max, lng_min, lng_max)
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
def recent_parking(window: str = "15m", start_time: Optional[str] = None, end_time: Optional[str] = None,
                   lat_min: Optional[float] = None, lat_max: Optional[float] = None,
                   lng_min: Optional[float] = None, lng_max: Optional[float] = None) -> List[Dict[str, Any]]:
    """Return latest parking occupancy points within the given time window.

    Response schema: [{ id, entity_id, lat, lng, total_spots, occupied_spots, available_spots, status, street, ts, geometry }]
    """
    flux = _flux_recent_parking(window, start_time, end_time, lat_min, lat_max, lng_min, lng_max)
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


@app.get("/api/traffic/recent")
def recent_traffic(window: str = "15m", start_time: Optional[str] = None, end_time: Optional[str] = None,
                   lat_min: Optional[float] = None, lat_max: Optional[float] = None,
                   lng_min: Optional[float] = None, lng_max: Optional[float] = None) -> List[Dict[str, Any]]:
    """Return latest traffic observations within the given time window.

    Response schema: [{ id, entity_id, ref_segment, lat, lng, intensity, avg_speed, density, occupancy, congested, congestion, ts }]
    """
    flux = _flux_recent_traffic(window, start_time, end_time, lat_min, lat_max, lng_min, lng_max)
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
                lat = float(v.get("lat"))
                lng = float(v.get("lng"))
                intensity = float(v.get("intensity"))
                avg_speed = float(v.get("avg_speed"))
                density = float(v.get("density"))
                occupancy = float(v.get("occupancy"))
                congested_raw = v.get("congested")
                congested = False
                if isinstance(congested_raw, str):
                    congested = congested_raw.lower() in ("true", "1", "yes")
                elif congested_raw is not None:
                    congested = bool(congested_raw)
                congestion_level = str(v.get("congestion")) if v.get("congestion") is not None else ""
                geometry = None
                snapped = _nearest_road_segment(lat, lng)
                if snapped:
                    geometry = {"type": "LineString", "coordinates": snapped}
                else:
                    geometry = {"type": "Point", "coordinates": [lng, lat]}
                items.append({
                    "id": entity_id.split(":")[-1],
                    "entity_id": entity_id,
                    "ref_segment": v.get("ref_segment"),
                    "lat": lat,
                    "lng": lng,
                    "intensity": intensity,
                    "avg_speed": avg_speed,
                    "density": density,
                    "occupancy": occupancy,
                    "congested": congested,
                    "congestion": congestion_level,
                    "ts": str(v.get("_time")),
                    "geometry": geometry,
                })
            except (TypeError, ValueError):
                continue
    return items


@app.get("/api/violations/recent")
def recent_violations(window: str = "15m", start_time: Optional[str] = None, end_time: Optional[str] = None,
                      lat_min: Optional[float] = None, lat_max: Optional[float] = None,
                      lng_min: Optional[float] = None, lng_max: Optional[float] = None) -> List[Dict[str, Any]]:
    """Return latest traffic violations within the given time window.

    Response schema: [{ id, entity_id, lat, lng, violation, description, payment_status, equipment_id, ts }]
    """
    flux = _flux_recent_violations(window, start_time, end_time, lat_min, lat_max, lng_min, lng_max)
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
                lat = float(v.get("lat"))
                lng = float(v.get("lng"))
                violation_code = str(v.get("violation")) if v.get("violation") is not None else ""
                items.append({
                    "id": entity_id.split(":")[-1],
                    "entity_id": entity_id,
                    "lat": lat,
                    "lng": lng,
                    "violation": violation_code,
                    "description": str(v.get("description")) if v.get("description") is not None else "",
                    "payment_status": str(v.get("payment_status")) if v.get("payment_status") is not None else "",
                    "equipment_id": str(v.get("equipment_id")) if v.get("equipment_id") is not None else "",
                    "equipment_type": str(v.get("equipment_type")) if v.get("equipment_type") is not None else "",
                    "ts": str(v.get("_time")),
                })
            except (TypeError, ValueError):
                continue
    return items


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
