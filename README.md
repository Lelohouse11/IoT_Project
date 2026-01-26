# IoT Project Overview

Compact toolkit for simulating, collecting, and visualizing city traffic incidents. Features real-time camera event processing with Vision Language Model integration, FIWARE smart city modeling, and driver reward system.

## Project Structure

```
IoT_Project/
├── backend/             # Core Backend Services & Bridges
│   ├── admin/           # Admin-only services (not accessible to driver PWA)
│   ├── public/          # Public services (accessible to driver PWA)
│   ├── shared/          # Shared utilities (config, database)
│   └── simulation/      # Simulation scripts (fakers)
├── city_dashboard/      # Admin Dashboard (JS/HTML)
├── db_init/             # SQL Schema & Migration Scripts
│   └── seed_data/       # Raw JSON/GeoJSON Data Files
├── docker/              # Dockerfiles and startup scripts
├── drivers_side_pwa/    # Driver App (React)
├── edge_detection/      # YOLOv8 Edge Processing (videos, zones, src)
├── presentation/        # Project milestones (Concept, MVP, Final)
└── .vscode/             # Task & Launch Configs
```

## Modules & Tech

### Frontend Applications
- **City Dashboard** (`city_dashboard`) – Vanilla JS + Leaflet frontend. Renders live accidents, parking, and traffic data. Features a modular architecture (`config.js`, `layout.js`) and embeds Grafana widgets. Includes user authentication with JWT-based login/registration restricted to a whitelist of email addresses (defined in `backend/shared/config.py`).
- **Driver Companion App** (`drivers_side_pwa`) – React + Vite PWA. Provides a mobile-first interface for drivers to view alerts and report incidents. Connects to `backend/public/frontend_map_api.py` for optimized traffic data.

### Computer Vision & Edge Processing
- **Edge Detection** (`edge_detection/`) – Real-time YOLOv8 inference on edge devices (cameras). Processes video streams with vehicle tracking, zone-based filtering, and event triggering:
  - Parking zone monitoring (entry/exit after 30s stationary)
  - Double-parking violation detection (1-minute stationary in no-parking zones)
  - Traffic monitoring snapshots (every 60 seconds)
  - Automatic retry logic (3–5 attempts) for backend submission
  - Silent operation with no local output
- **Camera Event System** - Server-side event processing using Vision Language Model (VLM) for license plate OCR and free spot counting

### Data Simulation & Event Generation
- **Simulation** (`backend/simulation/`) – Python scripts simulating smart city entities:
  - `accident_generator.py`: Synthesizes `TrafficAccident` entities.
  - `traffic_violation_generator.py`: Emits `TrafficViolation` detections (red light, illegal parking).
  - `parking_generator.py`: Simulates `OnStreetParking` occupancy.
  - `traffic_generator.py`: Drives `TrafficFlowObserved` entities.
  - `camera_entities_init.py`: Initializes camera-related Fiware entities on startup.

### Backend Services
- **Admin Services** (`backend/admin/`) – Restricted access, not available to driver PWA:
  - `map_service.py` (FastAPI): Serves geo-snapped data for the admin dashboard and reward endpoints.
  - `auth_service.py` (FastAPI): Dedicated authentication server for login/register (port 8002).
  - `camera_event_service.py` (FastAPI): Processes camera events with VLM and updates Fiware (port 8003).
  - `orion_bridge_service.py`: MQTT-to-InfluxDB bridge for persisting Orion updates.
  - `llm_service.py` (Flask): Proxy for the LLM chat assistant (port 9090).
  - `processing_service.py`: Handles data processing and analysis tasks.
  - `camera_fiware_service.py`: Manages FIWARE camera entities and interactions.

- **Public Services** (`backend/public/`) – Accessible to driver PWA:
  - `frontend_map_api.py` (FastAPI): PWA-facing API (Port 8010) for serving traffic overlays, authentication, and rewards.
  - `auth_router.py` (FastAPI): Driver authentication endpoints for login, registration, and token refresh.
  - `reward_service.py`: Calculates driver streaks and reward data.
  - `reward_router.py`: FastAPI router for `/api/rewards/*` endpoints.
  - `report_service.py`: Handles driver-submitted accident reports with UUID-based IDs.
  - `report_router.py`: FastAPI router for `/pwa/reports` endpoint (POST accident reports).

