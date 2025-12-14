"""
Simple YOLOv8 nano test runner for images and videos.

Detection, double-parking events, and parking-spot availability are modularized.
"""

from __future__ import annotations

import argparse
import logging
import uuid
import sys
from pathlib import Path
from typing import Optional, List

import cv2
from ultralytics import YOLO
try:
    from ultralytics.utils import LOGGER as ULTRA_LOGGER
except Exception:
    ULTRA_LOGGER = None

# Support execution both as a package module and as a standalone script.
if __package__ is None or __package__ == "":
    sys.path.append(str(Path(__file__).resolve().parent))

if ULTRA_LOGGER is not None:
    ULTRA_LOGGER.setLevel(logging.ERROR)

try:
    from yolov8_tests.parking_spots import (
        PARKING_AREA_BOX,
        detect_roadside_spots,
    )
    from yolov8_tests.general_detection import (
        INPUT_IMAGES,
        INPUT_VIDEOS,
        OUTPUT_IMAGES,
        OUTPUT_VIDEOS,
        IMAGE_EXTS,
        VIDEO_EXTS,
        VEHICLE_CLASS_NAMES,
        iter_files,
        utc_timestamp,
        write_metadata,
    )
except ImportError:  # fallback for direct script execution
    from parking_spots import (
        PARKING_AREA_BOX,
        detect_roadside_spots,
    )
    from general_detection import (
        INPUT_IMAGES,
        INPUT_VIDEOS,
        OUTPUT_IMAGES,
        OUTPUT_VIDEOS,
        IMAGE_EXTS,
        VIDEO_EXTS,
        VEHICLE_CLASS_NAMES,
        iter_files,
        utc_timestamp,
        write_metadata,
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run YOLOv8 nano on local images/videos."
    )
    parser.add_argument(
        "--device",
        default="cpu",
        help="e.g. cpu, cuda:0. Falls back to CPU if no GPU driver is available.",
    )
    parser.add_argument(
        "--conf",
        type=float,
        default=0.15,
        help="Confidence threshold for detections (lower -> more boxes).",
    )
    parser.add_argument(
        "--images",
        action="store_true",
        help="Process images only (default: images and videos).",
    )
    parser.add_argument(
        "--videos",
        action="store_true",
        help="Process videos only (default: images and videos).",
    )
    parser.add_argument(
        "--camera-id",
        default="cam-01",
        help="Camera identifier used in event metadata.",
    )
    parser.add_argument(
        "--gps-lat",
        type=float,
        default=0.0,
        help="GPS latitude for metadata.",
    )
    parser.add_argument(
        "--gps-lon",
        type=float,
        default=0.0,
        help="GPS longitude for metadata.",
    )
    return parser.parse_args()


def draw_parking_area_overlay(image, line_y_px: float, label: str = "Parking area (top region)") -> None:
    """Draw the full parking area box (top region) with a highlighted bottom edge."""
    y_bottom = int(round(line_y_px))
    color = (0, 255, 255)  # yellow
    thickness = 2
    # Draw rectangle covering the parking area (top portion of the frame)
    cv2.rectangle(image, (0, 0), (image.shape[1] - 1, y_bottom), color, thickness)
    # Emphasize the bottom edge
    cv2.line(image, (0, y_bottom), (image.shape[1] - 1, y_bottom), color, thickness + 1)
    cv2.putText(
        image,
        label,
        (10, max(20, y_bottom - 10)),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.7,
        color,
        2,
        cv2.LINE_AA,
    )


