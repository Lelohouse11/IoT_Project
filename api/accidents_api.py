"""
FastAPI service exposing recent active accidents from InfluxDB.

Used by the city-side map for live updates. The API returns a flat list of the
latest record per accident id that is still active within a given time window.

Notes
- CORS is enabled for local development (serving the UI via Live Server).
- Severity is stored as a tag in Influx and is preserved after pivot.
"""

import sys
from pathlib import Path
from typing import Any, Dict, List

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
from debug import print_context  # noqa: F401

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from influxdb_client import InfluxDBClient

# Reuse InfluxDB settings from sensor_faker.py
#from sensor_faker import influxdb_url, bucket, org, token

influxdb_url = "http://150.140.186.118:8086"
bucket = "LeandersDB"
org = "students"
token = "8fyeafMyUOuvA5sKqGO4YSRFJX5SjdLvbJKqE2jfQ3PFY9cWkeQxQgpiMXV4J_BAWqSzAnI2eckYOsbYQqICeA=="

app = FastAPI(title="Accidents API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

client = InfluxDBClient(url=influxdb_url, token=token, org=org)
query_api = client.query_api()


def _flux_recent_active(window: str = "15m") -> str:
    """Flux to retrieve the latest active record per accident id in a window.

    Steps
    - filter fields we need
    - pivot field names to columns for easier JSON mapping
    - group by id and keep the newest record per id
    - filter to active only
    """
    return f'''
from(bucket: "{bucket}")
  |> range(start: -{window})
  |> filter(fn: (r) => r._measurement == "accidents")
  |> filter(fn: (r) => r._field == "id" or r._field == "entity_id" or r._field == "desc" or r._field == "lat" or r._field == "lng" or r._field == "status" or r._field == "event")
  |> pivot(rowKey: ["_time"], columnKey: ["_field"], valueColumn: "_value")
  |> group(columns: ["id"])
  |> sort(columns: ["_time"], desc: true)
  |> unique(column: "id")
  |> filter(fn: (r) => r.status == "active")
  |> keep(columns: ["_time", "id", "entity_id", "lat", "lng", "desc", "severity", "event", "status"])  // severity/tag included
'''


@app.get("/api/accidents/recent")
def recent_accidents(window: str = "15m") -> List[Dict[str, Any]]:
    """Return latest active accidents within the given time window.

    Response schema: [{ id, lat, lng, severity, desc, ts }]
    """
    flux = _flux_recent_active(window)
    tables = query_api.query(org=org, query=flux)

    items: List[Dict[str, Any]] = []
    for table in tables:
        for record in table.records:
            v = record.values
            try:
                entity_id = v.get("entity_id")
                accident_id = v.get("id") or entity_id
                if accident_id is None:
                    continue
                accident_id = str(accident_id)
                if entity_id:
                    entity_id = str(entity_id)
                if accident_id.startswith("urn:"):
                    simple_id = accident_id.split(":")[-1]
                else:
                    simple_id = accident_id
                status = str(v.get("status")) if v.get("status") is not None else ""
                event_type = str(v.get("event")) if v.get("event") is not None else ""
                if status and status.lower() != "active":
                    continue
                if event_type and event_type.lower() == "clear":
                    continue
                items.append({
                    "id": simple_id,
                    "lat": float(v.get("lat")),
                    "lng": float(v.get("lng")),
                    "severity": str(v.get("severity")) if v.get("severity") is not None else "minor",
                    "desc": str(v.get("desc")) if v.get("desc") is not None else "",
                    "ts": str(v.get("_time")),
                })
            except (TypeError, ValueError):
                # Skip malformed rows (e.g., missing lat/lng)
                continue
    return items


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
