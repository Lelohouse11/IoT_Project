from __future__ import annotations

import math
import uuid
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import cv2

if __package__ is None or __package__ == "":
    sys.path.append(str(Path(__file__).resolve().parent))

try:
    from yolov8_tests.general_detection import in_any_zone
except ImportError:
    from general_detection import in_any_zone

DOUBLE_PARKING_STATIONARY_SEC = 20.0
MOVE_EPS_REL = 0.01  # relative movement threshold to consider "stationary" (1% of frame)
VEHICLE_CLASS_NAMES = {"car", "truck", "bus", "motorcycle", "motorbike", "bicycle", "van"}


def detect_double_parking_events(
    result: Any,
    frame_idx: int,
    fps: float,
    lanes: List[List[Tuple[float, float]]],
    parking_zones: List[List[Tuple[float, float]]],
    track_state: Dict[int, Dict[str, Any]],
    move_eps_rel: float = MOVE_EPS_REL,
    stationary_sec: float = DOUBLE_PARKING_STATIONARY_SEC,
) -> List[Dict[str, Any]]:
    events: List[Dict[str, Any]] = []
    boxes = result.boxes
    img_h, img_w = result.orig_shape
    move_eps = move_eps_rel * max(img_w, img_h)
    names = result.names

    for i in range(len(boxes)):
        cls_id = int(boxes.cls[i].item())
        cls_name = names.get(cls_id, "")
        if cls_name not in VEHICLE_CLASS_NAMES:
            continue

        track_id_tensor = boxes.id
        if track_id_tensor is None:
            continue
        track_id = int(track_id_tensor[i].item())

        cx, cy, bw, bh = boxes.xywh[i].tolist()
        center_rel = (cx / img_w, cy / img_h)

        in_lane = in_any_zone(center_rel, lanes)
        in_parking = in_any_zone(center_rel, parking_zones)

        if not in_lane or in_parking:
            continue

        frame_time = frame_idx / fps
        state = track_state.get(track_id)
        if state is None:
            state = {
                "first_seen": frame_time,
                "last_move": frame_time,
                "last_pos": (cx, cy),
                "event_emitted": False,
            }
            track_state[track_id] = state

        last_pos = state["last_pos"]
        dist = math.hypot(cx - last_pos[0], cy - last_pos[1])
        if dist > move_eps:
            state["last_move"] = frame_time
            state["last_pos"] = (cx, cy)

        stationary_time = frame_time - state["last_move"]
        if stationary_time >= stationary_sec and not state["event_emitted"]:
            annotated_frame = result.plot()
            state["event_emitted"] = True
            events.append(
                {
                    "track_id": track_id,
                    "stationary_seconds": stationary_time,
                    "bbox": {"cx": cx, "cy": cy, "w": bw, "h": bh},
                    "severity": float(boxes.conf[i].item()),
                    "annotated_frame": annotated_frame,
                    "event_id": uuid.uuid4().hex,
                }
            )

    return events