- **Shared Utilities** (`backend/shared/`) – Common configuration and database access:
  - `config.py`: Environment variable management (includes VLM settings).
  - `database.py`: MySQL connection utilities.

## Data & Infrastructure

- **FIWARE Orion Context Broker** – Central NGSI v2 endpoint for simulated entities.
- **MySQL 8.0** – Relational database for static city data (road network, parking entities), user management (admin dashboard with whitelist), and driver profiles (driver PWA authentication and rewards). Runs in Docker.
- **InfluxDB 2.x** – Stores time-series data (accidents, traffic flow) for historical analysis.
- **Grafana** – Visualizes KPIs and is embedded inside the City Dashboard.

### External Services & APIs
- **OpenStreetMap (via Overpass API)** – Source of the Patras road network geometry (`db_init/seed_data/patras_roads.geojson`).
- **GraphHopper API** – Provides routing for the Driver Companion App.
- **Vision Language Model (VLM) API** – External service for image analysis:
  - Vehicle counting in traffic monitoring events
  - License plate OCR for violation detection
  - Parking spot counting
  - Default: `http://labserver.sense-campus.gr:7080/vision`

- **Leaflet** – Open-source JavaScript library for interactive maps.

## Docker Architecture

The project uses a multi-container architecture with 8 services organized in three layers:

**Infrastructure Layer**:
- `iot_database`: MySQL 8.0 database (port 3306)
- `iot_phpmyadmin`: Database admin UI (port 8081)

**Application Layer**:
- `iot_admin_apis`: Admin backend services (ports 8000, 8002, 8003, 9090)
  - Port 8000: Map API for dashboard data
  - Port 8002: Authentication API
  - Port 8003: Camera Event API (processes VLM events)
  - Port 9090: LLM chat service
  - Background: Orion bridge for MQTT → InfluxDB sync
  
- `iot_public_apis`: Driver-facing backend (port 8010)
  - Frontend Map API for PWA with traffic overlays
  - Reward calculations
  
- `iot_fakers`: Data generators
  - Simulates traffic, parking, accidents, violations

**Presentation Layer**:
- `iot_city_dashboard`: Admin web interface (port 5000)
  - Vanilla JS + Leaflet maps
  - Grafana dashboards embedded
  
- `iot_drivers_pwa`: Driver mobile app (port 5173)
  - React + Vite
  - Geolocation and navigation

**Network**: All containers connected via `iot_network` (Docker bridge) for service discovery.

### Container Details

| Container | Image | Purpose | Ports | Dependencies |
|-----------|-------|---------|-------|--------------|
| `iot_database` | mysql:8.0 | Database server | 3306 | - |
| `iot_phpmyadmin` | phpmyadmin | DB admin UI | 8081 | iot_database |
| `iot_admin_apis` | Custom (Dockerfile.admin_api) | Admin backend services | 8000, 8002, 8003, 9090 | iot_database |
| `iot_public_apis` | Custom (Dockerfile.public_api) | Public backend services | 8010 | iot_database |
| `iot_fakers` | Custom (Dockerfile.fakers) | Data generators/simulators | - | iot_database |
| `iot_city_dashboard` | Custom (Dockerfile.city_dashboard) | Admin frontend | 5000 | - |
| `iot_drivers_pwa` | Custom (Dockerfile.drivers_pwa) | Driver frontend | 5173 | - |
| `iot_edge_detection` | Custom (Dockerfile.edge_detection) | Edge YOLOv8 processor | - | iot_admin_apis |

## Running the Stack

The project runs entirely in Docker containers for consistency and ease of deployment.

