"""Report service for handling driver-submitted accident reports."""

import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict

import requests

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.simulation.orion_helpers import OrionClient

# Orion configuration - must match accident_generator.py
ORION_BASE_URL = "http://150.140.186.118:1026"
FIWARE_SERVICE_PATH = "/week4_up1125093"
FIWARE_OWNER = "week4_up1125093"
REQUEST_TIMEOUT = 5

ORION = OrionClient(
    base_url=ORION_BASE_URL,
    service_path=FIWARE_SERVICE_PATH,
    request_timeout=REQUEST_TIMEOUT,
)

# In-memory registry of active driver reports {report_id: timestamp}
# This will be accessed by the expiration service
active_reports: Dict[str, float] = {}


def _generate_report_id() -> str:
    """Generate unique UUID-based report ID with driver prefix."""
    # Format: D_{uuid4}_{timestamp_ms}
    timestamp_ms = int(datetime.now(timezone.utc).timestamp() * 1000)
    unique_id = str(uuid.uuid4())[:8]  # Use first 8 chars of UUID for brevity
    return f"D_{unique_id}_{timestamp_ms}"


def _build_fiware_entity(
    report_id: str,
    latitude: float,
    longitude: float,
    severity: str,
    description: str,
    event: str,
    status: str,
    now_iso: str
) -> Dict[str, Any]:
    """Construct NGSI v2 entity payload for driver-reported TrafficAccident."""
    return {
        "id": f"urn:ngsi-ld:TrafficAccident:{report_id}",
        "type": "TrafficAccident",
        "dateObserved": {"type": "DateTime", "value": now_iso},
        "location": {
            "type": "geo:json",
            "value": {"type": "Point", "coordinates": [longitude, latitude]},
        },
        "severity": {"type": "Text", "value": severity},
        "description": {"type": "Text", "value": description},
        "status": {"type": "Text", "value": status},
        "eventType": {"type": "Text", "value": event},
        "owner": {"type": "Text", "value": FIWARE_OWNER},
    }


def submit_accident_report(
    latitude: float,
    longitude: float,
    severity: str,
    description: str
) -> str:
    """Submit driver accident report to Orion Context Broker."""
    report_id = _generate_report_id()
    now_iso = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    
    entity = _build_fiware_entity(
        report_id=report_id,
        latitude=latitude,
        longitude=longitude,
        severity=severity,
        description=description,
        event="create",
        status="active",
        now_iso=now_iso
    )
    
    with requests.Session() as session:
        success = ORION.send_entity(session, entity, "create")
        
        if not success:
            raise RuntimeError(f"Failed to create accident report entity in Orion for {report_id}")
        
        # Track this report for expiration
        timestamp = datetime.now(timezone.utc).timestamp()
        active_reports[report_id] = timestamp
        
        print(f"[driver-report] Created {entity['id']} {severity} at ({latitude:.5f}, {longitude:.5f})")
        
        return report_id


def clear_accident_report(report_id: str, latitude: float, longitude: float, severity: str, description: str) -> bool:
    """Mark driver-reported accident as cleared in Orion."""
    now_iso = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    
    entity = _build_fiware_entity(
        report_id=report_id,
        latitude=latitude,
        longitude=longitude,
        severity=severity,
        description=description,
        event="clear",
        status="cleared",
        now_iso=now_iso
    )
    
    with requests.Session() as session:
        success = ORION.send_entity(session, entity, "update")
        
        if success:
            print(f"[driver-report] Cleared {entity['id']}")
            # Remove from active tracking
            active_reports.pop(report_id, None)
            
        return success
