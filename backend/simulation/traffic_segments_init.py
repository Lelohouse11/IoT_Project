"""Initialization script to seed TrafficFlowObserved entities in Orion and MySQL."""

import argparse
import random
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Sequence, Tuple

import requests

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.simulation.orion_helpers import OrionClient
from backend.simulation.geo_helpers import load_road_segments, sample_point_on_road
from backend.shared import database

# Orion / FIWARE settings
FIWARE_TYPE = "TrafficFlowObserved"
SMART_DATA_MODEL_SCHEMA = (
    "https://smart-data-models.github.io/dataModel.Transportation/TrafficFlowObserved/schema.json"
)
ORION_BASE_URL = "http://150.140.186.118:1026"
FIWARE_SERVICE_PATH = "/week4_up1125093"
FIWARE_OWNER = "week4_up1125093"
REQUEST_TIMEOUT = 5

ORION = OrionClient(
    base_url=ORION_BASE_URL,
    service_path=FIWARE_SERVICE_PATH,
    request_timeout=REQUEST_TIMEOUT,
)


@dataclass
class TrafficSegment:
    """Simple representation of a traffic segment (camera location)."""

    pid: str
    name: str
    lat: float
    lng: float
    street_name: str = ""
    
    def to_geojson(self) -> Dict[str, Any]:
        return {
            "type": "Point",
            "coordinates": [self.lng, self.lat]
        }


def _build_entity(segment: TrafficSegment, now_iso: str) -> Dict[str, Dict[str, Any]]:
    """Return a FIWARE TrafficFlowObserved entity matching the Smart Data Model."""
    geojson = segment.to_geojson()
    return {
        "id": f"urn:ngsi-ld:{FIWARE_TYPE}:{segment.pid}",
        "type": FIWARE_TYPE,
        "owner": {"type": "Text", "value": FIWARE_OWNER},
        "name": {"type": "Text", "value": segment.name},
        "streetName": {"type": "Text", "value": segment.street_name or segment.name},
        "dateObserved": {"type": "DateTime", "value": now_iso},
        "location": {"type": "geo:json", "value": geojson},
        "intensity": {"type": "Number", "value": 0},
        "averageVehicleSpeed": {"type": "Number", "value": 0},
        "occupancy": {"type": "Number", "value": 0},
        "density": {"type": "Number", "value": 0},
        "congestionLevel": {"type": "Text", "value": "unknown"},
        "congested": {"type": "Boolean", "value": False},
        "dataModel": {"type": "Text", "value": SMART_DATA_MODEL_SCHEMA},
    }


def _default_segments() -> List[TrafficSegment]:
    """Return a generated set of 100 sample traffic segments along the road network."""
    from backend.simulation.geo_helpers import haversine_distance_m
    
    segments = []
    road_segs, weights = load_road_segments()
    
    # Patras center and radius in meters
    center_lat = 38.2464
    center_lng = 21.7346
    max_radius_m = 1000  # 1 km radius around Patras center
    
    if not road_segs:
        print("[warn] no road segments loaded; using random locations as fallback")
        max_offset = 0.005
        for i in range(100):
            lat = center_lat + random.uniform(-max_offset, max_offset)
            lng = center_lng + random.uniform(-max_offset, max_offset)
            pid = f"SEG{i + 1:03d}"
            segments.append(
                TrafficSegment(
                    pid=pid,
                    name=f"Traffic Camera {pid}",
                    lat=lat,
                    lng=lng,
                    street_name=f"Street {pid}"
                )
            )
        return segments
    
    # Filter road segments to only those within max_radius_m of Patras center
    filtered_segs = []
    filtered_weights = []
    for seg, weight in zip(road_segs, weights):
        (lat1, lng1), (lat2, lng2) = seg
        # Check if segment midpoint is within radius
        mid_lat = (lat1 + lat2) / 2
        mid_lng = (lng1 + lng2) / 2
        dist = haversine_distance_m(center_lat, center_lng, mid_lat, mid_lng)
        if dist <= max_radius_m:
            filtered_segs.append(seg)
            filtered_weights.append(weight)
    
    if not filtered_segs:
        print(f"[warn] no road segments within {max_radius_m}m of center; using fallback")
        return _default_segments()  # Use fallback
    
    # Normalize weights for filtered segments
    total_weight = sum(filtered_weights)
    filtered_weights = [w / total_weight for w in filtered_weights]
    
    # Generate segments along road network
    for i in range(100):
        point = sample_point_on_road(filtered_segs, filtered_weights)
        if not point:
            print(f"[warn] failed to sample point for segment {i}")
            continue
            
        lat, lng = point
        pid = f"SEG{i + 1:03d}"
        segments.append(
            TrafficSegment(
                pid=pid,
                name=f"Traffic Camera {pid}",
                lat=lat,
                lng=lng,
                street_name=f"Street {pid}"
            )
        )
    return segments


def _persist_segment_to_db(segment: TrafficSegment, entity_id: str) -> None:
    """Persist created entity to the MySQL database."""
    try:
        query = """
            INSERT INTO traffic_entities (entity_id, name, lat, lng)
            VALUES (%s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
                name = VALUES(name),
                lat = VALUES(lat),
                lng = VALUES(lng)
        """
        database.execute_query(query, (entity_id, segment.name, segment.lat, segment.lng))
        print(f"[info] persisted {entity_id} to database")
    except Exception as exc:
        print(f"[warn] failed to persist {entity_id} to db: {exc}")


def seed_traffic_segments(segments: Sequence[TrafficSegment]) -> None:
    """Create all traffic segments in Orion and persist to DB."""
    if not segments:
        print("[warn] no traffic segments to seed")
        return

    now_iso = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    with requests.Session() as session:
        for segment in segments:
            entity = _build_entity(segment, now_iso)
            if ORION.send_entity(session, entity, "create"):
                print(f"[create] {entity['id']} {segment.name}")
                _persist_segment_to_db(segment, entity["id"])


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed Orion with traffic segments")
    args = parser.parse_args()

    segments = _default_segments()
    seed_traffic_segments(segments)


if __name__ == "__main__":
    main()
