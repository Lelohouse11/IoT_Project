"""
Edge Detection - Production Detection Runner
Processes videos and sends detection events to backend API.
"""

from datetime import datetime
from pathlib import Path
import traceback
import time

from src.yolo_processor import YOLOProcessor
from src.zone_detector import ZoneDetector
from src.stationary_tracker import StationaryTracker
from src.parking_tracker import ParkingTracker
from src.traffic_light_detector import TrafficLightDetector
from src.red_light_violation_tracker import RedLightViolationTracker
from src.traffic_monitoring_tracker import TrafficMonitoringTracker
from src.backend_sender import BackendSender
from src.config import Config, get_camera_id_from_filename, load_camera_zones


class DetectionRunner:
    """Production detection pipeline runner."""
    
    def __init__(self):
        print("\n" + "=" * 70)
        print("Edge Detection Runner - Initializing")
        print("=" * 70)
        
        self.config = Config()
        
        print(f"\n[CONFIG] Backend URL: {self.config.get('backend_url')}")
        print(f"[CONFIG] YOLO Model: {self.config.get('model_path')}")
        print(f"[CONFIG] Device: {self.config.get('device')}")
        print(f"[CONFIG] Max Retries: {self.config.get('max_retries')}")
        print(f"[CONFIG] Request Timeout: {self.config.get('request_timeout')}s\n")
        
        self.yolo_processor = YOLOProcessor(
            model_path=self.config.get("model_path"),
            device=self.config.get("device")
        )
        zones_config = load_camera_zones(Path("zones/zones.json"))
        self.zone_detector = ZoneDetector(zones_config)
        self.stationary_tracker = StationaryTracker(
            epsilon_px=self.config.get("stationary_epsilon_px"),
            fps=self.config.get("fps")
        )
        
        print("\n[INIT] Creating backend sender...")
        self.backend_sender = BackendSender(
            backend_url=self.config.get("backend_url"),
            max_retries=self.config.get("max_retries"),
            timeout=self.config.get("request_timeout")
        )
        
        # Perform initial health check
        print("\n[INIT] Performing initial backend health check...")
        if self.backend_sender.check_health():
            print("[INIT] ✓ Backend is available and healthy\n")
        else:
            print("[INIT] ⚠️  WARNING: Backend is not available!")
            print("[INIT]     Events will be queued and retried...\n")
        
        self.parking_threshold = self.config.get("parking_stationary_duration")
        self.double_parking_threshold = self.config.get("double_parking_stationary_duration")
        
        # Tracking components
        self.parking_tracker = ParkingTracker(
            exit_cooldown_sec=10.0,
            exit_debounce_frames=100
        )
        self.traffic_light_detector = TrafficLightDetector()
        self.red_light_violation_tracker = RedLightViolationTracker(cooldown_sec=30.0)
        
        fps = self.config.get("fps", 25)
        traffic_interval_seconds = self.config.get("traffic_monitoring_interval", 60)
        self.traffic_monitoring_tracker = TrafficMonitoringTracker(
            interval_frames=int(traffic_interval_seconds * fps)
        )
        
        # Event tracking
        self.events_sent = 0
        self.events_dropped = 0
        
    def send_event(self, event_type: str, camera_id: str, zone_name: str, 
                   frame, detections: list, metadata: dict):
        """Send event to backend API."""
        success = self.backend_sender.send_event(
            camera_id=camera_id,
            event_type=event_type,
            frame=frame,
            metadata={**metadata, "zone_name": zone_name}
        )
        
        track_ids = [d.get('track_id', -1) for d in detections]
        if success:
            self.events_sent += 1
            print(f"   ✓ {event_type} in {zone_name} (Camera: {camera_id}, Track IDs: {track_ids})")
        else:
            self.events_dropped += 1
            print(f"   ✗ Event dropped: {event_type} in {zone_name} (backend unavailable)")
        
    def process_video(self, video_path: str):
        """Process video and detect events."""
        camera_id = get_camera_id_from_filename(video_path)
        print(f"\n📹 Processing: {Path(video_path).name} (Camera: {camera_id})")
        
        double_parking_violations = {}
        video_fps_configured = False
        frame_count = 0
        
        for result in self.yolo_processor.process_video(video_path):
            frame_count = result['frame_idx']
            frame = result['frame']
            detections = result['detections']
            
            if not video_fps_configured:
                actual_fps = result['fps']
                traffic_interval_seconds = self.config.get("traffic_monitoring_interval", 60)
                self.traffic_monitoring_tracker.set_interval_seconds(traffic_interval_seconds, actual_fps)
                video_fps_configured = True
            
            vehicle_detections = [
                self.stationary_tracker.update(det, frame_count) 
                for det in detections
            ]
            
            traffic_dets_by_zone = self.zone_detector.get_detections_in_any_zone_of_type(
                camera_id, vehicle_detections, "traffic"
            )
            
            # Traffic monitoring
            if self.traffic_monitoring_tracker.should_send_event(camera_id, frame_count):
                camera_zones = self.zone_detector.zones_config.get(camera_id, {}).get("zones", [])
                traffic_zones = [z["name"] for z in camera_zones if z.get("type") == "traffic"]
                
                for zone_name in traffic_zones:
                    vehicles_in_zone = traffic_dets_by_zone.get(zone_name, [])
                    self.send_event(
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
            
            parking_dets_by_zone = self.zone_detector.get_detections_in_any_zone_of_type(
                camera_id, vehicle_detections, "parking"
            )
            double_parking_dets_by_zone = self.zone_detector.get_detections_in_any_zone_of_type(
                camera_id, vehicle_detections, "double_parking"
            )
            
            # Parking entries
            if parking_dets_by_zone:
                for zone_name, vehicles_in_zone in parking_dets_by_zone.items():
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
                            
                            self.send_event(
                                event_type="parking_status",
                                camera_id=camera_id,
                                zone_name=zone_name,
                                frame=frame,
                                detections=[det],
                                metadata={
                                    "event_id": event_id,
                                    "track_ids": [track_id] if track_id >= 0 else [],
                                    "stationary_seconds": stationary_time,
                                    "frame_number": frame_count,
                                    "parking_event_type": "entry"
                                }
                            )
            
            # Parking exits
            for zone_name in list(self.parking_tracker.zone_tracked_ids.keys()):
                vehicles_in_zone = parking_dets_by_zone.get(zone_name, []) if parking_dets_by_zone else []
                
                exited_vehicles = self.parking_tracker.check_parking_exit(
                    zone_name=zone_name,
                    vehicles_in_zone=vehicles_in_zone,
                    current_frame=frame_count,
                )
                
                for event_id, duration, track_id in exited_vehicles:
                    self.send_event(
                        event_type="parking_status",
                        camera_id=camera_id,
                        zone_name=zone_name,
                        frame=frame,
                        detections=[],
                        metadata={
                            "event_id": event_id,
                            "parking_duration_seconds": duration,
                            "track_id": track_id,
                            "frame_number": frame_count,
                            "parking_event_type": "exit"
                        }
                    )
            
            # Red light violations
            h, w = frame.shape[:2]
            
            light_zone = self.zone_detector.get_zone_by_name(camera_id, "traffic_light")
            light_zone_coords = light_zone.get("coordinates") if light_zone else None
            
            light_result = self.traffic_light_detector.detect_light_state(
                frame,
                light_zone_coords=light_zone_coords,
                img_h=h,
                img_w=w,
            )
            
            light_is_red = light_result["light_state"] == "red"
            
            stop_line_zone = self.zone_detector.get_zone_by_name(camera_id, "stop_line")
            if stop_line_zone:
                stop_line_coords = stop_line_zone.get("coordinates", [])
                
                for det in vehicle_detections:
                    track_id = det.get("track_id") or -1
                    class_name = det.get("class_name", "")
                    
                    if track_id < 0:
                        continue
                    
                    vehicle_classes = {"car", "truck", "bus", "motorcycle", "bicycle", "vehicle"}
                    if class_name.lower() not in vehicle_classes:
                        continue
                    
                    if det.get("cx") is None or det.get("cy") is None:
                        continue
                    
                    is_past_line = self.zone_detector.is_past_stop_line(
                        det,
                        stop_line_coords,
                        img_h=h,
                        img_w=w,
                    )
                    
                    is_violation, violation_id = self.red_light_violation_tracker.check_violation(
                        det,
                        light_is_red=light_is_red,
                        vehicle_crossed_stop_line=is_past_line,
                    )
                    
                    if is_violation and light_is_red and is_past_line:
                        self.send_event(
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
            
            # Double parking violations
            for zone_name, vehicles_in_zone in double_parking_dets_by_zone.items():
                for det in vehicles_in_zone:
                    track_id = det.get('track_id') or -1
                    stationary_time = det.get('stationary_duration_sec') or 0
                    
                    if stationary_time >= self.double_parking_threshold:
                        if track_id not in double_parking_violations:
                            double_parking_violations[track_id] = datetime.now()
                            
                            self.send_event(
                                event_type="double_parking",
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
        
        print(f"✅ Completed: {Path(video_path).name} ({frame_count} frames processed)")
        

def main():
    """Main runner - continuous loop."""
    print("=" * 70)
    print("🚗 EDGE DETECTION - PRODUCTION RUNNER (CONTINUOUS MODE)")
    print("=" * 70)
    
    # Wait for backend to be fully ready
    print("\n[STARTUP] Waiting 10 seconds for backend services to initialize...")
    time.sleep(10)
    
    video_dir = Path("videos")
    if not video_dir.exists():
        print(f"❌ Video directory not found: {video_dir}")
        return
    
    iteration = 0
    
    while True:
        iteration += 1
        print(f"\n{'=' * 70}")
        print(f"🔄 Iteration #{iteration} - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 70)
        
        try:
            runner = DetectionRunner()
            
            video_files = list(video_dir.glob("*.mp4")) + list(video_dir.glob("*.avi"))
            
            if not video_files:
                print(f"⚠️  No video files found in {video_dir}")
                print("   Waiting 60 seconds before retry...")
                time.sleep(60)
                continue
            
            print(f"\n📂 Found {len(video_files)} video file(s) to process\n")
            
            for video_file in video_files:
                try:
                    runner.process_video(str(video_file))
                except Exception as e:
                    print(f"❌ Error processing {video_file.name}: {e}")
                    traceback.print_exc()
            
            print("\n" + "=" * 70)
            print(f"✅ Iteration #{iteration} complete!")
            print(f"   📊 Events sent: {runner.events_sent}")
            print(f"   ❌ Events dropped: {runner.events_dropped}")
            print("   ⏳ Waiting 10 seconds before next iteration...")
            print("=" * 70)
            
        except Exception as e:
            print(f"❌ Unexpected error in main loop: {e}")
            traceback.print_exc()
        
        time.sleep(10)


if __name__ == "__main__":
    main()
