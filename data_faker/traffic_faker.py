"""Simulate TrafficFlowObserved entities and push updates to Orion Context Broker."""

import argparse
import random
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Tuple

import requests

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
from debug import print_context  # noqa: F401
from data_faker.orion_helpers import OrionClient

FIWARE_TYPE = "TrafficFlowObserved"
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
class TrafficSimConfig:
    """Simulation knobs for street coverage and dynamics."""

    center_lat: float = 38.2464
    center_lng: float = 21.7346
    max_offset_deg: float = 0.02
    interval_sec: float = 5.0
    segments: int = 6
    base_intensity_range: Tuple[int, int] = (300, 1100)  # vehicles/hour
    base_speed_range: Tuple[float, float] = (28.0, 55.0)  # km/h
    speed_jitter: float = 6.0
    congestion_chance: float = 0.18
    congestion_speed_drop: float = 0.45  # multiply by this factor on congestion
    congestion_intensity_boost: float = 1.35
    jam_density: float = 120.0  # vehicles/km where traffic is considered jammed


@dataclass
class SegmentState:
    """Track current state for a monitored street segment."""

    ref_id: str
    lat: float
    lng: float
    base_intensity: float
    base_speed: float
    current_intensity: float
    current_speed: float


def _seed_segments(cfg: TrafficSimConfig) -> List[SegmentState]:
    """Create a set of random street segments around the configured center."""
    segments: List[SegmentState] = []
    for idx in range(cfg.segments):
        lat = cfg.center_lat + random.uniform(-cfg.max_offset_deg, cfg.max_offset_deg)
        lng = cfg.center_lng + random.uniform(-cfg.max_offset_deg, cfg.max_offset_deg)
        base_intensity = random.uniform(*cfg.base_intensity_range)
        base_speed = random.uniform(*cfg.base_speed_range)
        ref_id = f"SEG{idx + 1:03d}"
        segments.append(
            SegmentState(
                ref_id=ref_id,
                lat=lat,
                lng=lng,
                base_intensity=base_intensity,
                base_speed=base_speed,
                current_intensity=base_intensity,
                current_speed=base_speed,
            )
        )
    return segments


def _traffic_payload(seg: SegmentState, cfg: TrafficSimConfig, now_iso: str) -> Dict[str, Dict[str, object]]:
    """Build a Smart Data Models compliant TrafficFlowObserved payload."""
    density = seg.current_intensity / max(seg.current_speed, 5.0)
    occupancy = min(1.0, density / cfg.jam_density)
    if density >= cfg.jam_density * 0.8 or seg.current_speed < 10:
        level = "heavy"
    elif density >= cfg.jam_density * 0.4 or seg.current_speed < 20:
        level = "moderate"
    else:
        level = "freeFlow"
    congested = level != "freeFlow"

    return {
        "id": f"urn:ngsi-ld:{FIWARE_TYPE}:{seg.ref_id}",
        "type": FIWARE_TYPE,
        "owner": {"type": "Text", "value": FIWARE_OWNER},
        "refRoadSegment": {"type": "Text", "value": seg.ref_id},
        "dateObserved": {"type": "DateTime", "value": now_iso},
        "location": {
            "type": "geo:json",
            "value": {"type": "Point", "coordinates": [round(seg.lng, 6), round(seg.lat, 6)]},
        },
        "intensity": {"type": "Number", "value": int(round(seg.current_intensity))},
        "averageVehicleSpeed": {"type": "Number", "value": round(seg.current_speed, 1)},
        "density": {"type": "Number", "value": round(density, 2)},
        "occupancy": {"type": "Number", "value": round(occupancy, 3)},
        "congestionLevel": {"type": "Text", "value": level},
        "congested": {"type": "Boolean", "value": congested},
    }


def _tick_segment(seg: SegmentState, cfg: TrafficSimConfig) -> None:
    """Update a segment's speed/intensity with smooth noise and occasional congestion."""
    seg.current_speed = max(
        5.0,
        seg.base_speed + random.uniform(-cfg.speed_jitter, cfg.speed_jitter),
    )
    seg.current_intensity = max(
        80.0,
        seg.base_intensity + random.uniform(-seg.base_intensity * 0.08, seg.base_intensity * 0.08),
    )

    if random.random() < cfg.congestion_chance:
        seg.current_speed = max(5.0, seg.current_speed * cfg.congestion_speed_drop)
        seg.current_intensity *= cfg.congestion_intensity_boost


def simulate_traffic(cfg: TrafficSimConfig) -> None:
    """Continuously emit traffic observations for several street segments."""
    segments = _seed_segments(cfg)
    first_publish = True

    with requests.Session() as session:
        while True:
            now_iso = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
            action = "create" if first_publish else "update"
            sent = 0

            for seg in segments:
                _tick_segment(seg, cfg)
                entity = _traffic_payload(seg, cfg, now_iso)
                if ORION.send_entity(session, entity, action):
                    sent += 1

            first_publish = False
            print(f"[traffic] sent {sent} {action} requests at {now_iso}")
            time.sleep(cfg.interval_sec)


def main() -> None:
    parser = argparse.ArgumentParser(description="TrafficFlowObserved data faker (Orion Context Broker)")
    parser.add_argument("--interval", type=float, default=TrafficSimConfig.interval_sec, help="Interval between updates (seconds)")
    parser.add_argument("--segments", type=int, default=TrafficSimConfig.segments, help="Number of street segments to simulate")
    parser.add_argument("--congestion", type=float, default=TrafficSimConfig.congestion_chance, help="Probability of congestion per segment per tick (0-1)")
    parser.add_argument("--center-lat", type=float, default=TrafficSimConfig.center_lat, help="Center latitude for generated segments")
    parser.add_argument("--center-lng", type=float, default=TrafficSimConfig.center_lng, help="Center longitude for generated segments")
    parser.add_argument("--offset", type=float, default=TrafficSimConfig.max_offset_deg, help="Max random offset in degrees from the center")
    args = parser.parse_args()

    cfg = TrafficSimConfig(
        center_lat=args.center_lat,
        center_lng=args.center_lng,
        max_offset_deg=args.offset,
        interval_sec=args.interval,
        segments=args.segments,
        congestion_chance=args.congestion,
    )
    simulate_traffic(cfg)


if __name__ == "__main__":
    main()
