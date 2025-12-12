"""
Simple YOLOv8 nano test runner for images and videos.

Detection, double-parking events, and parking-spot availability are modularized.
"""

from __future__ import annotations

import argparse
import uuid
import sys
from pathlib import Path
from typing import Dict, Optional, List

import cv2
from ultralytics import YOLO

# Support execution both as a package module and as a standalone script.
if __package__ is None or __package__ == "":
    sys.path.append(str(Path(__file__).resolve().parent))

try:
    from yolov8_tests.double_parking import (
        DOUBLE_PARKING_STATIONARY_SEC,
        MOVE_EPS_REL,
        detect_double_parking_events,
        VEHICLE_CLASS_NAMES as VEHICLE_CLASSES_DOUBLE,
    )
    from yolov8_tests.parking_spots import (
        CURB_DISTANCE_NORM,
        DEFAULT_METERS_PER_PIXEL,
        PARKING_GAP_THRESHOLD_M,
        detect_roadside_spots,
    )
    from yolov8_tests.general_detection import (
        BASE_DIR,
        INPUT_IMAGES,
        INPUT_VIDEOS,
        OUTPUT_IMAGES,
        OUTPUT_VIDEOS,
        ZONES_CONFIG,
        IMAGE_EXTS,
        VIDEO_EXTS,
        VEHICLE_CLASS_NAMES,
        iter_files,
        utc_timestamp,
        write_metadata,
        load_zones,
        in_any_zone,
    )
