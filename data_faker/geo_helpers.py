import json
import math
import random
from pathlib import Path
from typing import List, Optional, Sequence, Tuple

def haversine_distance_m(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """Approximate distance in meters between two lat/lng pairs."""
    r = 6371000.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = phi2 - phi1
    dlambda = math.radians(lng2 - lng1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return 2 * r * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def load_road_segments(path: Path) -> Tuple[List[Tuple[Tuple[float, float], Tuple[float, float]]], List[float]]:
    """Load road line segments from a GeoJSON file written by the Overpass fetch step."""
    if not path.exists():
        print(f"[warn] road data file missing at {path}, falling back to bounding-box sampling")
        return [], []

    try:
        data = json.loads(path.read_text())
    except Exception as exc:  # pragma: no cover - defensive parsing
        print(f"[warn] failed to parse road data ({exc}), falling back to bounding-box sampling")
        return [], []

    segments: List[Tuple[Tuple[float, float], Tuple[float, float]]] = []
    weights: List[float] = []
    for feature in data.get("features", []):
        geometry = feature.get("geometry") or {}
        if geometry.get("type") != "LineString":
            continue
        coords: Sequence[Sequence[float]] = geometry.get("coordinates") or []
        for i in range(len(coords) - 1):
            lng1, lat1 = coords[i]
            lng2, lat2 = coords[i + 1]
            dist = haversine_distance_m(lat1, lng1, lat2, lng2)
            if dist <= 0:
                continue
            segments.append(((lat1, lng1), (lat2, lng2)))
            weights.append(dist)

    if not segments:
        print(f"[warn] no usable road segments found in {path}, falling back to bounding-box sampling")
    else:
        print(f"[info] loaded {len(segments)} road segments from {path}")
    return segments, weights


def sample_point_on_road(
    segments: Sequence[Tuple[Tuple[float, float], Tuple[float, float]]],
    weights: Sequence[float],
) -> Optional[Tuple[float, float]]:
    """Pick a random point along the provided road segments."""
    if not segments:
        return None

    try:
        start, end = random.choices(segments, weights=weights, k=1)[0]
    except IndexError:
        return None
    t = random.random()
    lat = start[0] + (end[0] - start[0]) * t
    lng = start[1] + (end[1] - start[1]) * t
    return lat, lng
