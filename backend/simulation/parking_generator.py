"""Simulation script generating synthetic parking occupancy updates for Orion."""

import argparse
import json
import random
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import requests

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
from backend.simulation.orion_helpers import OrionClient
from backend.shared import database

FIWARE_TYPE = "OnStreetParking"
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
class ParkingSimConfig:
    """Simulation knobs for interval, step size, and randomness."""
    interval_sec: float = 30.0
    max_step_change: int = 4
    jitter_prob: float = 0.45


@dataclass
class ParkingState:
    """Local cache of a parking entity's occupancy."""
    entity_id: str
    total_spots: int
    occupied: int


def target_occupancy_range_for_hour(hour: int) -> Tuple[float, float]:
    """Return (min_pct, max_pct) target occupancy for a given hour."""
    if 0 <= hour < 6:
        return 0.15, 0.45
    if 6 <= hour < 10:
        return 0.35, 0.8
    if 10 <= hour < 16:
        return 0.45, 0.95
    if 16 <= hour < 22:
        return 0.55, 1.05
    return 0.25, 0.75


def _load_entity_ids() -> List[str]:
    """Read stored entity ids from the MySQL database."""
    try:
        rows = database.fetch_all("SELECT entity_id FROM parking_entities")
        ids = [row["entity_id"] for row in rows]
        if not ids:
            print("[warn] no parking entities found in database")
        return ids
    except Exception as exc:
        print(f"[warn] failed to read entities from db: {exc}")
        return []


def _attr_value(entity: Dict[str, Any], key: str) -> Any:
    """Return attribute value handling NGSI v2 attribute objects."""
    raw = entity.get(key)
    if isinstance(raw, dict) and "value" in raw:
        return raw.get("value")
    return raw


def _fetch_parking_state(session: requests.Session) -> List[ParkingState]:
    """Fetch OnStreetParking entities by ids from the seed file."""
    entity_ids = _load_entity_ids()
    if not entity_ids:
        return []

    states: List[ParkingState] = []
    for eid in entity_ids:
        try:
            resp = session.get(
                f"{ORION.entities_url}/{eid}",
                headers=ORION.headers_no_body,
                timeout=ORION.request_timeout,
            )
            resp.raise_for_status()
        except requests.RequestException as exc:
            print(f"[warn] failed to fetch {eid}: {exc}")
            continue

        try:
            ent = resp.json()
        except ValueError:
            print(f"[warn] unable to parse entity {eid} response: {resp.text}")
            continue

        total_spots_raw = _attr_value(ent, "totalSpotNumber") or _attr_value(ent, "totalspotnumber")
        try:
            total_spots = int(total_spots_raw)
        except (TypeError, ValueError):
            continue
        occupied_raw = (
            _attr_value(ent, "occupiedSpotNumber")
            or _attr_value(ent, "occupiedspotnumber")
            or 0
        )
        try:
            occupied = int(occupied_raw)
        except (TypeError, ValueError):
            occupied = 0
        if not total_spots:
            continue
        states.append(
            ParkingState(
                entity_id=eid,
                total_spots=total_spots,
                occupied=max(0, min(occupied, total_spots)),
            )
        )

    print(f"[info] fetched {len(states)} OnStreetParking entities from Orion")
    return states


def simulate_parking(config: Optional[ParkingSimConfig] = None) -> None:
    """Continuously simulate parking occupancy and patch Orion entities."""
    if config is None:
        config = ParkingSimConfig()

    with requests.Session() as session:
        states = _fetch_parking_state(session)
        while not states:
            print("[warn] no OnStreetParking entities found; will retry after sleep")
            time.sleep(config.interval_sec)
            states = _fetch_parking_state(session)

        while True:
            if not states:
                print("[warn] no parking zones to update; sleeping")
                time.sleep(config.interval_sec)
                states = _fetch_parking_state(session)
                continue

            hour = datetime.now().hour
            min_pct, max_pct = target_occupancy_range_for_hour(hour)
            updated = 0
            occ_sum = 0
            now_iso = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

            for st in states:
                target_pct = random.uniform(min_pct, max_pct)
                target_slots = int(round(st.total_spots * target_pct))
                delta = target_slots - st.occupied
                # Clamp per-tick change but allow slightly larger swings
                if delta > config.max_step_change:
                    delta = config.max_step_change
                elif delta < -config.max_step_change:
                    delta = -config.max_step_change
                if random.random() < config.jitter_prob:
                    delta += random.choice([-2, -1, 1, 2])
                st.occupied = max(0, min(st.total_spots, st.occupied + delta))
                available = st.total_spots - st.occupied
                entity = {
                    "id": st.entity_id,
                    "type": FIWARE_TYPE,
                    "occupiedSpotNumber": {"type": "Number", "value": st.occupied},
                    "availableSpotNumber": {"type": "Number", "value": available},
                    "observationDateTime": {"type": "DateTime", "value": now_iso},
                }
                if ORION.send_entity(session, entity, "update"):
                    updated += 1
                    occ_sum += st.occupied / st.total_spots if st.total_spots else 0

            avg_pct = (occ_sum / updated * 100) if updated else 0.0
            print(f"[parking] updated {updated} zones, avg occupancy={avg_pct:.1f}% at {now_iso}")
            time.sleep(config.interval_sec)


def main() -> None:
    parser = argparse.ArgumentParser(description="On-street parking data faker (Orion Context Broker)")
    parser.add_argument("--interval", type=float, default=ParkingSimConfig.interval_sec, help="Interval between updates (seconds)")
    parser.add_argument("--step", type=int, default=ParkingSimConfig.max_step_change, help="Max +/- change per tick")
    parser.add_argument("--jitter", type=float, default=ParkingSimConfig.jitter_prob, help="Probability to add extra +/-1 noise")
    args = parser.parse_args()

    config = ParkingSimConfig(
        interval_sec=args.interval,
        max_step_change=args.step,
        jitter_prob=args.jitter,
    )
    simulate_parking(config)


if __name__ == "__main__":
    main()
