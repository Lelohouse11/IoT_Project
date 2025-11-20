# Smart City Traffic & Parking Management – System Architecture

This document describes the updated architecture for the Smart City Traffic & Parking Management System, including edge processing, backend structure, university-provided AI services, routing technologies, and the driver-side PWA.

---

## 1. System Overview & Constraints

- **Provided by the University**
  - MQTT Broker
  - FIWARE Context Broker (Orion-LD)
  - AI services (LLM for text + vision/multimodal model)
- **Your components**
  - Raspberry Pi camera units for each road segment
  - Backend services: event processor, routing, rewards system
  - Databases:
    - InfluxDB for time-series
    - MySQL for relational data (users, rewards, license plates, reports)
- **Goal**
  - Full camera coverage of all road segments
- **Parking context**
  - Mostly unmarked roadside parking → requires gap detection, not spot detection

---

## 2. Edge Layer – Cameras & Raspberry Pi

### 2.1 Deployment & Calibration
- Raspberry Pi + camera at each road segment
- Each unit has:
  - `camera_id`
  - `road_segment_id`
  - GPS position + orientation
- Optional: **WebVMT** for synchronizing video + location + time

### 2.2 On-Device Processing
- Lightweight YOLO models for:
  - Vehicle detection
  - Roadside gap detection
  - Preliminary event detection (double parking suspicion, red light suspicion)

### 2.3 Communication to Backend
- **MQTT** for event metadata (JSON)
- **HTTP Upload API** for images/snippets
- MQTT event includes:
  - event type
  - timestamp
  - camera + segment IDs
  - severity
  - `image_id` reference

---

## 3. Backend & University AI Infrastructure

### 3.1 Event Flow
1. Raspberry Pi publishes events → MQTT Broker  
2. Backend subscriber processes messages  
3. Events converted into FIWARE Smart Data Models  
4. Sent to Orion-LD (Context Broker)  
5. Cygnus/QuantumLeap writes:
   - Time-series → **InfluxDB**
   - Relational → **MySQL**

### 3.2 University AI Services
- Vision model validates:
  - red-light violations
  - double parking
  - unclear images
- Text LLM generates:
  - city improvement suggestions

---

## 4. Detection Logic

### 4.1 Traffic Congestion
- Inputs:
  - Camera density  
  - Driver PWA GPS-based speed  
  - Optional external data:
    - TomTom Traffic API
    - HERE Traffic API
    - Google Traffic Layer
- Congestion = high density + low average speed

### 4.2 Roadside Parking Gap Detection
1. Detect parked vehicles along road edge  
2. Sort vehicles along axis  
3. Compute gaps between vehicles  
4. A gap is available if > minimum length  
5. Convert to world coordinates via:
   - calibration
   - WebVMT
   - simplified segment mapping

### 4.3 Double Parking
- Vehicle detected:
  - in driving lane
  - stationary over a threshold
  - parallel to parked vehicles
- University AI validates

### 4.4 Red-Light Violations
- Virtual stop line calibrated per intersection
- Signal status from external controller or vision model
- Vehicle crosses stop line while red → snippet sent to AI

---

## 5. APIs, Routing, and Data Models

### 5.1 External APIs

#### Traffic APIs
- TomTom Traffic API
- HERE Traffic API
- Google Traffic Layer

#### Routing APIs / Engines
- **Ready-made cloud APIs**
  - TomTom Routing API
  - HERE Routing API
  - Google Directions API
  - OpenRouteService API
  - Mapbox Directions API
- **Self-hosted engines**
  - OSRM
  - GraphHopper
  - Valhalla

#### Video/Geo Synchronization
- WebVMT

### 5.2 Map Frameworks
- Leaflet
- MapLibre GL JS
- OpenLayers

Each supports markers, polylines, traffic overlays, and parking gap rendering.

---

## 6. City Dashboard

### 6.1 Map Visualization
- Framework options:
  - Leaflet
  - MapLibre
  - OpenLayers
- Optional traffic overlays:
  - TomTom / HERE / Google

### 6.2 Routing for Operators
- OSRM / GraphHopper / OpenRouteService

### 6.3 Filters
- Time range (InfluxDB)
- Map bounding box  
- No district filter required

### 6.4 Grafana Dashboards
Recommended metrics:
- Violations over time
- Parking pressure (free gap length / total roadside)
- Average congestion
- Peak hours
- Before/after comparisons
- User report validation rate

---

## 7. AI Suggestions for Urban Improvement
- Aggregated city data (per segment/intersection) sent to text LLM
- Output includes:
  - recommended measures
  - ranking by impact
  - reasoning based on metrics

---

## 8. Driver-Side Application (PWA)

### 8.1 Technology
Progressive Web App with:
- GPS access
- push notifications
- offline caching
- installable on iOS/Android

Frameworks:
- React PWA
- Vue PWA
- SvelteKit
- Angular PWA

### 8.2 Live Information
- Congestion
- Parking gaps
- Incidents

### 8.3 Smart Parking Navigation
- Backend selects best gap
- Routing options:
  - OSRM / GraphHopper / ORS / Valhalla
  - OR cloud routing APIs (TomTom, HERE, Google, Mapbox)
- Route displayed directly in the PWA

---

## 9. Reporting System

### 9.1 User Reports
- Category, location, timestamp, description
- No photos
- Stored in MySQL + FIWARE

