from __future__ import annotations

from typing import Any, Dict, List

# Slightly smaller upper region to focus on the parking area
PARKING_AREA_BOX = {"x0": 0.0, "y0": 0.0, "x1": 1.0, "y1": 0.35}


def detect_parking_area_occupancy(
    vehicle_centers: List[Dict[str, Any]],
    img_w: int,
    img_h: int,
    area_box: Dict[str, float] = PARKING_AREA_BOX,
) -> List[Dict[str, Any]]:
    """
    Mark the upper region of the frame as the parking area.
    Any vehicle whose bbox intersects this area is counted as occupying it.
    Returns a single occupancy event with the vehicle count and members.
    """
    events: List[Dict[str, Any]] = []
    if img_w <= 0 or img_h <= 0:
        return events

    y_min_px = area_box["y0"] * img_h
    y_max_px = area_box["y1"] * img_h
    vehicles_in_area: List[Dict[str, Any]] = []

    for v in vehicle_centers:
        cx_px = v["cx"] * img_w
        cy_px = v["cy"] * img_h
        w_px = v.get("w", 0) * img_w
        h_px = v.get("h", 0) * img_h
        left_px = cx_px - 0.5 * w_px
        right_px = cx_px + 0.5 * w_px
        top_px = cy_px - 0.5 * h_px
        bottom_px = cy_px + 0.5 * h_px

        # Intersects the parking area box
        if bottom_px >= y_min_px and top_px <= y_max_px:
            vehicles_in_area.append(
                {
                    **v,
                    "cx_px": cx_px,
                    "cy_px": cy_px,
                    "w_px": w_px,
                    "h_px": h_px,
                    "left_px": max(0.0, left_px),
                    "right_px": min(float(img_w), right_px),
                    "top_px": max(0.0, top_px),
                    "bottom_px": min(float(img_h), bottom_px),
                }
            )

    events.append(
        {
            "event_type": "parking_area_occupancy",
            "parking_area": area_box,
            "line_y_px": y_max_px,
            "vehicle_count": len(vehicles_in_area),
            "vehicles": vehicles_in_area,
        }
    )
    return events


def detect_roadside_spots(
    vehicle_centers: List[Dict[str, Any]],
    img_w: int,
    img_h: int,
) -> List[Dict[str, Any]]:
    # Gap-based curb logic removed: this now only checks occupancy in the upper half box.
    return detect_parking_area_occupancy(vehicle_centers, img_w, img_h, PARKING_AREA_BOX)
