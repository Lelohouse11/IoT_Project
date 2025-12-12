"""Fetch Patras street data from Overpass API and store it locally for the accident faker."""

import json
from datetime import datetime, timezone
from pathlib import Path

import requests

OVERPASS_URL = "https://overpass-api.de/api/interpreter"
# Bounding box around Patras to avoid geocoding ambiguity while capturing all streets.
OVERPASS_QUERY = """
[out:json][timeout:120];
(
  way["highway"](38.18,21.65,38.32,21.85);
);
out geom;
"""
OUT_PATH = Path(__file__).resolve().parents[1] / "seed_data" / "patras_roads.geojson"


def fetch_patras_roads() -> Path:
    response = requests.post(OVERPASS_URL, data={"data": OVERPASS_QUERY}, timeout=120)
    response.raise_for_status()
    payload = response.json()

    features = []
    for el in payload.get("elements", []):
        if el.get("type") != "way" or "geometry" not in el:
            continue
        coords = [[pt["lon"], pt["lat"]] for pt in el["geometry"] if "lon" in pt and "lat" in pt]
        tags = el.get("tags", {}) or {}
        props = {
            "id": el.get("id"),
            "highway": tags.get("highway"),
            "name": tags.get("name"),
        }
        features.append(
            {
                "type": "Feature",
                "properties": {k: v for k, v in props.items() if v is not None},
                "geometry": {"type": "LineString", "coordinates": coords},
            }
        )

    data = {
        "type": "FeatureCollection",
        "generated": datetime.now(timezone.utc).isoformat(),
        "features": features,
    }
    OUT_PATH.write_text(json.dumps(data))
    print(f"Saved {len(features)} road features to {OUT_PATH.resolve()}")
    return OUT_PATH


if __name__ == "__main__":
    fetch_patras_roads()
