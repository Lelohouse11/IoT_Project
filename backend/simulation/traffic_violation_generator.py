"""Simulation script generating synthetic traffic violation events for Orion."""

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

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
from backend.simulation.orion_helpers import OrionClient
from backend.simulation.geo_helpers import load_road_segments, sample_point_on_road

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

    # Wait for road segments to be loaded
    road_segments, segment_weights = load_road_segments()
    while not road_segments:
        print("[warn] No road segments loaded; retrying in 5 seconds...")
        time.sleep(5)
        road_segments, segment_weights = load_road_segments()
    
    next_id = 1

    def rnd_coord() -> Tuple[float, float]:
        on_road = sample_point_on_road(road_segments, segment_weights)
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
