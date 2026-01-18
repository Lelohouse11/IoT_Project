"""
YOLOv8 processor module for edge detection.
Handles video/image processing with YOLOv8 tracking.
"""

import cv2
from pathlib import Path
from typing import Iterator, Dict, Any, List, Optional
from ultralytics import YOLO
import logging

logger = logging.getLogger(__name__)


class YOLOProcessor:
    """YOLOv8 inference engine with tracking support."""

    def __init__(self, model_path: str = "yolov8n.pt", device: str = "cpu"):
        """
        Initialize YOLO processor.

        Args:
            model_path: Path to YOLOv8 model (default: nano for edge devices)
            device: Device to run on ("cpu" or "cuda:0")
        """
        # Resolve model path relative to edge_detection folder to avoid auto-download to project root
        resolved_path = Path(model_path)
        if not resolved_path.is_absolute():
            # If relative path, resolve relative to edge_detection folder
            edge_detection_dir = Path(__file__).parent.parent
            resolved_path = edge_detection_dir / model_path
        
        self.model = YOLO(str(resolved_path))
        self.model.to(device)
        self.device = device

    def process_video(
        self,
        video_path: Path,
        conf: float = 0.5,
    ) -> Iterator[Dict[str, Any]]:
        """
        Process video with YOLOv8 tracking.

        Args:
            video_path: Path to video file
            conf: Confidence threshold for detections

        Yields:
            Dictionary containing:
                - frame_idx: Frame number
                - frame: Raw BGR frame
                - timestamp: Frame timestamp in milliseconds
                - detections: List of detected vehicles with track IDs
                - img_h, img_w: Frame dimensions
        """
        try:
            cap = cv2.VideoCapture(str(video_path))
            if not cap.isOpened():
                logger.error(f"Failed to open video: {video_path}")
                return

            fps = cap.get(cv2.CAP_PROP_FPS) or 30
            frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            
            # Process at ~10fps (skip frames for performance)
            frame_skip = max(1, int(fps / 10))
            
            frame_idx = 0
            while frame_idx < frame_count:
                ret, frame = cap.read()
                if not ret:
                    break

                # Skip frames to achieve ~10fps processing
                if frame_idx % frame_skip != 0:
                    frame_idx += 1
                    continue

                # Get timestamp in milliseconds
                timestamp_ms = cap.get(cv2.CAP_PROP_POS_MSEC)

                # Run tracking
                results = self.model.track(
                    source=frame,
                    conf=conf,
                    device=self.device,
                    persist=True,
                    tracker="bytetrack.yaml",
                    verbose=False,
                )

                img_h, img_w = frame.shape[:2]
                detections = []

                if results:
                    result = results[0]
                    boxes = result.boxes

                    for i in range(len(boxes)):
                        # Extract track ID
                        track_id = None
                        if boxes.id is not None:
                            track_id = int(boxes.id[i].item())

                        # Get normalized center coordinates and dimensions
                        cx, cy, bw, bh = boxes.xywh[i].tolist()
                        confidence = float(boxes.conf[i].item())
                        class_id = int(boxes.cls[i].item())
                        class_name = result.names[class_id]
                        
                        # Get bbox coordinates (x1, y1, x2, y2)
                        x1, y1, x2, y2 = boxes.xyxy[i].tolist()

                        # Convert to pixel coordinates (absolute)
                        det = {
                            "track_id": track_id,
                            "class_name": class_name,
                            "class_id": class_id,
                            "cx": int(cx),  # Center x in pixels
                            "cy": int(cy),  # Center y in pixels
                            "w": int(bw),   # Width in pixels
                            "h": int(bh),   # Height in pixels
                            "bbox": [int(x1), int(y1), int(x2), int(y2)],  # Bounding box
                            "bbox_norm": [x1/img_w, y1/img_h, x2/img_w, y2/img_h],  # Normalized bbox
                            "cx_norm": cx / img_w,  # Normalized center x
                            "cy_norm": cy / img_h,  # Normalized center y
                            "w_norm": bw / img_w,   # Normalized width
                            "h_norm": bh / img_h,   # Normalized height
                            "confidence": confidence,
                        }
                        detections.append(det)

                yield {
                    "frame_idx": frame_idx,
                    "frame": frame,
                    "timestamp_ms": timestamp_ms,
                    "detections": detections,
                    "img_h": img_h,
                    "img_w": img_w,
                    "fps": fps,
                }

                frame_idx += 1

            cap.release()

        except Exception as e:
            logger.error(f"Error processing video {video_path}: {e}")
            raise

    def process_image(self, image_path: Path, conf: float = 0.5) -> Dict[str, Any]:
        """
        Process single image with YOLO detection.

        Args:
            image_path: Path to image file
            conf: Confidence threshold

        Returns:
            Dictionary with frame, detections, and dimensions
        """
        frame = cv2.imread(str(image_path))
        if frame is None:
            raise ValueError(f"Failed to load image: {image_path}")

        results = self.model.predict(
            source=frame,
            conf=conf,
            device=self.device,
            verbose=False,
        )

        img_h, img_w = frame.shape[:2]
        detections = []

        if results:
            result = results[0]
            boxes = result.boxes

            for i in range(len(boxes)):
                cx, cy, bw, bh = boxes.xywh[i].tolist()
                confidence = float(boxes.conf[i].item())
                class_id = int(boxes.cls[i].item())
                class_name = result.names[class_id]
                
                # Get bbox coordinates
                x1, y1, x2, y2 = boxes.xyxy[i].tolist()

                det = {
                    "track_id": None,  # No tracking for single image
                    "class_name": class_name,
                    "class_id": class_id,
                    "cx": int(cx),
                    "cy": int(cy),
                    "w": int(bw),
                    "h": int(bh),
                    "bbox": [int(x1), int(y1), int(x2), int(y2)],
                    "bbox_norm": [x1/img_w, y1/img_h, x2/img_w, y2/img_h],
                    "cx_norm": cx / img_w,
                    "cy_norm": cy / img_h,
                    "w_norm": bw / img_w,
                    "h_norm": bh / img_h,
                    "confidence": confidence,
                }
                detections.append(det)

        return {
            "frame": frame,
            "detections": detections,
            "img_h": img_h,
            "img_w": img_w,
        }
