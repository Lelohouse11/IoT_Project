"""Initialization script to seed OnStreetParking entities in Orion and MySQL."""

import argparse
import json
import random
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

import requests

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from simulation.orion_helpers import OrionClient
from backend import database

# Orion / FIWARE settings (reuse values from accident_generator.py)
FIWARE_TYPE = "OnStreetParking"
SMART_DATA_MODEL_SCHEMA = (
    "https://smart-data-models.github.io/dataModel.Parking/OnStreetParking/schema.json"
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
ORION_ENTITIES_URL = ORION.entities_url


@dataclass
class ParkingZone:
    """Simple representation of a parking segment (LineString)."""

    pid: str
    name: str
    total_spots: int
    occupied_spots: int
    coords: Sequence[Tuple[float, float]]  # [(lat, lng), ...]
    street_name: str = ""
    category: Sequence[str] = ("public",)
    allowed_vehicle_types: Sequence[str] = ("car",)
    highway_type: str = "residential"

    @property
    def available_spots(self) -> int:
        return max(0, self.total_spots - self.occupied_spots)

    def to_geojson(self) -> Dict[str, Any]:
        coord_pairs = [[lng, lat] for lat, lng in self.coords]
        return {"type": "LineString", "coordinates": coord_pairs}


def _build_entity(zone: ParkingZone, now_iso: str) -> Dict[str, Dict[str, Any]]:
    """Return a FIWARE OnStreetParking entity matching the Smart Data Model."""
    geojson = zone.to_geojson()
    return {
        "id": f"urn:ngsi-ld:{FIWARE_TYPE}:{zone.pid}",
        "type": FIWARE_TYPE,
        "owner": {"type": "Text", "value": FIWARE_OWNER},
        "name": {"type": "Text", "value": zone.name},
        "streetName": {"type": "Text", "value": zone.street_name or zone.name},
        "highwayType": {"type": "Text", "value": zone.highway_type},
        "category": {"type": "StructuredValue", "value": list(zone.category)},
        "allowedVehicleType": {
            "type": "StructuredValue",
            "value": list(zone.allowed_vehicle_types),
        },
        "totalSpotNumber": {"type": "Number", "value": zone.total_spots},
        "occupiedSpotNumber": {"type": "Number", "value": zone.occupied_spots},
        "availableSpotNumber": {"type": "Number", "value": zone.available_spots},
        "status": {"type": "Text", "value": "open"},
        "observationDateTime": {"type": "DateTime", "value": now_iso},
        "location": {"type": "geo:json", "value": geojson},
        "dataModel": {"type": "Text", "value": SMART_DATA_MODEL_SCHEMA},
    }


def _default_zones() -> List[ParkingZone]:
    """Return a generated set of 100 sample on-street segments around Patras."""
    zones = []
    center_lat = 38.2464
    center_lng = 21.7346
    max_offset = 0.02

    street_names = ["Maizonos", "Korinthou", "Agiou Andreou", "Gounari", "Agiou Nikolaou", "Ermou", "Patreos", "Votsi", "Kanari", "Miaouli"]
    categories = [("public", "free"), ("public", "feeCharged"), ("public", "shortTerm"), ("public", "forDisabled")]
    
    for i in range(100):
        pid = f"P-{i+1:03d}"
        
        # Random start point
        lat1 = center_lat + random.uniform(-max_offset, max_offset)
        lng1 = center_lng + random.uniform(-max_offset, max_offset)
        
        # Random end point (short segment)
        lat2 = lat1 + random.uniform(-0.001, 0.001)
        lng2 = lng1 + random.uniform(-0.001, 0.001)
        
        total_spots = random.randint(10, 100)
        occupied_spots = random.randint(0, total_spots)
        
        zones.append(
            ParkingZone(
                pid=pid,
                name=f"Parking Zone {pid}",
                street_name=random.choice(street_names),
                highway_type="residential",
                category=random.choice(categories),
                allowed_vehicle_types=("car",),
                total_spots=total_spots,
                occupied_spots=occupied_spots,
                coords=[(lat1, lng1), (lat2, lng2)],
            )
        )
    return zones


def _parse_feature(feature: Dict[str, Any]) -> Optional[ParkingZone]:
    """Map a GeoJSON feature into a ParkingZone dataclass."""
    props = feature.get("properties") or {}
    geom = feature.get("geometry") or {}
    coords_raw = geom.get("coordinates")
    geom_type = geom.get("type")

    coord_list: List[Tuple[float, float]] = []
    if geom_type == "LineString":
        for pt in coords_raw or []:
            if not isinstance(pt, Sequence) or len(pt) < 2:
                continue
            lng, lat = pt[0], pt[1]
            coord_list.append((float(lat), float(lng)))
    elif geom_type == "Polygon":
        # Use exterior ring as a rough curb line
        ring: Iterable[Sequence[float]] = (coords_raw or [])[0] if coords_raw else []
        for pt in ring:
            if not isinstance(pt, Sequence) or len(pt) < 2:
                continue
            lng, lat = pt[0], pt[1]
            coord_list.append((float(lat), float(lng)))
    if not coord_list:
        return None

    pid = str(props.get("id") or props.get("pid") or "")
    name = str(props.get("name") or pid or "Parking Zone")
    street_name = str(props.get("streetName") or name)
    highway_type = str(props.get("highwayType") or "residential")
    raw_category = props.get("category") or ["public"]
    category: List[str] = (
        list(raw_category) if isinstance(raw_category, (list, tuple)) else [str(raw_category)]
    )
    raw_allowed = props.get("allowedVehicleType") or ["car"]
    allowed_vehicle_types: List[str] = (
        list(raw_allowed) if isinstance(raw_allowed, (list, tuple)) else [str(raw_allowed)]
    )
    try:
        total_spots = int(
            props.get(
                "totalSpotNumber",
                props.get("totalCapacity", props.get("capacity", 0)),
            )
        )
    except (TypeError, ValueError):
        total_spots = 0
    try:
        occupied = int(
            props.get(
                "occupiedSpotNumber",
                props.get("occupiedSlots", props.get("occupied", 0)),
            )
        )
    except (TypeError, ValueError):
        occupied = 0
    occupied = max(0, min(occupied, total_spots))
    if not pid or total_spots <= 0:
        return None
    return ParkingZone(
        pid=pid,
        name=name,
        street_name=street_name,
        highway_type=highway_type,
        category=category,
        allowed_vehicle_types=allowed_vehicle_types,
        total_spots=total_spots,
        occupied_spots=occupied,
        coords=coord_list,
    )


def _load_geojson(path: Path) -> List[ParkingZone]:
    """Load parking zones from a GeoJSON FeatureCollection."""
    try:
        data = json.loads(path.read_text())
    except Exception as exc:  # pragma: no cover - defensive parsing
        print(f"[error] failed to parse GeoJSON at {path}: {exc}")
        return []
    zones: List[ParkingZone] = []
    for feature in data.get("features", []):
        zone = _parse_feature(feature)
        if zone:
            zones.append(zone)
    if not zones:
        print(f"[warn] no valid parking zones found in {path}")
    return zones


def _persist_zone_to_db(zone: ParkingZone, entity_id: str) -> None:
    """Persist created entity to the MySQL database."""
    try:
        # Calculate centroid for simple lat/lng storage
        lats = [p[0] for p in zone.coords]
        lngs = [p[1] for p in zone.coords]
        avg_lat = sum(lats) / len(lats)
        avg_lng = sum(lngs) / len(lngs)

        query = """
            INSERT INTO parking_entities (entity_id, name, lat, lng, total_spots)
            VALUES (%s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
                name = VALUES(name),
                lat = VALUES(lat),
                lng = VALUES(lng),
                total_spots = VALUES(total_spots)
        """
        database.execute_query(query, (entity_id, zone.name, avg_lat, avg_lng, zone.total_spots))
        print(f"[info] persisted {entity_id} to database")
    except Exception as exc:
        print(f"[warn] failed to persist {entity_id} to db: {exc}")


def seed_parking_zones(zones: Sequence[ParkingZone]) -> None:
    """Create all parking zones in Orion and persist to DB."""
    if not zones:
        print("[warn] no parking zones to seed")
        return

    now_iso = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    with requests.Session() as session:
        for zone in zones:
            entity = _build_entity(zone, now_iso)
            if ORION.send_entity(session, entity, "create"):
                print(
                    f"[create] {entity['id']} {zone.name} total={zone.total_spots} occupied={zone.occupied_spots}"
                )
                _persist_zone_to_db(zone, entity["id"])


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed Orion with parking zones (static polygons)")
    parser.add_argument(
        "--geojson",
        type=Path,
        help="GeoJSON FeatureCollection to override default parking zones",
    )
    args = parser.parse_args()

    zones = _load_geojson(args.geojson) if args.geojson else _default_zones()
    seed_parking_zones(zones)


if __name__ == "__main__":
    main()
