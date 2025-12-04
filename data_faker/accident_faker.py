"""Generate synthetic accident events and push them to Orion Context Broker.

Each accident follows an event life-cycle:
  - create: new accident appears (status=active)
  - update: position and/or severity refined (status=active)
  - clear:  accident resolved (status=cleared)

This aligns with the simple post/patch scripts provided in the lab materials,
but automatically drives the Orion Context Broker with richer accident data.
"""

import argparse
import json
import math
import random
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

import requests

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
from data_faker.orion_helpers import OrionClient

FIWARE_TYPE = "TrafficAccident"
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
    interval_sec: float = 3.0
    prob_new: float = 0.6
    prob_update: float = 0.25
    prob_clear: float = 0.15


@dataclass
class Accident:
    lat: float
    lng: float
    severity: str
    desc: str

    def jitter_location(self, max_delta: float = 0.001) -> None:
        """Apply slight jitter to simulate refined coordinates."""
        self.lat += random.uniform(-max_delta, max_delta)
        self.lng += random.uniform(-max_delta, max_delta)

    def maybe_update_severity(self, probability: float = 0.2) -> None:
        """Occasionally update severity to mimic new reports."""
        if random.random() < probability:
            self.severity = random_severity()


def random_severity() -> str:
    """Return a severity with a simple weighted distribution."""
    r = random.random()
    # Weighted distribution: minor (65%), medium (20%), major (15%)
    if r < 0.15:
        return "major"
    if r < 0.35:
        return "medium"
    return "minor"


def _haversine_distance_m(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """Approximate distance in meters between two lat/lng pairs."""
    r = 6371000.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = phi2 - phi1
    dlambda = math.radians(lng2 - lng1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return 2 * r * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def _load_road_segments(path: Path = ROADS_PATH) -> Tuple[List[Tuple[Tuple[float, float], Tuple[float, float]]], List[float]]:
    """Load road line segments from a GeoJSON file written by the Overpass fetch step."""
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


def _build_fiware_entity(aid: str, accident: Accident, event: str, status: str, now_iso: str) -> Dict[str, Dict[str, Any]]:
    """Return a FIWARE TrafficAccident entity with NGSI v2 attribute shape."""
    geojson = {
        "type": "Point",
        "coordinates": [round(accident.lng, 6), round(accident.lat, 6)],
    }
    sub_category = "collision" if "collision" in accident.desc.lower() else "incident"
    return {
        "id": f"urn:ngsi-ld:{FIWARE_TYPE}:{aid}",
        "type": FIWARE_TYPE,
        "owner": {"type": "Text", "value": FIWARE_OWNER},
        "category": {"type": "Text", "value": ["traffic", "accident"]},
        "subCategory": {"type": "Text", "value": [sub_category]},
        "description": {"type": "Text", "value": accident.desc},
        "severity": {"type": "Text", "value": accident.severity},
        "status": {"type": "Text", "value": status},
        "eventType": {"type": "Text", "value": event},
        "dateObserved": {"type": "DateTime", "value": now_iso},
        "location": {"type": "geo:json", "value": geojson},
    }



def generate_accident_data(config: Optional[GeneratorConfig] = None):
    """Continuously emit fake accident events to the Orion Context Broker."""
    if config is None:
        config = GeneratorConfig()

    road_segments, segment_weights = _load_road_segments()

    actions = ("create", "update", "clear")
    weights = (config.prob_new, config.prob_update, config.prob_clear)

    def next_action(active: Dict[str, Accident]) -> str:
        if not active:
            return "create"
        return random.choices(actions, weights=weights, k=1)[0]

    def rnd_coord():
        on_road = _sample_point_on_road(road_segments, segment_weights)
        if on_road:
            return on_road
        lat = config.center_lat + random.uniform(-config.max_offset_deg, config.max_offset_deg)
        lng = config.center_lng + random.uniform(-config.max_offset_deg, config.max_offset_deg)
        return lat, lng

    # Track active accidents in-memory by ID to simulate updates/clear actions
    active: Dict[str, Accident] = {}
    next_id = 1
    descriptions = [
        "Rear-end collision",
        "Multi-vehicle accident",
        "Blocked lane",
        "Minor fender bender",
        "Vehicle breakdown",
        "Debris on road",
    ]

    with requests.Session() as session:
        while True:
            action = next_action(active)

            if action == "create":
                lat, lng = rnd_coord()
                severity = random_severity()
                desc = random.choice(descriptions)
                aid = f"A{next_id:05d}"
                accident = Accident(lat=lat, lng=lng, severity=severity, desc=desc)
                entity = _build_fiware_entity(
                    aid=aid,
                    accident=accident,
                    event="create",
                    status="active",
                    now_iso=datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
                )
                if ORION.send_entity(session, entity, "create"):
                    active[aid] = accident
                    next_id += 1
                    print(f"[create] {entity['id']} {severity} at ({lat:.5f}, {lng:.5f})")

            elif action == "update":
                aid, accident = random.choice(list(active.items()))
                accident.lat, accident.lng = rnd_coord()
                accident.maybe_update_severity()
                entity = _build_fiware_entity(
                    aid=aid,
                    accident=accident,
                    event="update",
                    status="active",
                    now_iso=datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
                )
                if ORION.send_entity(session, entity, "update"):
                    print(f"[update] {entity['id']} {accident.severity} at ({accident.lat:.5f}, {accident.lng:.5f})")

            else:
                aid, accident = random.choice(list(active.items()))
                active.pop(aid)
                entity = _build_fiware_entity(
                    aid=aid,
                    accident=accident,
                    event="clear",
                    status="cleared",
                    now_iso=datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
                )
                if ORION.send_entity(session, entity, "update"):
                    print(f"[clear]  {entity['id']} cleared")

            time.sleep(config.interval_sec)


def main():
    """CLI wrapper for the accident faker with helpful defaults."""
    parser = argparse.ArgumentParser(description="Accident data faker (Orion Context Broker)")
    parser.add_argument("--center-lat", type=float, default=GeneratorConfig.center_lat, help="Center latitude")
    parser.add_argument("--center-lng", type=float, default=GeneratorConfig.center_lng, help="Center longitude")
    parser.add_argument("--offset", type=float, default=GeneratorConfig.max_offset_deg, help="Max random offset in degrees")
    parser.add_argument("--interval", type=float, default=GeneratorConfig.interval_sec, help="Interval between events (seconds)")
    parser.add_argument("--new", type=float, default=GeneratorConfig.prob_new, help="Probability of a new accident per tick")
    parser.add_argument("--update", type=float, default=GeneratorConfig.prob_update, help="Probability of an update per tick")
    parser.add_argument("--clear", type=float, default=GeneratorConfig.prob_clear, help="Probability of a clear per tick")
    args = parser.parse_args()

    config = GeneratorConfig(
        center_lat=args.center_lat,
        center_lng=args.center_lng,
        max_offset_deg=args.offset,
        interval_sec=args.interval,
        prob_new=args.new,
        prob_update=args.update,
        prob_clear=args.clear,
    )

    generate_accident_data(config)


if __name__ == "__main__":
    main()