### Prerequisites
- Install [Docker Desktop](https://www.docker.com/products/docker-desktop)
- **Minimum 15GB free disk space** (Docker images + dependencies)
- Ensure ports 5000, 5173, 8000, 8002, 8003, 8010, 8081, 9090, 3306 are available
- Copy `.env.example` to `.env` in the root directory and update with your credentials (InfluxDB token, API keys)

### Starting the Stack

> ** First Build Warning**: The initial `docker compose up -d --build` can take 20-30 minutes due to edge detection dependencies (PyTorch, Ultralytics YOLOv8). If you want to skip edge detection for faster testing, comment out the `iot_edge_detection` service in `docker-compose.yml`.

```bash
# Build and start all containers
docker compose up -d --build
```

### Stopping the Stack

```bash
docker compose down

# Remove volumes (reset database)
docker compose down -v
```

### What Gets Started

1. **Database Services** (startup order: first)
   - MySQL database with auto-initialization from `db_init/`
   - phpMyAdmin UI for database management

2. **Admin Backend** (`iot_admin_apis`) - starts after database
   - Map API (port 8000): Serves dashboard data
   - Auth API (port 8002): User authentication
   - Camera Event API (port 8003): Processes camera events with VLM
   - LLM Service (port 9090): AI analysis proxy
   - Orion Bridge: Subscribes to Orion updates via MQTT

3. **Public Backend** (`iot_public_apis`) - starts after database
   - Frontend Map API (port 8010): Driver PWA data access
   - Reward API: Driver streak and reward calculations

4. **Data Generators** (`iot_fakers`) - starts after database
   - Continuously generates simulated events:
   - Traffic observations (every 5 seconds)
   - Parking occupancy updates (every 10 seconds)
   - Random accidents (every 60 seconds)
   - Traffic violations (on generated events)

5. **Edge Detection** (`iot_edge_detection`) - starts after admin backend
   - Processes video files from `edge_detection/videos/` folder
   - YOLOv8 inference with vehicle tracking
   - Sends detected events to backend Camera Event API (port 8003)
   - Detects: parking violations, double-parking, traffic flow
   - Automatic retry logic with silent failure handling

6. **Frontend Applications** (no dependencies)
   - City Dashboard (port 5000): Admin visualization
   - Driver PWA (port 5173): Driver mobile app

**Service Access**:
- **City Dashboard**: [http://localhost:5000](http://localhost:5000)
- **Driver App**: [http://localhost:5173](http://localhost:5173)
- **Database Admin**: [http://localhost:8081](http://localhost:8081)

**Admin APIs** (not accessible to drivers):
- Map API: [http://localhost:8000/docs](http://localhost:8000/docs)
- Auth API: [http://localhost:8002/docs](http://localhost:8002/docs)
- Camera Event API: [http://localhost:8003/docs](http://localhost:8003/docs)
- LLM Service: [http://localhost:9090](http://localhost:9090)

**Public API** (Driver PWA only):
- Frontend Map API: [http://localhost:8010/docs](http://localhost:8010/docs)

## Camera Event Processing System

Real-time camera event processing using Vision Language Model (VLM) analysis.

### Event Types
1. **Traffic Monitoring** - Count vehicles, calculate traffic density
   - Uses YOLO-detected vehicle data to count vehicles and calculate traffic density
   - Updates `TrafficFlowObserved` entity with density and congestion level

2. **Double Parking** - Detect parking violations
   - VLM extracts license plate via OCR
   - Updates driver profile if plate matched
   - Creates `TrafficViolation` entity in Fiware

3. **Red Light Violation** - Detect traffic violations
   - VLM extracts license plate via OCR
   - Updates driver profile if plate matched
   - Creates `TrafficViolation` entity in Fiware

4. **Parking Status** - Monitor parking occupancy
   - VLM counts free parking spots
   - Updates `OnStreetParking` entity availability

### Camera Setup
Two pre-configured cameras in Vrachnaiika, Patras:
- **CAM-VRACH-01**: Traffic & Parking monitoring (38.271°N, 21.782°E)
  - Event Types: `traffic_monitoring`, `parking_status`, `double_parking`
  - Linked Fiware Entities:
    - Traffic Flow: `urn:ngsi-ld:TrafficFlowObserved:VRACH-01`
    - Parking: `urn:ngsi-ld:OnStreetParking:P-095`
- **CAM-VRACH-02**: Red light violation monitoring (38.2685°N, 21.7795°E)
  - Event Types: `red_light_violation`
  - No Fiware traffic/parking entities (violations only)

All Fiware entities are automatically created on startup and follow the [FIWARE Smart Data Model](https://smart-data-models.github.io/) schema with the owner attribute set to `week4_up1125093`.

**Important**: Camera parking entities (P-002, P-095) are excluded from the `parking_entities` table to prevent data simulators from overwriting real camera observations. These entities exist only in Fiware and are updated exclusively by camera VLM analysis.

## Authentication

The project implements two separate authentication systems for different user types:

### City Dashboard (Admin)
- **Access**: Restricted to whitelisted email addresses
- **Whitelist**: Configured in `backend/shared/config.py` (`WHITELISTED_EMAILS`)
- **Endpoints**: `http://localhost:8002/login`, `http://localhost:8002/register`
- **Features**: JWT-based authentication, password hashing (PBKDF2), 30-minute token expiration
- **User Table**: `users` table in MySQL

### Driver PWA
- **Access**: Open registration (no whitelist)
- **Endpoints**: `http://localhost:8010/public/login`, `http://localhost:8010/public/register`, `http://localhost:8010/public/refresh`
- **Features**: JWT-based authentication, password hashing (PBKDF2), 30-minute token expiration with automatic 15-minute refresh
- **User Table**: `driver_profiles` table in MySQL (includes reward points, streaks, and license plate)
- **Session Persistence**: Tokens stored in localStorage, users remain logged in until sign-out or app closure
- **Protected Endpoints**: All reward endpoints require authentication and extract driver ID from token

**Creating Test Accounts**:

*City Dashboard (Admin)*:
1. Add your email to `WHITELISTED_EMAILS` in `backend/shared/config.py`
2. Navigate to [http://localhost:5000](http://localhost:5000)
3. Click "Register" and create an account

*Driver PWA*:
1. Navigate to [http://localhost:5173](http://localhost:5173)
2. Click "Register" and create an account (no whitelist required)
3. Optionally provide your license plate during registration



## Edge Detection and Computer Vision

Vehicles are detected using a pretrained YOLOv8 nano model in the edge detection container. The pipeline supports counting and parking occupancy detection, with events processed via the Camera Event API.

Real-time YOLOv8 inference engine for camera feeds. Detects parking violations, traffic flow, and double-parking violations by processing video streams in `edge_detection/videos/`. Events are sent via POST to the backend Camera Event API. Zone definitions and configuration are located in `edge_detection/zones/zones.json` and `edge_detection/config.json`.

## Database Schema

### Key Tables

| Table | Purpose | Key Fields |
|-------|---------|-----------|
| `users` | Admin authentication | id, username, email, password_hash, role |
| `driver_profiles` | Driver management & rewards | id, username, license_plate, last_traffic_violation, last_parking_violation, current_points |
| `camera_devices` | Camera registration | camera_id, location_lat/lng, traffic_flow_entity_id, onstreet_parking_entity_id |
| `parking_entities` | Parking zone data | id, entity_id, lat, lng, total_spots |
| `traffic_entities` | Traffic segment data | id, entity_id, lat, lng |
| `road_segments` | Road network geometry | id, lat1, lng1, lat2, lng2 |
| `rewards_catalog` | Available rewards | id, name, description, points_cost |
| `milestone_awards` | Reward tracking | id, driver_id, streak_type, milestone_days, points_awarded |

See [db_init/01_schema.sql](db_init/01_schema.sql) for complete schema.

## Collaboration Rules
To keep our workflow clean and consistent:

1. Do not push directly to `main`. Create a branch: `feature/<short-description>` or `fix/<short-description>`.
2. Open a Merge Request/PR when work is ready. Get a review before merging.
3. Write meaningful commit messages (e.g., `feat: add parking recommendation logic`).
4. Keep commits small and clear; avoid giant “everything at once” commits.
5. Use English for all commit messages, variable names, and comments.
