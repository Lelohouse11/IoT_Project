"""Generate synthetic TrafficViolation events and push them to Orion Context Broker."""

import argparse
import json
import math
import random
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

import requests

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
from data_faker.orion_helpers import OrionClient

FIWARE_TYPE = "TrafficViolation"
ORION_BASE_URL = "http://150.140.186.118:1026"
FIWARE_SERVICE_PATH = "/week4_up1125093"
FIWARE_OWNER = "week4_up1125093"
REQUEST_TIMEOUT = 5
ORION = OrionClient(
    base_url=ORION_BASE_URL,
    service_path=FIWARE_SERVICE_PATH,
    request_timeout=REQUEST_TIMEOUT,
)
ROADS_PATH = PROJECT_ROOT / "data_faker" / "patras_roads.geojson"


@dataclass
class GeneratorConfig:
    center_lat: float = 38.2464
    center_lng: float = 21.7346
    max_offset_deg: float = 0.02
    interval_sec: float = 4.0


VIOLATION_TYPES: List[Dict[str, str]] = [
    {"code": "double-parking", "desc": "Double parking detected"},
    {"code": "red-light", "desc": "Red light violation"},
    {"code": "no-stopping", "desc": "Stopping in no stopping zone"},
    {"code": "near-intersection", "desc": "Parking too close to intersection"},
]

EQUIPMENT_IDS = ("CAM-01", "CAM-02", "SENSOR-05", "SENSOR-09")
EQUIPMENT_TYPES = ("camera", "roadsideSensor")


def _haversine_distance_m(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """Approximate distance in meters between two lat/lng pairs."""
    r = 6371000.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = phi2 - phi1
    dlambda = math.radians(lng2 - lng1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return 2 * r * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def _load_road_segments(path: Path = ROADS_PATH) -> Tuple[List[Tuple[Tuple[float, float], Tuple[float, float]]], List[float]]:
    """Load road line segments from a GeoJSON file to place violations on streets."""
    if not path.exists():
        print(f"[warn] road data file missing at {path}, falling back to bounding-box sampling")
        return [], []

    try:
        data = json.loads(path.read_text())
    except Exception as exc:  # pragma: no cover - defensive parsing
        print(f"[warn] failed to parse road data ({exc}), falling back to bounding-box sampling")
        return [], []

    segments: List[Tuple[Tuple[float, float], Tuple[float, float]]] = []
    weights: List[float] = []
    for feature in data.get("features", []):
        geometry = feature.get("geometry") or {}
        if geometry.get("type") != "LineString":
            continue
        coords: Sequence[Sequence[float]] = geometry.get("coordinates") or []
        for i in range(len(coords) - 1):
            lng1, lat1 = coords[i]
            lng2, lat2 = coords[i + 1]
            dist = _haversine_distance_m(lat1, lng1, lat2, lng2)
            if dist <= 0:
                continue
            segments.append(((lat1, lng1), (lat2, lng2)))
            weights.append(dist)

    if not segments:
        print(f"[warn] no usable road segments found in {path}, falling back to bounding-box sampling")
    else:
        print(f"[info] loaded {len(segments)} road segments from {path}")
    return segments, weights


def _sample_point_on_road(
    segments: Sequence[Tuple[Tuple[float, float], Tuple[float, float]]],
    weights: Sequence[float],
) -> Optional[Tuple[float, float]]:
    """Pick a random point along the provided road segments."""
    if not segments:
        return None

    try:
        start, end = random.choices(segments, weights=weights, k=1)[0]
    except IndexError:
        return None
    t = random.random()
    lat = start[0] + (end[0] - start[0]) * t
    lng = start[1] + (end[1] - start[1]) * t
    return lat, lng


def _build_entity(
    vid: str,
    violation: Dict[str, str],
    lat: float,
    lng: float,
    now_iso: str,
) -> Dict[str, Dict[str, object]]:
    """Return a Smart Data Models compliant TrafficViolation entity."""
    return {
        "id": f"urn:ngsi-ld:{FIWARE_TYPE}:{vid}",
        "type": FIWARE_TYPE,
        "owner": {"type": "Text", "value": FIWARE_OWNER},
        "titleCode": {"type": "Text", "value": violation["code"]},
        "description": {"type": "Text", "value": violation["desc"]},
        "observationDateTime": {"type": "DateTime", "value": now_iso},
        "paymentStatus": {"type": "Text", "value": "Unpaid"},
        "equipmentId": {"type": "Text", "value": random.choice(EQUIPMENT_IDS)},
        "equipmentType": {"type": "Text", "value": random.choice(EQUIPMENT_TYPES)},
        "location": {
            "type": "geo:json",
            "value": {"type": "Point", "coordinates": [round(lng, 6), round(lat, 6)]},
        },
    }


def generate_violation_data(config: Optional[GeneratorConfig] = None) -> None:
    """Continuously emit synthetic traffic violations to Orion."""
    if config is None:
        config = GeneratorConfig()

    road_segments, segment_weights = _load_road_segments()
    next_id = 1

    def rnd_coord() -> Tuple[float, float]:
        on_road = _sample_point_on_road(road_segments, segment_weights)
        if on_road:
            return on_road
        lat = config.center_lat + random.uniform(-config.max_offset_deg, config.max_offset_deg)
        lng = config.center_lng + random.uniform(-config.max_offset_deg, config.max_offset_deg)
        return lat, lng

    with requests.Session() as session:
        while True:
            lat, lng = rnd_coord()
            violation = random.choice(VIOLATION_TYPES)
            vid = f"V{next_id:05d}"
            now_iso = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
            entity = _build_entity(vid, violation, lat, lng, now_iso)
            if ORION.send_entity(session, entity, "create"):
                print(f"[violation] {entity['id']} {violation['code']} at ({lat:.5f}, {lng:.5f})")
                next_id += 1
            time.sleep(config.interval_sec)


def main() -> None:
    parser = argparse.ArgumentParser(description="TrafficViolation faker (Orion Context Broker)")
    parser.add_argument("--center-lat", type=float, default=GeneratorConfig.center_lat, help="Center latitude")
    parser.add_argument("--center-lng", type=float, default=GeneratorConfig.center_lng, help="Center longitude")
    parser.add_argument("--offset", type=float, default=GeneratorConfig.max_offset_deg, help="Max random offset in degrees")
    parser.add_argument("--interval", type=float, default=GeneratorConfig.interval_sec, help="Interval between events (seconds)")
    args = parser.parse_args()

    config = GeneratorConfig(
        center_lat=args.center_lat,
        center_lng=args.center_lng,
        max_offset_deg=args.offset,
        interval_sec=args.interval,
    )
    generate_violation_data(config)


if __name__ == "__main__":
    main()
