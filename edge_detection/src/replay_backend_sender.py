"""
Replay detection events from outputs/detection_test and send to backend using BackendSender.
Maps edge event types to backend-supported types and builds minimal metadata.

Usage:
  python -m edge_detection.src.replay_backend_sender --folder edge_detection/outputs/detection_test \
      --backend-url http://localhost:8003/api/camera

Environment variables:
  BACKEND_URL (fallback if --backend-url not provided)
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Dict, Any, List

from .backend_sender import BackendSender

SUPPORTED_EVENT_TYPES = {
    "traffic_monitoring": "traffic_monitoring",
    "double_parking_violation": "double_parking",
    "red_light_violation": "red_light_violation",
    # parking events mapped to parking_status to let VLM infer free spots
    "parking_entry": "parking_status",
    "parking_exit": "parking_status",
}


def build_metadata_from_detection(det: Dict[str, Any]) -> Dict[str, Any]:
    meta: Dict[str, Any] = {}
    if det:
        bbox = det.get("bbox")
        if bbox and isinstance(bbox, list) and len(bbox) == 4:
            x1, y1, x2, y2 = bbox
            meta["bbox"] = {"x": x1, "y": y1, "w": x2 - x1, "h": y2 - y1}
        conf = det.get("confidence")
        if conf is not None:
            meta["confidence"] = float(conf)
    return meta


def load_events_from_folder(folder: Path) -> List[Dict[str, Any]]:
    events: List[Dict[str, Any]] = []
    for json_file in sorted(folder.glob("*.json")):
        with open(json_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        event_type_raw = data.get("event_type")
        mapped_type = SUPPORTED_EVENT_TYPES.get(event_type_raw)
        if not mapped_type:
            # skip unsupported types
            continue
        camera_id = data.get("camera_id")
        # Always use current backend-side timestamp; ignore file timestamp
        image_file = data.get("image_file")
        if not image_file:
            # derive from json name
            image_file = json_file.with_suffix(".jpg").name
        image_path = (json_file.parent / image_file)
        # use first detection for optional metadata
        first_det = None
        dets = data.get("detections")
        if isinstance(dets, list) and dets:
            first_det = dets[0]
        metadata = build_metadata_from_detection(first_det or {})

        events.append(
            {
                "camera_id": camera_id,
                "event_type": mapped_type,
                "frame": str(image_path),
                "metadata": metadata,
                # Do not pass a timestamp so the sender uses 'now' in UTC
            }
        )
    return events


def main() -> int:
    parser = argparse.ArgumentParser(description="Replay detection_test events to backend")
    parser.add_argument(
        "--folder",
        type=str,
        default=str(Path(__file__).resolve().parents[2] / "outputs" / "detection_test"),
        help="Folder with detection_test JSON/JPG files",
    )
    parser.add_argument(
        "--backend-url",
        type=str,
        default=os.getenv("BACKEND_URL", "http://localhost:8003/api/camera"),
        help="Backend base URL (e.g., http://localhost:8003/api/camera)",
    )
    args = parser.parse_args()

    folder = Path(args.folder)
    if not folder.exists():
        print(f"Folder not found: {folder}")
        return 2

    sender = BackendSender(args.backend_url)
    if not sender.check_health():
        print(f"Backend not healthy at {args.backend_url}")
        return 3

    events = load_events_from_folder(folder)
    if not events:
        print("No events found to send.")
        return 0

    result = sender.send_events_batch(events)
    print(f"Sent: {result['sent']}, Dropped: {result['dropped']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
