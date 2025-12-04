# Camera Pipeline Overview

## 1. Edge Layer – Camera & Raspberry Pi

**Hardware Setup**
- Raspberry Pi + Camera module deployed at each road segment.
- Attach GPS + Timestamp + Orientation
- Timestamp & orientation sensors for calibration and event tagging.
- Optional: WebVMT for improved synchronization of video frames with GPS and time (not required).

**On-Device Processing**  
- Lightweight detection models:  
  - **YOLOv8-Nano/Tiny** – Best accuracy for vehicle detection, gap measurement, bounding boxes, and lane positioning.  
    - More reliable 
    - Higher detection precision
  - **MobileNetSSD** – Lightweight and faster, suitable for basic vehicle presence detection.  
    - Works well on lower-end Raspberry Pi or when real-time performance is prioritized over accuracy.  
    - Good fallback model when hardware is limited or power consumption must be minimized.

**Primary Edge Detection Tasks**
- Vehicle detection
- Roadside parking gap detection 
- Double parking suspicion
- Red-light violation suspicion using virtual stop-line
- Basic vehicle movement tracking and position analysis

**Snippet Creation**
- On event detection, the system stores:
  - Image frame
  - Embedded metadata:
    - `timestamp`
    - `camera_id`
    - `GPS position`
    - `event_type`
    - `snippet_id`
      
---

## 2. Communication Layer
### MQTT (Event Metadata Only)
- Transmits metadata as lightweight JSON:
  - event_type
  - camera_id
  - segment_id
  - timestamp
  - GPS position
  - severity/confidence
  - snippet_id or image_id reference

### HTTP Upload API (Snippets)
- Snippets uploaded via REST API.
- Stored in backend and linked using snippet_id.

---

## 3. Backend Processing (FIWARE Integration)
- MQTT events received and converted to FIWARE Smart Data Models.
- Stored in FIWARE systems:
  - Orion-LD (context management)
  - InfluxDB (time-series event storage)
  - MySQL (relational)
- Dashboard tools provide:
  - Live status
  - Violation history
  - Parking availability visualization
  - Heat maps of congestion and illegal parking

---

## 4. AI Validation & Decision Layer
- University AI services perform second-stage analysis using stronger models
- Behavior-based frame analysis:
  - Checks if vehicle is stationary in driving lane
  - Identifies red-light violations using virtual stop line
  - Confirms double parking by location, path obstruction, and duration
- Final decisions include:
  - Violation type classification
  - Confidence level
  - Suggested enforcement action
  - Snippet evidence
 
  ---

## Detection Approach – How Each Violation is Identified

### Double Parking 
- Vehicle is detected in the **driving lane**, not in a valid parking zone.
- Remains **stationary for a defined duration (e.g., >30s)**.
- Bounding box overlaps with lane area and blocks traffic flow.
- Confirmed by comparing with adjacent parked vehicles (parallel blocking behavior).
- Final validation happens via University AI.

---

### Red-Light Violation
- A **virtual stop-line** is created using GPS calibration or manual mapping.
- Traffic signal status (optional) determined via AI or external data.
- If bounding box crosses the stop-line during red phase → violation suspected.
- Multiple frame tracking used to confirm motion direction and timing.

### Traffic Congestion Detection

- Camera-based vehicle density estimation using YOLO/MobileNetSSD.
- Count number of vehicles in defined road segment using bounding boxes.
- Driver PWA GPS-based average vehicle speed.
- Combine traffic density with average speed to determine congestion
- Optional third-party traffic APIs:
  - TomTom Traffic API
  - HERE Traffic API
  - Google Maps Traffic Layer
 
---

### Roadside Parking Space 
- Vehicles near the curb are detected and sorted by position.
- **Distance between vehicles is measured** to identify free parking spaces.
- If gap > threshold (e.g., 5.5 meters) → spot classified as available.

---
## Camera Pipeline

```text
Camera Sensor detects vehicle behavior
     ↓
Local Processing (YOLO / MobileNetSSD) analyzes frame
     ↓
Suspicious event detected (double parking, red-light, speed, roadside parking)
     ↓
Create snippet (frame) + metadata 
     ↓
Send metadata via MQTT (lightweight JSON)
     ↓
Send snippet via HTTP Upload API (image)
     ↓
Backend receives MQTT event → stores in FIWARE Orion-LD as Smart Data Model
     ↓
Backend links snippet file and enriches with location, map, road rules
     ↓
University AI performs second-stage validation
     ↓
AI confirms violation using:
   • Virtual stop lines (red-light)
   • Stationary + lane position + time (double parking)
   • Space measurement + curb distance (parking violation)
     ↓
Decision Engine adds classification, confidence score, enforcement suggestion
     ↓
Violation is stored in database (MySQL, InfluxDB, Object Storage)
     ↓
Dashboard displays real-time status, alerts, heat maps, parking visibility

```
