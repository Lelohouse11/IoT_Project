"""Simulation script generating synthetic traffic accident events for Orion."""

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
from simulation.orion_helpers import OrionClient
from simulation.geo_helpers import load_road_segments, sample_point_on_road

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


def _build_fiware_entity(aid: str, accident: Accident, event: str, status: str, now_iso: str) -> Dict[str, Any]:
    """Construct the NGSI v2 entity payload for a TrafficAccident."""
    return {
        "id": f"urn:ngsi-ld:TrafficAccident:{aid}",
        "type": "TrafficAccident",
        "dateObserved": {"type": "DateTime", "value": now_iso},
        "location": {
            "type": "geo:json",
            "value": {"type": "Point", "coordinates": [accident.lng, accident.lat]},
        },
        "severity": {"type": "Text", "value": accident.severity},
        "description": {"type": "Text", "value": accident.desc},
        "status": {"type": "Text", "value": status},
        "eventType": {"type": "Text", "value": event},
        "owner": {"type": "Text", "value": "week4_up1125093"},
    }


def generate_accident_data(config: Optional[GeneratorConfig] = None):
    """Continuously emit fake accident events to the Orion Context Broker."""
    if config is None:
        config = GeneratorConfig()

    # Wait for road segments to be loaded
    road_segments, segment_weights = load_road_segments()
    while not road_segments:
        print("[warn] No road segments loaded; retrying in 5 seconds...")
        time.sleep(5)
        road_segments, segment_weights = load_road_segments()

    actions = ("create", "update", "clear")
    weights = (config.prob_new, config.prob_update, config.prob_clear)

    def next_action(active: Dict[str, Accident]) -> str:
        if not active:
            return "create"
        return random.choices(actions, weights=weights, k=1)[0]

    def rnd_coord():
        on_road = sample_point_on_road(road_segments, segment_weights)
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