def run_on_images(
    model: YOLO,
    conf: float,
    device: str,
    camera_id: str,
    gps_lat: float,
    gps_lon: float,
    vehicle_class_ids: Optional[List[int]],
) -> None:
    OUTPUT_IMAGES.mkdir(parents=True, exist_ok=True)
    image_paths = list(iter_files(INPUT_IMAGES, IMAGE_EXTS))

    if not image_paths:
        print(f"No images found in {INPUT_IMAGES}.")
        return

    for image_path in image_paths:
        results = model.predict(source=str(image_path), conf=conf, device=device, classes=vehicle_class_ids)
        for result in results:
            annotated = result.plot()  # BGR-Array
            detection_count = len(result.boxes)

            names = result.names
            vehicle_centers = []
            img_h, img_w = result.orig_shape
            for i in range(len(result.boxes)):
                cls_id = int(result.boxes.cls[i].item())
                cls_name = names.get(cls_id, "")
                if cls_name not in VEHICLE_CLASS_NAMES:
                    continue
                cx, cy, bw, bh = result.boxes.xywh[i].tolist()
                vehicle_centers.append(
                    {
                        "cx": cx / img_w,
                        "cy": cy / img_h,
                        "w": bw / img_w,
                        "h": bh / img_h,
                        "conf": float(result.boxes.conf[i].item()),
                        "class": cls_name,
                    }
                )

            occupancy_events = detect_roadside_spots(
                vehicle_centers,
                img_w,
                img_h,
            )
            line_y_px = img_h * PARKING_AREA_BOX["y1"]
            if occupancy_events:
                # Use the line position from the detector if present
                line_y_px = occupancy_events[0].get("line_y_px", line_y_px)

            draw_parking_area_overlay(annotated, line_y_px)

            save_path = OUTPUT_IMAGES / f"{image_path.stem}_yolov8n{image_path.suffix}"
            cv2.imwrite(str(save_path), annotated)
            print(f"{image_path.name}: {detection_count} objects -> {save_path}")

            if detection_count > 0:
                confidence = float(result.boxes.conf.max().item())
                snippet_id = uuid.uuid4().hex
                meta = {
                    "event_type": "vehicle_detected",
                    "camera_id": camera_id,
                    "segment_id": image_path.stem,
                    "timestamp": utc_timestamp(),
                    "gps_position": {"lat": gps_lat, "lon": gps_lon},
                    "severity": confidence,
                    "snippet_id": snippet_id,
                    "image_id": snippet_id,
                    "source_file": image_path.name,
                    "output_file": save_path.name,
                }
                meta_path = OUTPUT_IMAGES / f"{image_path.stem}_yolov8n.json"
                write_metadata(meta_path, meta)
                print(f"Metadata -> {meta_path}")

            if occupancy_events:
                occupancy_path = OUTPUT_IMAGES / f"{image_path.stem}_parking_area.json"
                payload = {
                    "event_type": "parking_area_occupancy",
                    "camera_id": camera_id,
                    "segment_id": image_path.stem,
                    "timestamp": utc_timestamp(),
                    "gps_position": {"lat": gps_lat, "lon": gps_lon},
                    "source_file": image_path.name,
                    **occupancy_events[0],
                }
                write_metadata(occupancy_path, payload)
                print(f"Parking area occupancy -> {occupancy_path}")


