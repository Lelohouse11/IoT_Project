import json
import math
import random
import sys
from pathlib import Path
from typing import List, Optional, Sequence, Tuple

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from api import database

def haversine_distance_m(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """Approximate distance in meters between two lat/lng pairs."""
    r = 6371000.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = phi2 - phi1
    dlambda = math.radians(lng2 - lng1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return 2 * r * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def load_road_segments(path: Optional[Path] = None) -> Tuple[List[Tuple[Tuple[float, float], Tuple[float, float]]], List[float]]:
    """Load road line segments from the MySQL database (ignoring path if provided)."""
    segments: List[Tuple[Tuple[float, float], Tuple[float, float]]] = []
    weights: List[float] = []

    try:
        rows = database.fetch_all("SELECT lat1, lng1, lat2, lng2 FROM road_segments")
        if not rows:
            print("[warn] no road segments found in database")
            return [], []
            
        for row in rows:
            lat1, lng1 = row["lat1"], row["lng1"]
            lat2, lng2 = row["lat2"], row["lng2"]
            dist = haversine_distance_m(lat1, lng1, lat2, lng2)
            if dist <= 0:
                continue
            segments.append(((lat1, lng1), (lat2, lng2)))
            weights.append(dist)
            
        print(f"[info] loaded {len(segments)} road segments from database")
        return segments, weights

    except Exception as exc:
        print(f"[warn] failed to load road segments from db: {exc}")
        return [], []


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
