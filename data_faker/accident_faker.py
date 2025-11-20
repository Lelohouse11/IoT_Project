"""Generate synthetic accident events and push them to Orion Context Broker.

Each accident follows an event life-cycle:
  - create: new accident appears (status=active)
  - update: position and/or severity refined (status=active)
  - clear:  accident resolved (status=cleared)

This aligns with the simple post/patch scripts provided in the lab materials,
but automatically drives the Orion Context Broker with richer accident data.
"""

import argparse
import random
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

import requests

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
from debug import print_context  # noqa: F401

FIWARE_TYPE = "TrafficAccident"
ORION_BASE_URL = "http://150.140.186.118:1026"
ORION_ENTITIES_URL = f"{ORION_BASE_URL}/v2/entities"
FIWARE_SERVICE_PATH = "/week4_up1125093"
FIWARE_OWNER = "week4_up1125093"
ORION_HEADERS = {
    "Content-Type": "application/json",
    "FIWARE-ServicePath": FIWARE_SERVICE_PATH,
}
ORION_HEADERS_NO_BODY = {
    "FIWARE-ServicePath": FIWARE_SERVICE_PATH,
}
REQUEST_TIMEOUT = 5


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


def _response_detail(response: requests.Response) -> str:
    try:
        data = response.json()
        error = data.get("error", "")
        description = data.get("description", "")
        detail = " ".join(part for part in (error, description) if part)
        return detail or response.text
    except ValueError:
        return response.text


def _is_entity_exists_err(response: requests.Response) -> bool:
    """Return True if Orion reports the entity already exists."""
    detail = _response_detail(response).lower()
    return "already exists" in detail


def _delete_entity(session: requests.Session, entity_id: str) -> bool:
    """Delete an existing entity to allow recreation."""
    try:
        resp = session.delete(
            f"{ORION_ENTITIES_URL}/{entity_id}",
            headers=ORION_HEADERS_NO_BODY,
            timeout=REQUEST_TIMEOUT,
        )
    except requests.RequestException as exc:
        print(f"[error] delete {entity_id} failed: {exc}")
        return False

    if resp.status_code in (204, 404):
        print(f"[delete] {entity_id} removed before recreation")
        return True

    print(f"[error] delete {entity_id} failed: {resp.status_code} {_response_detail(resp)}")
    return False


def _send_to_orion(session: requests.Session, entity: Dict[str, Dict[str, Any]], action: str) -> bool:
    """Send the create or update payload to Orion, mirroring the lab templates."""
    try:
        if action == "create":
            response = session.post(
                ORION_ENTITIES_URL,
                json=entity,
                headers=ORION_HEADERS,
                timeout=REQUEST_TIMEOUT,
            )
            if response.status_code == 422 and _is_entity_exists_err(response):
                if _delete_entity(session, entity["id"]):
                    response = session.post(
                        ORION_ENTITIES_URL,
                        json=entity,
                        headers=ORION_HEADERS,
                        timeout=REQUEST_TIMEOUT,
                    )
                    print(f"[debug] send_to_orion create response: {response.status_code} {response.text} {response.headers}")
            expected = 201
        else:
            attrs = {k: v for k, v in entity.items() if k not in ("id", "type")}
            response = session.patch(
                f"{ORION_ENTITIES_URL}/{entity['id']}/attrs",
                json=attrs,
                headers=ORION_HEADERS,
                timeout=REQUEST_TIMEOUT,
            )
            expected = 204
    except requests.RequestException as exc:
        print(f"[error]  {action} {entity['id']} failed: {exc}")
        return False

    if response.status_code != expected:
        detail = _response_detail(response)
        print(f"[error] send_to_orion {action} {entity['id']} failed: {response.status_code} {detail}")
        return False

    return True



def generate_accident_data(config: Optional[GeneratorConfig] = None):
    """Continuously emit fake accident events to the Orion Context Broker."""
    if config is None:
        config = GeneratorConfig()

    actions = ("create", "update", "clear")
    weights = (config.prob_new, config.prob_update, config.prob_clear)

    def next_action(active: Dict[str, Accident]) -> str:
        if not active:
            return "create"
        return random.choices(actions, weights=weights, k=1)[0]

    def rnd_coord():
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
                if _send_to_orion(session, entity, "create"):
                    active[aid] = accident
                    next_id += 1
                    print(f"[create] {entity['id']} {severity} at ({lat:.5f}, {lng:.5f})")

            elif action == "update":
                aid, accident = random.choice(list(active.items()))
                accident.jitter_location()
                accident.maybe_update_severity()
                entity = _build_fiware_entity(
                    aid=aid,
                    accident=accident,
                    event="update",
                    status="active",
                    now_iso=datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
                )
                if _send_to_orion(session, entity, "update"):
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
                if _send_to_orion(session, entity, "update"):
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