def run_on_videos(
    model: YOLO,
    conf: float,
    device: str,
    camera_id: str,
    gps_lat: float,
    gps_lon: float,
    vehicle_class_ids: Optional[List[int]],
) -> None:
    OUTPUT_VIDEOS.mkdir(parents=True, exist_ok=True)
    video_paths = list(iter_files(INPUT_VIDEOS, VIDEO_EXTS))

    if not video_paths:
        print(f"No videos found in {INPUT_VIDEOS}.")
        return

    for video_path in video_paths:
        output_dir = OUTPUT_VIDEOS / video_path.stem
        output_dir.mkdir(parents=True, exist_ok=True)
        events_dir = output_dir / "events"
        events_dir.mkdir(parents=True, exist_ok=True)

        cap = cv2.VideoCapture(str(video_path))
        fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
        cap.release()

        detection_count = 0
        max_conf = 0.0
        parking_events_written = 0
        parking_event_keys: set[int] = set()  # track_ids that already emitted
        track_state: dict[int, dict[str, float]] = {}

        stream = model.track(
            source=str(video_path),
            conf=conf,
            device=device,
            save=True,
            project=str(OUTPUT_VIDEOS),
            name=video_path.stem,
            exist_ok=True,
            stream=True,
            tracker="bytetrack.yaml",
            persist=True,
            classes=vehicle_class_ids,
        )

        move_eps_rel = 0.01  # 1% of max dimension
        min_stationary_sec = 3.0

        for frame_idx, result in enumerate(stream):
            boxes = result.boxes
            img_h, img_w = result.orig_shape
            detection_count += len(boxes)
            if len(boxes) > 0:
                max_conf = max(max_conf, float(boxes.conf.max().item()))

            # Parking area occupancy per frame (upper half of the image)
            if len(boxes) > 0:
                annotated_frame = None
                vehicle_centers = []
                names = result.names
                for i in range(len(boxes)):
                    cls_id = int(boxes.cls[i].item())
                    cls_name = names.get(cls_id, "")
                    if cls_name not in VEHICLE_CLASS_NAMES:
                        continue
                    cx, cy, bw, bh = boxes.xywh[i].tolist()
                    track_id_tensor = boxes.id
                    track_id_val = int(track_id_tensor[i].item()) if track_id_tensor is not None else None
                    vehicle_centers.append(
                        {
                            "cx": cx / img_w,
                            "cy": cy / img_h,
                            "w": bw / img_w,
                            "h": bh / img_h,
                            "conf": float(boxes.conf[i].item()),
                            "class": cls_name,
                            "track_id": track_id_val,
                    }
                )

                occupancy_events = detect_roadside_spots(vehicle_centers, img_w, img_h)
                if occupancy_events:
                    ev = occupancy_events[0]
                    vehicles_in_area = ev.get("vehicles", [])
                    if vehicles_in_area:
                        annotated_frame = annotated_frame or result.plot()
                        line_y_px = ev.get("line_y_px", img_h * PARKING_AREA_BOX["y1"])
                        draw_parking_area_overlay(annotated_frame, line_y_px)
                        move_eps = move_eps_rel * max(img_w, img_h)
                        for v in vehicles_in_area:
                            tid = v.get("track_id")
                            if tid is None:
                                continue
                            cx_px = v.get("cx_px", v["cx"] * img_w)
                            cy_px = v.get("cy_px", v["cy"] * img_h)
                            state = track_state.get(tid, {"last_x": cx_px, "last_y": cy_px, "stationary_start": frame_idx})
                            dist = ((cx_px - state["last_x"]) ** 2 + (cy_px - state["last_y"]) ** 2) ** 0.5
                            if dist > move_eps:
                                # Reset stationary timer
                                state["stationary_start"] = frame_idx
                                state["last_x"] = cx_px
                                state["last_y"] = cy_px
                                track_state[tid] = state
                                continue

                            # stationary long enough?
                            elapsed_sec = (frame_idx - state["stationary_start"]) / fps if fps else 0.0
                            track_state[tid] = state
                            if elapsed_sec >= min_stationary_sec and tid not in parking_event_keys:
                                parking_event_keys.add(tid)
                                snippet_id = uuid.uuid4().hex
                                frame_path = events_dir / f"{snippet_id}_parking.jpg"
                                cv2.imwrite(str(frame_path), annotated_frame)
                                meta = {
                                    **ev,
                                    "event_type": ev.get("event_type", "parking_area_occupancy"),
                                    "camera_id": camera_id,
                                    "segment_id": video_path.stem,
                                    "timestamp": utc_timestamp(),
                                    "gps_position": {"lat": gps_lat, "lon": gps_lon},
                                    "snippet_id": snippet_id,
                                    "video_frame": frame_idx,
                                    "source_file": video_path.name,
                                    "output_dir": str(output_dir.name),
                                    "trigger_track_id": tid,
                                    "stationary_seconds": elapsed_sec,
                                }
                                meta_path = events_dir / f"{snippet_id}_parking.json"
                                write_metadata(meta_path, meta)
                                parking_events_written += 1
                                print(f"Parking area occupancy -> {meta_path}")

        video_meta = {
            "event_type": "vehicle_detected",
            "camera_id": camera_id,
            "segment_id": video_path.stem,
            "timestamp": utc_timestamp(),
            "gps_position": {"lat": gps_lat, "lon": gps_lon},
            "severity": max_conf,
            "video_id": uuid.uuid4().hex,
            "source_file": video_path.name,
            "output_dir": str((OUTPUT_VIDEOS / video_path.stem).name),
            "detections": detection_count,
            "parking_spot_events": parking_events_written,
        }
        meta_path = output_dir / "metadata.json"
        write_metadata(meta_path, video_meta)
        print(f"{video_path.name}: results saved to {output_dir}")
        print(f"Metadata -> {meta_path}")


def main() -> None:
    args = parse_args()
    run_images = args.images or not (args.images or args.videos)
    run_videos = args.videos or not (args.images or args.videos)

    model = YOLO("yolov8n.pt")
    model.to(args.device)
    vehicle_class_ids = [i for i, name in model.names.items() if name in VEHICLE_CLASS_NAMES]

    INPUT_IMAGES.mkdir(parents=True, exist_ok=True)
    INPUT_VIDEOS.mkdir(parents=True, exist_ok=True)

    if run_images:
        run_on_images(
            model,
            args.conf,
            args.device,
            args.camera_id,
            args.gps_lat,
            args.gps_lon,
            vehicle_class_ids,
        )
    if run_videos:
        run_on_videos(
            model,
            args.conf,
            args.device,
            args.camera_id,
            args.gps_lat,
            args.gps_lon,
            vehicle_class_ids,
        )


if __name__ == "__main__":
    main()
