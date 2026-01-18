"""
Edge Detection - Full Detection Testing
Tests the complete detection pipeline and saves events to output folder instead of sending to backend.
"""

import json
import os
from datetime import datetime
from pathlib import Path
import cv2
import numpy as np
import uuid
import traceback

from src.yolo_processor import YOLOProcessor
from src.zone_detector import ZoneDetector
from src.stationary_tracker import StationaryTracker
from src.parking_tracker import ParkingTracker
from src.traffic_light_detector import TrafficLightDetector
from src.red_light_violation_tracker import RedLightViolationTracker
from src.traffic_monitoring_tracker import TrafficMonitoringTracker
from src.config import Config, get_camera_id_from_filename, load_camera_zones


class DetectionTester:
    """Test detection pipeline and save events locally."""
    
    def __init__(self, output_dir: str = "edge_detection/outputs/detection_test"):
        self.config = Config()
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        self.yolo_processor = YOLOProcessor(
            model_path=self.config.get("model_path"),
            device=self.config.get("device")
        )
        zones_config = load_camera_zones(Path("edge_detection/zones/zones.json"))
        self.zone_detector = ZoneDetector(zones_config)
        self.stationary_tracker = StationaryTracker(
            epsilon_px=self.config.get("stationary_epsilon_px"),
            fps=self.config.get("fps")
        )
        
        self.parking_threshold = self.config.get("parking_stationary_duration")
        self.double_parking_threshold = self.config.get("double_parking_stationary_duration")
        self.event_counter = 0
        
        # Tracking components
        self.parking_tracker = ParkingTracker(
            exit_cooldown_sec=10.0,
            exit_debounce_frames=100
        )
        self.traffic_light_detector = TrafficLightDetector()
        self.red_light_violation_tracker = RedLightViolationTracker(cooldown_sec=30.0)
        
        # Traffic monitoring interval should be adjusted for the video frame rate
        # since YOLOProcessor returns actual video frame indices
        fps = self.config.get("fps", 25)
        traffic_interval_seconds = self.config.get("traffic_monitoring_interval", 60)
        self.traffic_monitoring_tracker = TrafficMonitoringTracker(
            interval_frames=int(traffic_interval_seconds * fps)
        )
        
    def save_event(self, event_type: str, camera_id: str, zone_name: str, 
                   frame, detections: list, metadata: dict):
        """Save event data to output folder."""
        self.event_counter += 1
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Generate unique event ID if not provided
        event_id = metadata.get("event_id") or str(uuid.uuid4())
        
        # Create event filename
        filename = f"{self.event_counter:04d}_{timestamp}_{camera_id}_{event_type}_{zone_name}"
        
        # Draw detections on frame
        annotated_frame = frame.copy()
        
        # Draw zone polygon
        zone_coords = self.zone_detector.get_zone_coordinates(camera_id, zone_name)
        
        if zone_coords:
            h, w = annotated_frame.shape[:2]
            poly_points = [[int(x * w), int(y * h)] for x, y in zone_coords]
            cv2.polylines(annotated_frame, [np.array(poly_points)], True, (0, 255, 255), 2)
            cv2.putText(annotated_frame, zone_name, tuple(poly_points[0]), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)
        
        # Draw vehicle bounding boxes
        for det in detections:
            x1, y1, x2, y2 = det['bbox']
            track_id = det.get('track_id') or -1
            
            # Color based on event type
            if event_type == "parking_entry":
                color = (0, 255, 0)  # Green
            elif event_type == "parking_exit":
                color = (0, 0, 255)  # Red
            elif event_type == "double_parking_violation":
                color = (255, 0, 255)  # Magenta
            else:
                color = (255, 255, 0)  # Cyan for traffic
            
            cv2.rectangle(annotated_frame, (x1, y1), (x2, y2), color, 2)
            label = f"ID:{track_id} {det['class_name']}"
            cv2.putText(annotated_frame, label, (x1, y1 - 10),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)
        
        # Save annotated image
        img_path = self.output_dir / f"{filename}.jpg"
        cv2.imwrite(str(img_path), annotated_frame)
        
        # Save event metadata as JSON
        event_data = {
            "id": event_id,  # Unique event ID
            "event_number": self.event_counter,
            "timestamp": datetime.now().isoformat(),
            "camera_id": camera_id,
            "event_type": event_type,
            "zone_name": zone_name,
            "metadata": metadata,
            "detections": [
                {
                    "track_id": det.get('track_id', -1),
                    "class_name": det['class_name'],
                    "confidence": det['confidence'],
                    "bbox": det['bbox'],
                    "bbox_normalized": det['bbox_norm']
                }
                for det in detections
            ],
            "image_file": f"{filename}.jpg"
        }
        
        json_path = self.output_dir / f"{filename}.json"
        with open(json_path, 'w') as f:
            json.dump(event_data, f, indent=2)
        
        print(f"   Event {self.event_counter}: {event_type} in {zone_name} (Track IDs: {[d.get('track_id', -1) for d in detections]})")
        
    def process_video(self, video_path: str):
        """Process video and detect events."""
        camera_id = get_camera_id_from_filename(video_path)
        print(f"\n Processing: {Path(video_path).name} (Camera: {camera_id})")
        
        double_parking_violations = {}
        video_fps_configured = False  # Track if we've set the FPS for this video
        
        for result in self.yolo_processor.process_video(video_path):
            frame_count = result['frame_idx']
            frame = result['frame']
            detections = result['detections']
            
            # Configure traffic monitoring with actual video FPS on first frame
            if not video_fps_configured:
                actual_fps = result['fps']
                traffic_interval_seconds = self.config.get("traffic_monitoring_interval", 60)
                self.traffic_monitoring_tracker.set_interval_seconds(traffic_interval_seconds, actual_fps)
                video_fps_configured = True
            
            # Update stationary tracker
            vehicle_detections = [
                self.stationary_tracker.update(det, frame_count) 
                for det in detections
            ]
            
            # Get traffic detections for ALL frames (needed for traffic monitoring tracker)
            traffic_dets_by_zone = self.zone_detector.get_detections_in_any_zone_of_type(
                camera_id, vehicle_detections, "traffic"
            )
            
            # Traffic monitoring (evaluated every frame, tracker controls send frequency)
            if self.traffic_monitoring_tracker.should_send_event(camera_id, frame_count):
                # Get all traffic zones for this camera (even if empty)
                camera_zones = self.zone_detector.zones_config.get(camera_id, {}).get("zones", [])
                traffic_zones = [z["name"] for z in camera_zones if z.get("type") == "traffic"]
                
                # Send event for each traffic zone (even with 0 vehicles)
                for zone_name in traffic_zones:
                    vehicles_in_zone = traffic_dets_by_zone.get(zone_name, [])
                    self.save_event(
                        event_type="traffic_monitoring",
                        camera_id=camera_id,
                        zone_name=zone_name,
                        frame=frame,
                        detections=vehicles_in_zone,
                        metadata={
                            "vehicle_count": len(vehicles_in_zone),
                            "frame_number": frame_count
                        }
                    )
            
            # Process remaining events on every processed frame (at ~10fps rate)
            # Don't skip frames here - we need to catch all parking entries/exits
            
            # Detect vehicles in each zone type
            parking_dets_by_zone = self.zone_detector.get_detections_in_any_zone_of_type(
                camera_id, vehicle_detections, "parking"
            )
            double_parking_dets_by_zone = self.zone_detector.get_detections_in_any_zone_of_type(
                camera_id, vehicle_detections, "double_parking"
            )
            
            # Parking events
            # First, check for parking entries in zones with detections
            if parking_dets_by_zone:
                for zone_name, vehicles_in_zone in parking_dets_by_zone.items():
                    # Check for parking entries
                    for det in vehicles_in_zone:
                        stationary_time = det.get('stationary_duration_sec') or 0
                        
                        is_new_entry, event_id = self.parking_tracker.check_parking_entry(
                            zone_name=zone_name,
                            detection=det,
                            stationary_seconds=stationary_time,
                            parking_threshold_sec=self.parking_threshold,
                        )
                        
                        if is_new_entry:
                            track_id = det.get('track_id', -1)
                            
                            self.save_event(
                                event_type="parking_entry",
                                camera_id=camera_id,
                                zone_name=zone_name,
                                frame=frame,
                                detections=[det],
                                metadata={
                                    "event_id": event_id,
                                    "track_ids": [track_id] if track_id >= 0 else [],
                                    "stationary_seconds": stationary_time,
                                    "frame_number": frame_count
                                }
                            )
            
            # Always check for parking exits in ALL zones we're tracking (even if currently empty)
            for zone_name in list(self.parking_tracker.zone_tracked_ids.keys()):
                # Get currently detected vehicles in this zone (empty list if none)
                vehicles_in_zone = parking_dets_by_zone.get(zone_name, []) if parking_dets_by_zone else []
                
                exited_vehicles = self.parking_tracker.check_parking_exit(
                    zone_name=zone_name,
                    vehicles_in_zone=vehicles_in_zone,
                    current_frame=frame_count,
                )
                
                for event_id, duration, track_id in exited_vehicles:
                    self.save_event(
                        event_type="parking_exit",
                        camera_id=camera_id,
                        zone_name=zone_name,
                        frame=frame,
                        detections=[],
                        metadata={
                            "event_id": event_id,
                            "parking_duration_seconds": duration,
                            "track_id": track_id,
                            "frame_number": frame_count
                        }
                    )
            
            # === RED LIGHT VIOLATIONS ===
            h, w = frame.shape[:2]
            
            # Detect traffic light state
            light_zone = self.zone_detector.get_zone_by_name(camera_id, "traffic_light")
            light_zone_coords = light_zone.get("coordinates") if light_zone else None
            
            light_result = self.traffic_light_detector.detect_light_state(
                frame,
                light_zone_coords=light_zone_coords,
                img_h=h,
                img_w=w,
            )
            
            light_is_red = light_result["light_state"] == "red"
            
            # Get stop line zone
            stop_line_zone = self.zone_detector.get_zone_by_name(camera_id, "stop_line")
            if stop_line_zone:
                stop_line_coords = stop_line_zone.get("coordinates", [])
                
                # Check each detection for violations
                for det in vehicle_detections:
                    track_id = det.get("track_id") or -1  # Handle both missing and None
                    class_name = det.get("class_name", "")
                    
                    if track_id < 0:
                        continue
                    
                    # Only process actual vehicles (not traffic lights, signs, etc.)
                    vehicle_classes = {"car", "truck", "bus", "motorcycle", "bicycle", "vehicle"}
                    if class_name.lower() not in vehicle_classes:
                        continue
                    
                    # Skip if detection has no position
                    if det.get("cx") is None or det.get("cy") is None:
                        continue
                    
                    # Check if vehicle is past stop line
                    is_past_line = self.zone_detector.is_past_stop_line(
                        det,
                        stop_line_coords,
                        img_h=h,
                        img_w=w,
                    )
                    
                    # Check for violation - only if light is actually red
                    is_violation, violation_id = self.red_light_violation_tracker.check_violation(
                        det,
                        light_is_red=light_is_red,
                        vehicle_crossed_stop_line=is_past_line,
                    )
                    
                    # Only save violation if:
                    # 1. It's detected as a violation
                    # 2. Light is actually RED (not unknown or green)
                    # 3. Vehicle has crossed stop line
                    if is_violation and light_is_red and is_past_line:
                        self.save_event(
                            event_type="red_light_violation",
                            camera_id=camera_id,
                            zone_name="stop_line",
                            frame=frame,
                            detections=[det],
                            metadata={
                                "violation_id": violation_id,
                                "track_id": track_id,
                                "light_state": light_result["light_state"],
                                "light_confidence": light_result["confidence"],
                                "frame_number": frame_count
                            }
                        )
            
            # === DOUBLE PARKING VIOLATIONS ===
            for zone_name, vehicles_in_zone in double_parking_dets_by_zone.items():
                for det in vehicles_in_zone:
                    track_id = det.get('track_id') or -1  # Handle both missing and None
                    stationary_time = det.get('stationary_duration_sec') or 0
                    
                    # Double parking violation (stationary >= 60s)
                    if stationary_time >= self.double_parking_threshold:
                        if track_id not in double_parking_violations:
                            double_parking_violations[track_id] = datetime.now()
                            
                            self.save_event(
                                event_type="double_parking_violation",
                                camera_id=camera_id,
                                zone_name=zone_name,
                                frame=frame,
                                detections=[det],
                                metadata={
                                    "track_id": track_id,
                                    "stationary_seconds": stationary_time,
                                    "frame_number": frame_count
                                }
                            )
        
        # Finalize any remaining parking exits at end of video
        print(f"✅ Processed {frame_count} frames")
        print(f"   Total events saved: {self.event_counter}")
        

def main():
    """Main test runner."""
    print("=" * 70)
    print("🚗 EDGE DETECTION - FULL TEST PIPELINE")
    print("=" * 70)
    
    tester = DetectionTester()
    
    # Process all videos in the videos directory
    video_dir = Path("edge_detection/videos")
    if not video_dir.exists():
        print(f"❌ Video directory not found: {video_dir}")
        return
    
    video_files = list(video_dir.glob("*.mp4")) + list(video_dir.glob("*.avi"))
    
    if not video_files:
        print(f"❌ No video files found in {video_dir}")
        return
    
    print(f"\n Found {len(video_files)} video(s) to process\n")
    
    for video_file in video_files:
        try:
            tester.process_video(str(video_file))
        except Exception as e:
            print(f"❌ Error processing {video_file.name}: {e}")
            traceback.print_exc()
    
    print("\n" + "=" * 70)
    print(f"✅ Testing complete! Events saved to: {tester.output_dir}")
    print("=" * 70)


if __name__ == "__main__":
    main()
