"""Processing Service for camera event analysis."""

import requests
import base64
import re
from typing import Dict, Optional
from backend.shared import config, database


class ProcessingService:
    """Service for processing camera events (traffic, parking, violations)."""

    def __init__(self):
        self.api_url = config.VLM_API_URL
        self.api_key = config.VLM_API_KEY
        self.model = config.VLM_MODEL
        self.timeout = config.VLM_TIMEOUT

    def _call_vlm(self, prompt: str, image_base64: str) -> Optional[str]:
        """Call VLM API with prompt and image, return response text."""
        print(f"[VLM] Calling VLM API: {self.api_url}, image: {len(image_base64)} bytes")
        headers = {
            "Content-Type": "application/json",
            "X-API-Key": self.api_key,
        }
        
        payload = {
            "model": self.model,
            "prompt": prompt,
            "image": image_base64
        }
        
        try:
            print(f"[VLM] Request with prompt: {prompt[:80]}...")
            response = requests.post(
                self.api_url,
                headers=headers,
                json=payload,
                timeout=self.timeout
            )
            response.raise_for_status()
            result = response.json()
            output = result.get("output", "")
            print(f"[VLM] Response: {output}")
            return output
        except requests.exceptions.HTTPError as e:
            print(f"[VLM ERROR] HTTP {e.response.status_code}: {e.response.text[:200]}")
            return None
        except requests.exceptions.Timeout:
            print(f"[VLM ERROR] Request timeout after {self.timeout}s")
            return None
        except requests.exceptions.RequestException as e:
            print(f"[VLM ERROR] VLM request failed: {e}")
            return None
        except Exception as e:
            print(f"[VLM ERROR] Unexpected error: {e}")
            return None

    def process_traffic_monitoring(self, image_base64: str, metadata: Dict) -> Dict:
        """Calculate traffic density from YOLO vehicle count."""
        print(f"[TRAFFIC] Processing traffic monitoring event")
        
        vehicle_count = metadata.get('vehicle_count', 0)
        print(f"[TRAFFIC] Vehicle count: {vehicle_count}")
        
        segment_length_km = 0.1
        density = vehicle_count / segment_length_km if segment_length_km > 0 else 0.0
        print(f"[TRAFFIC] Density: {density:.2f} vehicles/km")
        
        return {
            "vehicle_count": vehicle_count,
            "density": density,
            "vlm_output": None,
            "source": "yolo_tracking"
        }

    def process_double_parking(self, image_base64: str, metadata: Dict) -> Dict:
        """Extract license plate from double parking image."""
        print(f"[VLM] Processing double parking violation")
        prompt = (
            "Examine this image of a double-parked vehicle. "
            "Extract the license plate number if visible, uppercase only. "
            "Respond with plate text or 'NONE' if unreadable."
        )
        
        vlm_output = self._call_vlm(prompt, image_base64)
        
        if vlm_output is None:
            print(f"[VLM ERROR] Double parking VLM request failed")
            return {"license_plate": None, "driver_id": None, "error": "VLM request failed"}
        
        license_plate = self._extract_license_plate(vlm_output)
        print(f"[VLM] Extracted plate: {license_plate}")
        
        driver_id = None
        if license_plate:
            driver_id = self._match_driver_by_plate(license_plate)
            if driver_id:
                print(f"[VLM] Updating parking violation for driver {driver_id}")
                self._update_parking_violation(driver_id)
        
        return {
            "license_plate": license_plate,
            "driver_id": driver_id,
            "vlm_output": vlm_output
        }

    def process_red_light_violation(self, image_base64: str, metadata: Dict) -> Dict:
        """Extract license plate from red light violation image."""
        print(f"[VLM] Processing red light violation")
        prompt = (
            "Examine this image of a vehicle running a red light. "
            "Extract the license plate number if visible, uppercase only. "
            "Respond with plate text or 'NONE' if unreadable."
        )
        
        vlm_output = self._call_vlm(prompt, image_base64)
        
        if vlm_output is None:
            print(f"[VLM ERROR] Red light violation VLM request failed")
            return {"license_plate": None, "driver_id": None, "error": "VLM request failed"}
        
        license_plate = self._extract_license_plate(vlm_output)
        print(f"[VLM] Extracted plate: {license_plate}")
        
        driver_id = None
        if license_plate:
            driver_id = self._match_driver_by_plate(license_plate)
            if driver_id:
                print(f"[VLM] Updating traffic violation for driver {driver_id}")
                self._update_traffic_violation(driver_id)
        
        return {
            "license_plate": license_plate,
            "driver_id": driver_id,
            "vlm_output": vlm_output
        }

    def process_parking_status(self, image_base64: str, metadata: Dict) -> Dict:
        """Count free parking spots in surveillance image."""
        print(f"[VLM] Processing parking status")
        prompt = (
            "Analyze this street-level parking image. Count empty gaps large enough for one car (~4.5m). "
            "Rules: (1) Count only visible gaps, (2) Exclude occlusions, (3) Use conservative counting. "
            "Output only a single digit or 'UNABLE'."
        )
        
        vlm_output = self._call_vlm(prompt, image_base64)
        
        if vlm_output is None or "UNABLE" in vlm_output.upper():
            print(f"[VLM ERROR] Could not determine parking spots")
            return {"free_spots": None, "status": "unable", "error": "Unable to determine parking spots"}
        
        match = re.search(r'\d+', vlm_output)
        free_spots = int(match.group()) if match else None
        
        if free_spots is None:
            print(f"[VLM ERROR] Could not parse spot count from response")
            return {"free_spots": None, "status": "unable", "error": "Could not parse spot count"}
        
        print(f"[VLM] Parking status: {free_spots} free spots")
        return {
            "free_spots": free_spots,
            "vlm_output": vlm_output
        }

    def _extract_license_plate(self, vlm_output: str) -> Optional[str]:
        """Extract license plate from VLM text output."""
        if not vlm_output or "NONE" in vlm_output.upper():
            return None
        
        plate_pattern = r'[A-Z]{3,4}-\d{4}'
        match = re.search(plate_pattern, vlm_output.upper())
        if match:
            return match.group()
        
        cleaned = re.sub(r'[^A-Z0-9-]', '', vlm_output.upper())
        if 6 <= len(cleaned) <= 10:
            return cleaned
        
        return None

    def _match_driver_by_plate(self, license_plate: str) -> Optional[int]:
        """Find driver in database by license plate."""
        query = "SELECT id FROM driver_profiles WHERE license_plate = %s"
        result = database.fetch_all(query, (license_plate,))
        return result[0]['id'] if result else None

    def _update_parking_violation(self, driver_id: int) -> bool:
        """Update driver parking violation timestamp in database."""
        query = """
            UPDATE driver_profiles 
            SET last_parking_violation = CURRENT_TIMESTAMP 
            WHERE id = %s
        """
        try:
            database.execute_query(query, (driver_id,))
            return True
        except Exception as e:
            print(f"[VLM ERROR] Failed to update parking violation for driver {driver_id}: {e}")
            return False

    def _update_traffic_violation(self, driver_id: int) -> bool:
        """Update driver traffic violation timestamp in database."""
        query = """
            UPDATE driver_profiles 
            SET last_traffic_violation = CURRENT_TIMESTAMP 
            WHERE id = %s
        """
        try:
            database.execute_query(query, (driver_id,))
            return True
        except Exception as e:
            print(f"[VLM ERROR] Failed to update traffic violation for driver {driver_id}: {e}")
            return False


processing_service = ProcessingService()
