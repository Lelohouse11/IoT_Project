"""
Backend sender module for submitting detection events to the backend API.
Handles JSON payload construction, base64 encoding, and retry logic.
"""

import requests
import base64
import logging
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime, timezone
import time

logger = logging.getLogger(__name__)


class BackendSender:
    """Sends detection events to backend API with retry logic."""

    def __init__(self, backend_url: str, max_retries: int = 5, timeout: int = 30):
        """
        Initialize backend sender.

        Args:
            backend_url: Base URL of backend API (e.g., "http://localhost:8003/api/camera")
            max_retries: Number of retry attempts before dropping event
            timeout: Request timeout in seconds
        """
        self.backend_url = backend_url.rstrip("/")
        self.event_endpoint = f"{self.backend_url}/event"
        self.max_retries = max_retries
        self.timeout = timeout
        print(f"[BACKEND SENDER] Initialized with URL: {self.backend_url}")
        print(f"[BACKEND SENDER] Event endpoint: {self.event_endpoint}")
        print(f"[BACKEND SENDER] Max retries: {max_retries}, Timeout: {timeout}s")

    def check_health(self) -> bool:
        """
        Check if backend is healthy.

        Returns:
            True if backend responds to health check, False otherwise
        """
        try:
            health_url = f"{self.backend_url}/health"
            print(f"[BACKEND SENDER] Checking health at: {health_url}")
            response = requests.get(health_url, timeout=5)
            is_healthy = response.status_code == 200
            if is_healthy:
                print(f"[BACKEND SENDER] ✓ Backend is healthy")
            else:
                print(f"[BACKEND SENDER] ✗ Backend returned status {response.status_code}")
            return is_healthy
        except requests.exceptions.ConnectionError as e:
            print(f"[BACKEND SENDER] ✗ Connection failed: Cannot reach {health_url}")
            print(f"[BACKEND SENDER]   Error: {e}")
            return False
        except Exception as e:
            print(f"[BACKEND SENDER] ✗ Health check failed: {e}")
            return False

    @staticmethod
    def encode_image_to_base64(frame: Any) -> str:
        """
        Encode image/frame to base64 string.

        Args:
            frame: OpenCV BGR frame (numpy array) or path to image file

        Returns:
            Base64 encoded image string
        """
        import cv2

        if isinstance(frame, (str, Path)):
            # Read from file
            with open(frame, "rb") as f:
                image_data = f.read()
        else:
            # Encode frame to JPG bytes
            success, image_bytes = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
            if not success:
                raise ValueError("Failed to encode frame to JPEG")
            image_data = image_bytes.tobytes()

        return base64.b64encode(image_data).decode("utf-8")

    @staticmethod
    def get_iso_timestamp() -> str:
        """
        Get current timestamp in ISO 8601 format.

        Returns:
            Timestamp string (e.g., "2026-01-16T10:30:00Z")
        """
        return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")

    def build_payload(
        self,
        camera_id: str,
        event_type: str,
        frame: Any,
        metadata: Dict[str, Any],
        timestamp: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Build event payload for backend API.

        Args:
            camera_id: Camera identifier
            event_type: One of: "traffic_monitoring", "double_parking", 
                               "red_light_violation", "parking_status"
            frame: OpenCV frame or image path
            metadata: Dict with bbox, confidence, zone_coordinates, etc.
            timestamp: ISO 8601 timestamp (generated if not provided)

        Returns:
            Complete payload ready for JSON serialization
        """
        if timestamp is None:
            timestamp = self.get_iso_timestamp()

        image_base64 = self.encode_image_to_base64(frame)

        return {
            "camera_id": camera_id,
            "timestamp": timestamp,
            "event_type": event_type,
            "image": image_base64,
            "metadata": metadata,
        }

    def send_event(
        self,
        camera_id: str,
        event_type: str,
        frame: Any,
        metadata: Dict[str, Any],
        timestamp: Optional[str] = None,
    ) -> bool:
        """
        Send event to backend with automatic retry on failure.

        Args:
            camera_id: Camera identifier
            event_type: Event type (see build_payload)
            frame: Image frame or path
            metadata: Event metadata
            timestamp: ISO 8601 timestamp

        Returns:
            True if event sent successfully, False if dropped after retries
        """
        payload = self.build_payload(camera_id, event_type, frame, metadata, timestamp)

        for attempt in range(1, self.max_retries + 1):
            try:
                response = requests.post(
                    self.event_endpoint,
                    json=payload,
                    timeout=self.timeout,
                )

                if response.status_code in (200, 201):
                    logger.debug(f"Event sent successfully: {camera_id} {event_type}")
                    return True

                # Log error response but continue to retry
                print(f"[BACKEND SENDER] Backend returned {response.status_code}: {response.text[:200]}")
                logger.debug(
                    f"Backend returned {response.status_code}: {response.text[:100]}"
                )

            except requests.exceptions.ConnectionError as e:
                print(f"[BACKEND SENDER] Attempt {attempt}/{self.max_retries} - Connection failed: Cannot reach {self.event_endpoint}")
                logger.debug(f"Connection error on attempt {attempt}: {e}")
            except requests.exceptions.RequestException as e:
                print(f"[BACKEND SENDER] Attempt {attempt}/{self.max_retries} - Request failed: {e}")
                logger.debug(f"Attempt {attempt}/{self.max_retries} failed: {e}")

            # Wait before retry (exponential backoff: 1s, 2s, 4s, ...)
            if attempt < self.max_retries:
                wait_time = min(2 ** (attempt - 1), 10)  # Cap at 10 seconds
                print(f"[BACKEND SENDER] Retrying in {wait_time}s...")
                time.sleep(wait_time)

        # Max retries exceeded - silently drop event
        print(f"[BACKEND SENDER] ✗ Event dropped after {self.max_retries} retries: {camera_id} {event_type}")
        logger.debug(f"Event dropped after {self.max_retries} retries: {camera_id} {event_type}")
        return False

    def send_events_batch(
        self,
        events: list[Dict[str, Any]],
    ) -> Dict[str, int]:
        """
        Send multiple events.

        Args:
            events: List of event dicts, each with:
                   camera_id, event_type, frame, metadata, timestamp (optional)

        Returns:
            Dict with "sent" and "dropped" counts
        """
        sent = 0
        dropped = 0

        for event in events:
            if self.send_event(
                camera_id=event["camera_id"],
                event_type=event["event_type"],
                frame=event["frame"],
                metadata=event.get("metadata", {}),
                timestamp=event.get("timestamp"),
            ):
                sent += 1
            else:
                dropped += 1

        return {"sent": sent, "dropped": dropped}
