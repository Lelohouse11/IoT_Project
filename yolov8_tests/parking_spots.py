from __future__ import annotations

import math
from typing import Any, Dict, List, Optional, Tuple

DEFAULT_METERS_PER_PIXEL = 0.05  # fallback if no calibration is provided
PARKING_GAP_THRESHOLD_M = 5.5  # meters
CURB_DISTANCE_NORM = 0.05  # 5% of max(img_w, img_h)


def point_line_distance_with_t(point_px: Tuple[float, float], a_px: Tuple[float, float], b_px: Tuple[float, float]) -> Tuple[float, float]:
    ax, ay = a_px
    bx, by = b_px
    px, py = point_px
    vx, vy = bx - ax, by - ay
    seg_len_sq = vx * vx + vy * vy
    if seg_len_sq == 0:
        return float("inf"), 0.0
    t = ((px - ax) * vx + (py - ay) * vy) / seg_len_sq
    t_clamped = max(0.0, min(1.0, t))
    proj_x = ax + t_clamped * vx
    proj_y = ay + t_clamped * vy
    dist = math.hypot(px - proj_x, py - proj_y)
    return dist, t_clamped


def detect_roadside_spots(
    vehicle_centers: List[Dict[str, Any]],
    curbs: List[Dict[str, Any]],
    img_w: int,
    img_h: int,
    gap_threshold_m: float,
    curb_distance_norm: float,
    meters_per_pixel_override: Optional[float],
) -> List[Dict[str, Any]]:
    events: List[Dict[str, Any]] = []
    if not curbs or not vehicle_centers:
        return events

    curb_distance_px = curb_distance_norm * max(img_w, img_h)

    for curb_idx, curb in enumerate(curbs):
        pts_norm = curb["points"]
        a_n = pts_norm[0]
        b_n = pts_norm[-1]
        a_px = (a_n[0] * img_w, a_n[1] * img_h)
        b_px = (b_n[0] * img_w, b_n[1] * img_h)
        length_px = math.hypot(b_px[0] - a_px[0], b_px[1] - a_px[1])
        if length_px < 1.0:
            continue

        mpp = meters_per_pixel_override
        if mpp is None:
            mpp = curb.get("meters_per_pixel") or DEFAULT_METERS_PER_PIXEL
        gap_threshold_px = gap_threshold_m / mpp

        projected: List[Tuple[float, float, Dict[str, Any]]] = []
        # Unit direction of curb line
        dir_x = (b_px[0] - a_px[0]) / length_px
        dir_y = (b_px[1] - a_px[1]) / length_px
        for v in vehicle_centers:
            cx_px = v["cx"] * img_w
            cy_px = v["cy"] * img_h
            dist, t = point_line_distance_with_t((cx_px, cy_px), a_px, b_px)
            if dist <= curb_distance_px and 0.0 <= t <= 1.0:
                # Project bbox extent onto curb direction to avoid overestimating gap
                w_px = v.get("w", 0) * img_w
                h_px = v.get("h", 0) * img_h
                extent_along = 0.5 * (abs(dir_x) * w_px + abs(dir_y) * h_px)
                projected.append((t * length_px, extent_along, {**v, "t": t, "dist_px": dist, "extent_px": extent_along}))

        if not projected:
            continue

        projected.sort(key=lambda x: x[0])
        centers = [p[0] for p in projected]
        extents = [p[1] for p in projected]

        gaps = []
        # Start gap: from curb start (0) to first vehicle leading edge
        first_start = max(0.0, centers[0] - extents[0])
        gaps.append((0.0, first_start, None, projected[0][2]))

        for i in range(len(projected) - 1):
            end_current = centers[i] + extents[i]
            start_next = max(0.0, centers[i + 1] - extents[i + 1])
            gaps.append((end_current, start_next, projected[i][2], projected[i + 1][2]))

        last_end = min(length_px, centers[-1] + extents[-1])
        gaps.append((last_end, length_px, projected[-1][2], None))

        for start_px, end_px, left_v, right_v in gaps:
            gap_px = end_px - start_px
            if gap_px <= gap_threshold_px:
                continue
            gap_m = gap_px * mpp
            events.append(
                {
                    "event_type": "parking_spot_available",
                    "curb_index": curb_idx,
                    "gap_meters": gap_m,
                    "gap_pixels": gap_px,
                    "gap_threshold_m": gap_threshold_m,
                    "gap_threshold_px": gap_threshold_px,
                    "start_meters": start_px * mpp,
                    "end_meters": end_px * mpp,
                    "start_px": start_px,
                    "end_px": end_px,
                    "left_vehicle": left_v,
                    "right_vehicle": right_v,
                    "meters_per_pixel_used": mpp,
                }
            )

    return events
