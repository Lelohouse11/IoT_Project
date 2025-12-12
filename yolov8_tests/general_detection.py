from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable, List, Tuple


BASE_DIR = Path(__file__).resolve().parent
INPUT_IMAGES = BASE_DIR / "inputs" / "images"
INPUT_VIDEOS = BASE_DIR / "inputs" / "videos"
OUTPUT_IMAGES = BASE_DIR / "outputs" / "images"
OUTPUT_VIDEOS = BASE_DIR / "outputs" / "videos"
ZONES_CONFIG = BASE_DIR / "zones.json"

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}
VIDEO_EXTS = {".mp4", ".mov", ".avi", ".mkv", ".m4v"}

# COCO vehicle classes used by YOLOv8n
VEHICLE_CLASS_NAMES = {"car", "truck", "bus", "motorcycle", "motorbike", "bicycle", "van"}


def iter_files(folder: Path, exts: set[str]) -> Iterable[Path]:
    for path in sorted(folder.glob("*")):
        if path.is_file() and path.suffix.lower() in exts:
            yield path


def utc_timestamp() -> str:
    from datetime import datetime, timezone

    return datetime.now(timezone.utc).isoformat()


def write_metadata(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def load_zones(config_path: Path) -> tuple[List[List[Tuple[float, float]]], List[List[Tuple[float, float]]], list]:
    """
    Zones file format (normalized coordinates 0-1):
    {
      "lanes": [ [[x,y], [x,y], ...], ... ],
      "parking_zones": [ [[x,y], ...], ... ],
      "curbs": [
         {"points": [[x,y],[x,y]], "meters_per_pixel": 0.05}
      ]
    }
    """
    if not config_path.exists():
        return [], [], []
    with config_path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    lanes = [[(float(x), float(y)) for x, y in poly] for poly in data.get("lanes", [])]
    parking = [[(float(x), float(y)) for x, y in poly] for poly in data.get("parking_zones", [])]
    curbs_raw = data.get("curbs", [])
    curbs = []
    for c in curbs_raw:
        pts = c.get("points", [])
        if len(pts) < 2:
            continue
        curbs.append(
            {
                "points": [(float(x), float(y)) for x, y in pts],
                "meters_per_pixel": float(c.get("meters_per_pixel")) if c.get("meters_per_pixel") is not None else None,
            }
        )
    return lanes, parking, curbs


def point_in_polygon(point: Tuple[float, float], polygon: List[Tuple[float, float]]) -> bool:
    """Ray casting algorithm for point-in-polygon."""
    x, y = point
    inside = False
    n = len(polygon)
    for i in range(n):
        x1, y1 = polygon[i]
        x2, y2 = polygon[(i + 1) % n]
        if ((y1 > y) != (y2 > y)) and (x < (x2 - x1) * (y - y1) / (y2 - y1 + 1e-9) + x1):
            inside = not inside
    return inside


def in_any_zone(point: Tuple[float, float], zones: List[List[Tuple[float, float]]]) -> bool:
    return any(point_in_polygon(point, poly) for poly in zones)
