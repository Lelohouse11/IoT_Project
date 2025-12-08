"""Seed Orion Context Broker with OnStreetParking (Smart Data Models) entities.

The script now follows the Smart Data Models OnStreetParking schema:
  - NGSI v2 payload built with OnStreetParking attributes (totalSpotNumber, etc.)
  - creates a handful of static parking zones (LineString geometry)
  - deletes and recreates entities if they already exist

You can also point the script at a GeoJSON FeatureCollection via --geojson.
Each feature should include properties: id, name, totalSpotNumber, occupiedSpotNumber.
"""

import argparse
import json
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

import requests

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from data_faker.orion_helpers import OrionClient

# Orion / FIWARE settings (reuse values from accident_faker.py)
FIWARE_TYPE = "OnStreetParking"
SMART_DATA_MODEL_SCHEMA = (
    "https://smart-data-models.github.io/dataModel.Parking/OnStreetParking/schema.json"
)
ORION_BASE_URL = "http://150.140.186.118:1026"
FIWARE_SERVICE_PATH = "/week4_up1125093"
FIWARE_OWNER = "week4_up1125093"
REQUEST_TIMEOUT = 5
ENTITIES_FILE = Path(__file__).resolve().parent / "parking_entities.json"

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
    """Return a handful of sample on-street segments around Patras."""
    return [
        ParkingZone(
            pid="P-001",
            name="Parking Center",
            street_name="Maizonos",
            highway_type="tertiary",
            category=("public", "free"),
            allowed_vehicle_types=("car",),
            total_spots=60,
            occupied_spots=30,
            coords=[
                (38.2448, 21.7310),
                (38.2454, 21.7330),
            ],
        ),
        ParkingZone(
            pid="P-002",
            name="Harbor Lot",
            street_name="Akti Dymaion",
            highway_type="primary",
            category=("public", "feeCharged"),
            allowed_vehicle_types=("car", "motorcycle"),
            total_spots=90,
            occupied_spots=50,
            coords=[
                (38.2475, 21.7410),
                (38.2488, 21.7440),
            ],
        ),
        ParkingZone(
            pid="P-003",
            name="University Street",
            street_name="Kostas",
            highway_type="secondary",
            category=("public",),
            allowed_vehicle_types=("car", "motorcycle"),
            total_spots=45,
            occupied_spots=18,
            coords=[
                (38.2498, 21.7285),
                (38.2512, 21.7310),
            ],
        ),
        ParkingZone(
            pid="P-004",
            name="Old Town Stretch",
            street_name="Agiou Nikolaou",
            highway_type="tertiary",
            category=("public", "free"),
            allowed_vehicle_types=("car",),
            total_spots=35,
            occupied_spots=12,
            coords=[
                (38.2459, 21.7355),
                (38.2468, 21.7378),
            ],
        ),
        ParkingZone(
            pid="P-005",
            name="Hospital Side",
            street_name="Panepistimiou",
            highway_type="secondary",
            category=("public", "forDisabled"),
            allowed_vehicle_types=("car", "motorcycle"),
            total_spots=55,
            occupied_spots=25,
            coords=[
                (38.2625, 21.7450),
                (38.2640, 21.7475),
            ],
        ),
        ParkingZone(
            pid="P-006",
            name="Coastal Strip",
            street_name="Akti Dymaion",
            highway_type="primary",
            category=("public", "feeCharged"),
            allowed_vehicle_types=("car", "motorcycle"),
            total_spots=80,
            occupied_spots=52,
            coords=[
                (38.2422, 21.7365),
                (38.2436, 21.7390),
            ],
        ),
        ParkingZone(
            pid="P-007",
            name="North Pier",
            street_name="Gounari",
            highway_type="secondary",
            category=("public",),
            allowed_vehicle_types=("car",),
            total_spots=50,
            occupied_spots=28,
            coords=[
                (38.2490, 21.7405),
                (38.2502, 21.7428),
            ],
        ),
        ParkingZone(
            pid="P-008",
            name="South Dock",
            street_name="Othonos Amalias",
            highway_type="primary",
            category=("public", "feeCharged"),
            allowed_vehicle_types=("car",),
            total_spots=70,
            occupied_spots=46,
            coords=[
                (38.2385, 21.7325),
                (38.2399, 21.7351),
            ],
        ),
        ParkingZone(
            pid="P-009",
            name="Market Lane",
            street_name="Ermou",
            highway_type="tertiary",
            category=("public",),
            allowed_vehicle_types=("car", "motorcycle"),
            total_spots=40,
            occupied_spots=20,
            coords=[
                (38.2474, 21.7360),
                (38.2485, 21.7380),
            ],
        ),
        ParkingZone(
            pid="P-010",
            name="Station Front",
            street_name="Kalogeras",
            highway_type="tertiary",
            category=("public", "shortTerm"),
            allowed_vehicle_types=("car",),
            total_spots=30,
            occupied_spots=18,
            coords=[
                (38.2582, 21.7348),
                (38.2593, 21.7365),
            ],
        ),
        ParkingZone(
            pid="P-011",
            name="River Bend",
            street_name="Trion Navarchon",
            highway_type="secondary",
            category=("public",),
            allowed_vehicle_types=("car", "motorcycle"),
            total_spots=65,
            occupied_spots=34,
            coords=[
                (38.2460, 21.7288),
                (38.2475, 21.7314),
            ],
        ),
        ParkingZone(
            pid="P-012",
            name="Park Edge",
            street_name="Korinthou",
            highway_type="secondary",
            category=("public", "free"),
            allowed_vehicle_types=("car",),
            total_spots=55,
            occupied_spots=22,
            coords=[
                (38.2445, 21.7245),
                (38.2457, 21.7270),
            ],
        ),
        ParkingZone(
            pid="P-013",
            name="Museum Side",
            street_name="Maizonos",
            highway_type="secondary",
            category=("public",),
            allowed_vehicle_types=("car", "motorcycle"),
            total_spots=48,
            occupied_spots=30,
            coords=[
                (38.2433, 21.7308),
                (38.2446, 21.7330),
            ],
        ),
        ParkingZone(
            pid="P-014",
            name="Harbor West",
            street_name="Akti Dymaion",
            highway_type="primary",
            category=("public", "feeCharged"),
            allowed_vehicle_types=("car",),
            total_spots=85,
            occupied_spots=60,
            coords=[
                (38.2405, 21.7290),
                (38.2420, 21.7318),
            ],
        ),
        ParkingZone(
            pid="P-015",
            name="Library Front",
            street_name="Kanakari",
            highway_type="tertiary",
            category=("public", "shortTerm"),
            allowed_vehicle_types=("car",),
            total_spots=28,
            occupied_spots=12,
            coords=[
                (38.2488, 21.7275),
                (38.2496, 21.7295),
            ],
        ),
        ParkingZone(
            pid="P-016",
            name="University Link",
            street_name="Ateas",
            highway_type="secondary",
            category=("public",),
            allowed_vehicle_types=("car", "motorcycle"),
            total_spots=60,
            occupied_spots=38,
            coords=[
                (38.2620, 21.7380),
                (38.2634, 21.7405),
            ],
        ),
        ParkingZone(
            pid="P-017",
            name="Industrial Row",
            street_name="Asklipiou",
            highway_type="secondary",
            category=("public", "forLoadUnload"),
            allowed_vehicle_types=("car", "van"),
            total_spots=50,
            occupied_spots=26,
            coords=[
                (38.2550, 21.7470),
                (38.2562, 21.7495),
            ],
        ),
        ParkingZone(
            pid="P-018",
            name="Bus Terminal Side",
            street_name="Aratou",
            highway_type="tertiary",
            category=("public",),
            allowed_vehicle_types=("car", "motorcycle"),
            total_spots=42,
            occupied_spots=24,
            coords=[
                (38.2528, 21.7322),
                (38.2539, 21.7346),
            ],
        ),
        ParkingZone(
            pid="P-019",
            name="Residential Stretch",
            street_name="Agias Sofias",
            highway_type="residential",
            category=("public", "free"),
            allowed_vehicle_types=("car",),
            total_spots=38,
            occupied_spots=14,
            coords=[
                (38.2415, 21.7265),
                (38.2429, 21.7288),
            ],
        ),
        ParkingZone(
            pid="P-020",
            name="Upper Hill",
            street_name="Gerokostopoulou",
            highway_type="residential",
            category=("public",),
            allowed_vehicle_types=("car", "motorcycle"),
            total_spots=33,
            occupied_spots=10,
            coords=[
                (38.2570, 21.7278),
                (38.2581, 21.7301),
            ],
        ),
    ]


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