### 9.2 Validation (Optional)
- Cross-check with sensor data
- Validated reports → reward points

---

## 10. Rewards System

### 10.1 Identification
- User accounts with optional (but recommended) license plate
- Stored in MySQL
- Simplified encryption for the project

### 10.2 Tables
- `users`
- `license_plate_map`
- `violations`
- `rewards`

### 10.3 Points Logic
- Violation-free streak → earns points
- Points can be exchanged for rewards

---

## 11. Summary of Integrated APIs & Technologies

### Traffic
- TomTom Traffic API
- HERE Traffic API
- Google Traffic Layer

### Routing
- TomTom Routing API
- HERE Routing API
- Google Directions API
- OpenRouteService
- Mapbox Directions API
- OSRM
- GraphHopper
- Valhalla

### Map Frameworks
- Leaflet
- MapLibre GL JS
- OpenLayers

### Video/Geo Sync
- WebVMT

### Driver App
- Progressive Web App (React, Vue, SvelteKit, Angular)

### Diagramm

graph LR
  %% Direction
  %% left-to-right for readability
  %% Subgraphs structure the architecture

  %% =======================
  %% Edge Layer
  %% =======================
  subgraph EDGE[Edge Layer – Street Side]
    CAM[\"Cameras & Raspberry Pi\n- Object detection (YOLO)\n- Gap detection\"]
  end

  %% =======================
  %% Messaging & Upload
  %% =======================
  subgraph MSG[Messaging & Upload]
    MQTT[MQTT Broker\n(provided by University)]
    UPLOAD[Evidence Upload API\n(HTTP file upload)]
  end

  %% =======================
  %% Backend / Core Services
  %% =======================
  subgraph BACKEND[Backend Services]
    BE[Backend Services\n- Event Processor\n- API Gateway\n- Routing Service]
    FIWARE[FIWARE Context Broker\n(Orion-LD)\nCentral Live Data Hub]
  end

  %% =======================
  %% Databases
  %% =======================
  subgraph DATA[Data Storage]
    INFLUX[InfluxDB\nTime-series data]
    MYSQL[MySQL\nRelational data\n(users, rewards, reports, mappings)]
  end

  %% =======================
  %% City-Side Visualization
  %% =======================
  subgraph CITY[City-Side Visualization]
    CITYAPP[City Dashboard Web App\n(Map: Leaflet / MapLibre / OpenLayers)]
    GRAF[Grafana Dashboards\n(analytics & KPIs)]
  end

  %% =======================
  %% Driver-Side
  %% =======================
  subgraph DRIVER[Driver-Side Application]
    PWA[Driver Application (PWA)\n- Live map & routing\n- Smart parking\n- Reporting]
  end

  %% =======================
  %% External / University Services
  %% =======================
  subgraph UNI[University Services]
    AI[University AI Services\n- Vision LLM\n- Text LLM]
  end

  subgraph EXT[External APIs]
    TRAFFICAPI[Traffic APIs\nTomTom / HERE / Google]
    ROUTINGAPI[Routing APIs (optional)\nOpenRouteService / OSRM / GraphHopper / Valhalla]
  end

  %% =======================
  %% Connections – Edge to Backend
  %% =======================
  CAM -- "MQTT (events)" --> MQTT
  CAM -- "HTTP/REST (images/snippets)" --> UPLOAD

  MQTT -- "MQTT subscribe\n(event stream)" --> BE
  UPLOAD -- "Image metadata / IDs" --> BE

  %% =======================
  %% Backend <-> FIWARE
  %% =======================
  BE -- "NGSI-LD / NGSI v2\n(create/update entities)" --> FIWARE
  FIWARE -- "Context queries\n(NGSI-LD)" --> BE

  %% =======================
  %% FIWARE to Databases
  %% (via Cygnus / QuantumLeap - implicit)
  %% =======================
  FIWARE -- "NGSI → time-series\n(Cygnus / QuantumLeap)" --> INFLUX
  FIWARE -- "NGSI → relational\n(Cygnus etc.)" --> MYSQL

  %% =======================
  %% Backend to University AI
  %% =======================
  BE -- "HTTP/REST\n(image URLs + metadata)" --> AI
  AI -- "classification results\n(violation, confidence)" --> BE

  %% =======================
  %% Frontends (City / Driver)
  %% =======================
  BE -- "HTTP/REST APIs\n(city endpoints)" --> CITYAPP
  BE -- "HTTP/REST APIs\n(driver endpoints)" --> PWA

  %% City dashboard data
  CITYAPP -- "HTTP/REST\n(live context data)" --> FIWARE
  GRAF -- "Time-series queries\n(Flux/SQL over HTTP)" --> INFLUX

  %% Driver PWA telemetry & reports
  PWA -- "HTTP/REST\n(GPS speed, reports,\nparking requests)" --> BE

  %% =======================
  %% External traffic & routing APIs
  %% =======================
  CITYAPP -- "HTTP/REST\n(traffic overlays)" --> TRAFFICAPI
  PWA -- "HTTP/REST (optional)\ntraffic or directions" --> TRAFFICAPI

  BE -- "HTTP/REST (optional)\nroute calculation" --> ROUTINGAPI
  PWA -- "HTTPS\n(route & instructions\nfrom backend)" --> BE

