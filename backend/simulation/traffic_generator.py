"""Simulation script generating synthetic traffic flow updates for Orion."""

import argparse
import random
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Tuple

import requests

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
from backend.simulation.orion_helpers import OrionClient
from backend.shared import database
from backend.shared import config

FIWARE_TYPE = "TrafficFlowObserved"
ORION_BASE_URL = config.ORION_URL
FIWARE_SERVICE_PATH = config.FIWARE_SERVICE_PATH
FIWARE_OWNER = "week4_up1125093"
REQUEST_TIMEOUT = 5
ORION = OrionClient(
    base_url=ORION_BASE_URL,
    service_path=FIWARE_SERVICE_PATH,
    request_timeout=REQUEST_TIMEOUT,
)


@dataclass
class TrafficSimConfig:
    """Simulation knobs for dynamics."""
    interval_sec: float = 30.0
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
    entity_id: str
    base_intensity: float
    base_speed: float
    current_intensity: float
    current_speed: float


def _load_entity_ids() -> List[str]:
    """Read stored entity ids from the MySQL database."""
    try:
        rows = database.fetch_all("SELECT entity_id FROM traffic_entities")
        ids = [row["entity_id"] for row in rows]
        if not ids:
            print("[warn] no traffic entities found in database")
        return ids
    except Exception as exc:
        print(f"[warn] failed to read entities from db: {exc}")
        return []


def _init_segments(entity_ids: List[str], cfg: TrafficSimConfig) -> List[SegmentState]:
    """Initialize simulation state for existing entities."""
    segments: List[SegmentState] = []
    for eid in entity_ids:
        base_intensity = random.uniform(*cfg.base_intensity_range)
        base_speed = random.uniform(*cfg.base_speed_range)
        segments.append(
            SegmentState(
                entity_id=eid,
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

    # Include id/type and dynamic attributes for updates
    return {
        "id": seg.entity_id,
        "type": FIWARE_TYPE,
        "owner": {"type": "Text", "value": FIWARE_OWNER},
        "dateObserved": {"type": "DateTime", "value": now_iso},
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
    """Continuously emit traffic observations for existing street segments."""
    entity_ids = _load_entity_ids()
    while not entity_ids:
        print("[warn] No traffic entities found; will retry after sleep")
        time.sleep(cfg.interval_sec)
        entity_ids = _load_entity_ids()

    segments = _init_segments(entity_ids, cfg)
    print(f"[info] Starting simulation for {len(segments)} segments...")

    with requests.Session() as session:
        while True:
            now_iso = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
            sent = 0
            total_speed = 0.0
            total_intensity = 0.0

            for seg in segments:
                _tick_segment(seg, cfg)
                entity = _traffic_payload(seg, cfg, now_iso)
                # Use 'update' action to patch existing entities
                if ORION.send_entity(session, entity, "update"):
                    sent += 1
                    total_speed += seg.current_speed
                    total_intensity += seg.current_intensity

            avg_speed = (total_speed / sent) if sent else 0.0
            avg_intensity = (total_intensity / sent) if sent else 0.0
            print(f"[traffic] updated {sent} segments, avg speed={avg_speed:.1f} km/h, avg intensity={avg_intensity:.0f} at {now_iso}")
            time.sleep(cfg.interval_sec)


def main() -> None:
    parser = argparse.ArgumentParser(description="TrafficFlowObserved data faker (Orion Context Broker)")
    parser.add_argument("--interval", type=float, default=TrafficSimConfig.interval_sec, help="Interval between updates (seconds)")
    parser.add_argument("--congestion", type=float, default=TrafficSimConfig.congestion_chance, help="Probability of congestion per segment per tick (0-1)")
    args = parser.parse_args()

    cfg = TrafficSimConfig(
        interval_sec=args.interval,
        congestion_chance=args.congestion,
    )
    simulate_traffic(cfg)


if __name__ == "__main__":
    main()