def _persist_entity_ids(entity_ids: Sequence[str]) -> None:
    """Persist created entity ids for reuse by the simulator."""
    payload = [{"id": eid, "url": f"{ORION_ENTITIES_URL}/{eid}"} for eid in entity_ids]
    try:
        ENTITIES_FILE.write_text(json.dumps(payload, indent=2))
        print(f"[info] wrote {len(payload)} entity ids to {ENTITIES_FILE}")
    except OSError as exc:
        print(f"[warn] failed to write entities file {ENTITIES_FILE}: {exc}")


def seed_parking_zones(zones: Sequence[ParkingZone]) -> None:
    """Create all parking zones in Orion."""
    if not zones:
        print("[warn] no parking zones to seed")
        return

    now_iso = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    created_ids: List[str] = []
    with requests.Session() as session:
        for zone in zones:
            entity = _build_entity(zone, now_iso)
            if _send_to_orion(session, entity):
                print(
                    f"[create] {entity['id']} {zone.name} total={zone.total_spots} occupied={zone.occupied_spots}"
                )
                created_ids.append(entity["id"])
    if created_ids:
        _persist_entity_ids(created_ids)


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
    created_ids: List[str] = []
    with requests.Session() as session:
        for zone in zones:
            entity = _build_entity(zone, now_iso)
            if ORION.send_entity(session, entity, "create"):
                print(
                    f"[create] {entity['id']} {zone.name} total={zone.total_spots} occupied={zone.occupied_spots}"
                )
                created_ids.append(entity["id"])
    if created_ids:
        _persist_entity_ids(created_ids)