except ImportError:  # fallback for direct script execution
    from double_parking import (
        DOUBLE_PARKING_STATIONARY_SEC,
        MOVE_EPS_REL,
        detect_double_parking_events,
        VEHICLE_CLASS_NAMES as VEHICLE_CLASSES_DOUBLE,
    )
    from parking_spots import (
        CURB_DISTANCE_NORM,
        DEFAULT_METERS_PER_PIXEL,
        PARKING_GAP_THRESHOLD_M,
        detect_roadside_spots,
    )
    from general_detection import (
        BASE_DIR,
        INPUT_IMAGES,
        INPUT_VIDEOS,
        OUTPUT_IMAGES,
        OUTPUT_VIDEOS,
        ZONES_CONFIG,
        IMAGE_EXTS,
        VIDEO_EXTS,
        VEHICLE_CLASS_NAMES,
        iter_files,
        utc_timestamp,
        write_metadata,
        load_zones,
        in_any_zone,
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
        default=0.25,
        help="Confidence threshold for detections.",
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
    parser.add_argument(
        "--spot-threshold-m",
        type=float,
        default=PARKING_GAP_THRESHOLD_M,
        help="Minimum gap (meters) to classify as available curbside spot.",
    )
    parser.add_argument(
        "--curb-threshold",
        type=float,
        default=CURB_DISTANCE_NORM,
        help="Normalized distance (0-1 of max image dim) to consider vehicle near curb.",
    )
    parser.add_argument(
        "--meters-per-pixel",
        type=float,
        default=None,
        help="Override calibration for converting pixels to meters along curb (optional).",
    )
    return parser.parse_args()


def run_on_images(
    model: YOLO,
    conf: float,
    device: str,
    camera_id: str,
    gps_lat: float,
    gps_lon: float,
    lanes,
    parking_zones,
    curbs,
    gap_threshold_m: float,
    curb_distance_norm: float,
    meters_per_pixel_override: Optional[float],
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
            save_path = OUTPUT_IMAGES / f"{image_path.stem}_yolov8n{image_path.suffix}"
            cv2.imwrite(str(save_path), annotated)
            detection_count = len(result.boxes)
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

            spot_events = detect_roadside_spots(
                vehicle_centers,
                curbs,
                img_w,
                img_h,
                gap_threshold_m,
                curb_distance_norm,
                meters_per_pixel_override,
            )
            if spot_events:
                spots_path = OUTPUT_IMAGES / f"{image_path.stem}_spots.json"
                payload = {
                    "event_type": "parking_spot_available",
                    "camera_id": camera_id,
                    "segment_id": image_path.stem,
                    "timestamp": utc_timestamp(),
                    "gps_position": {"lat": gps_lat, "lon": gps_lon},
                    "source_file": image_path.name,
                    "spots": spot_events,
                }
                write_metadata(spots_path, payload)
                print(f"Parking spots -> {spots_path}")


def run_on_videos(
    model: YOLO,
    conf: float,
    device: str,
    camera_id: str,
    gps_lat: float,
    gps_lon: float,
    lanes,
    parking_zones,
    curbs,
    gap_threshold_m: float,
    curb_distance_norm: float,
    meters_per_pixel_override: Optional[float],
    vehicle_class_ids: Optional[List[int]],
) -> None:
    OUTPUT_VIDEOS.mkdir(parents=True, exist_ok=True)
    video_paths = list(iter_files(INPUT_VIDEOS, VIDEO_EXTS))

    if not video_paths:
        print(f"No videos found in {INPUT_VIDEOS}.")
        return

    if not lanes:
        print("No lane zones configured (zones.json). Double parking detection will be skipped.")
    if not curbs:
        print("No curb lines configured (zones.json). Roadside spot detection will be skipped.")

    for video_path in video_paths:
        output_dir = OUTPUT_VIDEOS / video_path.stem
        output_dir.mkdir(parents=True, exist_ok=True)
        events_dir = output_dir / "events"
        events_dir.mkdir(parents=True, exist_ok=True)

        cap = cv2.VideoCapture(str(video_path))
        fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
        cap.release()

        track_state: Dict[int, Dict[str, Optional[float]]] = {}
        detection_count = 0
        max_conf = 0.0
        events_written = 0
        parking_events_written = 0
        parking_event_keys: set[tuple[int, int, int]] = set()

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

        for frame_idx, result in enumerate(stream):
            boxes = result.boxes
            img_h, img_w = result.orig_shape
            detection_count += len(boxes)
            if len(boxes) > 0:
                max_conf = max(max_conf, float(boxes.conf.max().item()))

            # Double parking detection
            if lanes and len(boxes) > 0:
                dp_events = detect_double_parking_events(
                    result=result,
                    frame_idx=frame_idx,
                    fps=fps,
                    lanes=lanes,
                    parking_zones=parking_zones,
                    track_state=track_state,
                    move_eps_rel=MOVE_EPS_REL,
                    stationary_sec=DOUBLE_PARKING_STATIONARY_SEC,
                )
                for ev in dp_events:
                    snippet_id = ev["event_id"]
                    annotated_frame = ev.pop("annotated_frame")
                    frame_path = events_dir / f"{snippet_id}.jpg"
                    cv2.imwrite(str(frame_path), annotated_frame)

                    meta = {
                        "event_type": "double_parking",
                        "camera_id": camera_id,
                        "segment_id": video_path.stem,
                        "timestamp": utc_timestamp(),
                        "gps_position": {"lat": gps_lat, "lon": gps_lon},
                        "snippet_id": snippet_id,
                        "video_id": snippet_id,
                        "source_file": video_path.name,
                        "output_dir": str(output_dir.name),
                        "detections": detection_count,
                        **{k: v for k, v in ev.items() if k != "event_id"},
                    }
                    meta_path = events_dir / f"{snippet_id}.json"
                    write_metadata(meta_path, meta)
                    events_written += 1
                    print(f"Double parking event -> {meta_path}")

            # Roadside parking spot detection per frame
            if curbs and len(boxes) > 0:
                annotated_frame = None
                vehicle_centers = []
                names = result.names
                for i in range(len(boxes)):
                    cls_id = int(boxes.cls[i].item())
                    cls_name = names.get(cls_id, "")
                    if cls_name not in VEHICLE_CLASSES_DOUBLE:
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

                spot_events = detect_roadside_spots(
                    vehicle_centers,
                    curbs,
                    img_w,
                    img_h,
                    gap_threshold_m,
                    curb_distance_norm,
                    meters_per_pixel_override,
                )
                if spot_events:
                    if annotated_frame is None:
                        annotated_frame = result.plot()
                    for ev in spot_events:
                        key = (
                            ev["curb_index"],
                            int(ev["start_meters"] * 10),
                            int(ev["end_meters"] * 10),
                        )
                        if key in parking_event_keys:
                            continue
                        parking_event_keys.add(key)
                        snippet_id = uuid.uuid4().hex
                        frame_path = events_dir / f"{snippet_id}_spot.jpg"
                        cv2.imwrite(str(frame_path), annotated_frame)
                        meta = {
                            **ev,
                            "event_type": "parking_spot_available",
                            "camera_id": camera_id,
                            "segment_id": video_path.stem,
                            "timestamp": utc_timestamp(),
                            "gps_position": {"lat": gps_lat, "lon": gps_lon},
                            "snippet_id": snippet_id,
                            "video_frame": frame_idx,
                            "source_file": video_path.name,
                            "output_dir": str(output_dir.name),
                        }
                        meta_path = events_dir / f"{snippet_id}_spot.json"
                        write_metadata(meta_path, meta)
                        parking_events_written += 1
                        print(f"Parking spot available -> {meta_path}")

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
            "double_parking_events": events_written,
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

    lanes, parking_zones, curbs = load_zones(ZONES_CONFIG)

    if run_images:
        run_on_images(
            model,
            args.conf,
            args.device,
            args.camera_id,
            args.gps_lat,
            args.gps_lon,
            lanes,
            parking_zones,
            curbs,
            args.spot_threshold_m,
            args.curb_threshold,
            args.meters_per_pixel,
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
            lanes,
            parking_zones,
            curbs,
            args.spot_threshold_m,
            args.curb_threshold,
            args.meters_per_pixel,
            vehicle_class_ids,
        )


if __name__ == "__main__":
    main()
