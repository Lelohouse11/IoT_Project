"""Slim API for the driver-side PWA (Leaflet) to expose map overlays such as traffic.

This is intentionally separate from map_data_api.py to keep a narrow surface area
for the frontend. It reuses the same InfluxDB measurements and snaps points to
road geometries when possible.
"""

import asyncio
import sys
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from influxdb_client import InfluxDBClient

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from api import config  # noqa: E402  # isort: skip
from data_faker import geo_helpers  # noqa: E402  # isort: skip

influxdb_url = config.INFLUX_URL
bucket = config.INFLUX_BUCKET
org = config.INFLUX_ORG
token = config.INFLUX_TOKEN

ROADS_PATH = PROJECT_ROOT / "data_faker" / "patras_roads.geojson"

client = InfluxDBClient(url=influxdb_url, token=token, org=org)
query_api = client.query_api()
_road_segments: list = []
_traffic_cache: List[Dict[str, Any]] = []
_traffic_task: Optional[asyncio.Task] = None

MEASUREMENT_TRAFFIC = config.MEASUREMENT_TRAFFIC


def _load_roads() -> None:
    """Load road segments from Patras GeoJSON for snapping traffic lines."""
    global _road_segments
    if _road_segments:
        return

    segments, _ = geo_helpers.load_road_segments(ROADS_PATH)
    _road_segments = segments
    print(f"[frontend_map_api] Loaded {len(_road_segments)} road segments for snapping")


def _nearest_road_segment(lat: float, lng: float) -> Optional[list]:
    """Return the closest road segment to a point as GeoJSON coords [[lng,lat],[lng,lat]]."""
    _load_roads()
    best = None
    best_dist = float("inf")
    for (lat1, lng1), (lat2, lng2) in _road_segments:
        mid_lat = (lat1 + lat2) / 2
        mid_lng = (lng1 + lng2) / 2
        d = geo_helpers.haversine_distance_m(lat, lng, mid_lat, mid_lng)
        if d < best_dist:
            best_dist = d
            best = [[lng1, lat1], [lng2, lat2]]
    return best


def _flux_recent_traffic(window: str = "15m") -> str:
    """Flux to retrieve the latest traffic observations per segment within a window."""
    return f'''
from(bucket: "{bucket}")
  |> range(start: -{window})
  |> filter(fn: (r) => r._measurement == "{MEASUREMENT_TRAFFIC}")
  |> filter(fn: (r) => r._field == "entity_id" or r._field == "ref_segment" or r._field == "intensity" or r._field == "avg_speed" or r._field == "density" or r._field == "occupancy" or r._field == "congested" or r._field == "lat" or r._field == "lng")
  |> pivot(rowKey: ["_time"], columnKey: ["_field"], valueColumn: "_value")
  |> group(columns: ["entity_id"])
  |> sort(columns: ["_time"], desc: true)
  |> unique(column: "entity_id")
  |> keep(columns: ["_time", "entity_id", "ref_segment", "lat", "lng", "intensity", "avg_speed", "density", "occupancy", "congested", "congestion"])
'''


def _fetch_recent_traffic_sync(window: str = "15m") -> List[Dict[str, Any]]:
    flux = _flux_recent_traffic(window)
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


async def _refresh_traffic_cache(loop_window: str = "15m", interval_seconds: int = 15) -> None:
    """Poll Influx every interval and keep a fresh cache so the endpoint responds immediately."""
    global _traffic_cache
    while True:
        try:
            data = await asyncio.to_thread(_fetch_recent_traffic_sync, loop_window)
            _traffic_cache = data
            print(f"[frontend_map_api] Cache refresh -> {len(data)} traffic items (window={loop_window})")
        except Exception as exc:  # noqa: BLE001
            print(f"[frontend_map_api] Cache refresh error: {exc}")
        await asyncio.sleep(interval_seconds)


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _traffic_task
    print(f"[frontend_map_api] startup: influx={influxdb_url} bucket={bucket} org={org}")
    _traffic_task = asyncio.create_task(_refresh_traffic_cache())
    try:
        yield
    finally:
        if _traffic_task:
            _traffic_task.cancel()
            try:
                await _traffic_task
            except asyncio.CancelledError:
                pass
        print("[frontend_map_api] shutdown")


app = FastAPI(title="Driver PWA Map API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/pwa/traffic/recent")
def recent_traffic(window: str = "15m") -> List[Dict[str, Any]]:
    """Return latest traffic observations within the given time window for the PWA.

    Response schema: [{ id, entity_id, ref_segment, lat, lng, intensity, avg_speed, density, occupancy, congested, congestion, ts, geometry }]
    """
    print(f"[frontend_map_api] Traffic request received (window={window})")
    data = _traffic_cache if _traffic_cache else _fetch_recent_traffic_sync(window)
    print(f"[frontend_map_api] Traffic response window={window} -> {len(data)} items")
    return data


if __name__ == "__main__":
    import uvicorn
    print("[frontend_map_api] Starting on 0.0.0.0:8010")
    uvicorn.run(app, host="0.0.0.0", port=8010)
