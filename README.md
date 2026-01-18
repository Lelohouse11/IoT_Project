# IoT Project Overview

Compact toolkit for simulating, collecting, and visualizing city traffic incidents.

## Modules & Tech
- **City Dashboard** (`city_dashboard`) – Vanilla JS + Leaflet frontend. Renders live accidents, parking, and traffic data. Features a modular architecture (`config.js`, `layout.js`) and embeds Grafana widgets. Includes user authentication with JWT-based login/registration restricted to a whitelist of email addresses (defined in `backend/shared/config.py`).
- **Driver Companion App** (`drivers_side_pwa`) – React + Vite PWA. Provides a mobile-first interface for drivers to view alerts and submit accident reports. Features include:
  - Real-time traffic and parking data visualization
  - Driver reward tracking with streak progress
  - Accident reporting with automatic geolocation and 30-minute expiration
  - Connects to `backend/public/frontend_map_api.py` for optimized traffic data and `/pwa/reports` for report submission.
- **Computer Vision** (`yolov8_tests/`) – Vehicle detection pipeline using YOLOv8n. Analyzes video/images for traffic counting and parking occupancy events.
- **Simulation** (`backend/simulation/`) – Python scripts simulating smart city entities:
  - `accident_generator.py`: Synthesizes `TrafficAccident` entities.
  - `traffic_violation_generator.py`: Emits `TrafficViolation` detections (red light, illegal parking).
  - `parking_generator.py`: Simulates `OnStreetParking` occupancy.
  - `traffic_generator.py`: Drives `TrafficFlowObserved` entities.
- **Backend Services** (`backend/`) – Python services organized by access level for security:
  - **Admin Services** (`backend/admin/`) – Restricted access, not available to driver PWA:
    - `map_service.py` (FastAPI): Serves geo-snapped data for the admin dashboard and reward endpoints.
    - `auth_service.py` (FastAPI): Dedicated authentication server for login/register.
    - `orion_bridge_service.py`: MQTT-to-InfluxDB bridge for persisting Orion updates.
    - `llm_service.py` (Flask): Proxy for the LLM chat assistant.
    - `report_expiration_service.py`: Background scheduler that auto-clears driver reports after 30 minutes.
  - **Public Services** (`backend/public/`) – Accessible to driver PWA:
    - `frontend_map_api.py` (FastAPI): PWA-facing API (Port 8010) for serving traffic overlays.
    - `reward_service.py`: Calculates driver streaks and reward data.
    - `reward_router.py`: FastAPI router for `/api/rewards/*` endpoints.
    - `report_service.py`: Handles driver-submitted accident reports with UUID-based IDs.
    - `report_router.py`: FastAPI router for `/pwa/reports` endpoint (POST accident reports).
  - **Shared Utilities** (`backend/shared/`) – Common configuration and database access:
    - `config.py`: Environment variable management.
    - `database.py`: MySQL connection utilities.

## Data & Infra
- **FIWARE Orion Context Broker** – Central NGSI v2 endpoint for simulated entities.
- **MySQL 8.0** – Relational database for static city data (road network, parking entities), user management, and driver profiles for rewards. Runs in Docker.
- **InfluxDB 2.x** – Stores time-series data (accidents, traffic flow) for historical analysis.
- **Grafana** – Visualizes KPIs and is embedded inside the City Dashboard.

### External Services & APIs
- **OpenStreetMap (via Overpass API)** – Source of the Patras road network geometry used by the fakers (`db_init/seed_data/patras_roads.geojson`).
- **GraphHopper API** – Provides routing and navigation for the Driver Companion App (requires API key).
- **Geolocation API** – Browser-based geolocation service used by the Driver PWA for real-time location tracking.
- **Leaflet** – Open-source JavaScript library for interactive maps.

## Running the Stack

The project runs entirely in Docker containers for consistency and ease of deployment.

### Prerequisites
- Install [Docker Desktop](https://www.docker.com/products/docker-desktop)
- Ensure ports 5000, 5173, 8000, 8002, 8010, 8081, 9090, 3306 are available
- Copy `.env.example` to `.env` in the root directory and update with your credentials (InfluxDB token, API keys)

### Starting the Stack

```bash
docker compose up -d --build
```

### Stopping the Stack

```bash
docker compose down
```

### What Gets Started
The Docker stack includes separate containers:
- **Database Services**: MySQL database + phpMyAdmin admin UI
- **Admin Backend** (`iot_admin_apis`): Auth API, Map API, LLM Service, Orion Bridge (ports 8000, 8002, 9090)
- **Public Backend** (`iot_public_apis`): Frontend Map API accessible to driver PWA (port 8010)
- **Data Generators** (`iot_fakers`): Accident, traffic, parking and violation simulators
- **City Dashboard** (`iot_city_dashboard`): Admin frontend (port 5000)
- **Driver PWA** (`iot_drivers_pwa`): Driver-facing frontend (port 5173)

**Service Ports**:
- **City Dashboard**: [http://localhost:5000](http://localhost:5000)
- **Driver App**: [http://localhost:5173](http://localhost:5173)
- **Admin APIs**:
  - Auth API: [http://localhost:8002](http://localhost:8002)
  - Map API: [http://localhost:8000](http://localhost:8000)
  - LLM API: [http://localhost:9090](http://localhost:9090)
- **Public API** (Driver PWA only):
  - Frontend Map API: [http://localhost:8010](http://localhost:8010)
- **Database**:
  - phpMyAdmin: [http://localhost:8081](http://localhost:8081)

## Computer Vision (YOLOv8)
Vehicles are detected using a pretrained YOLOv8 nano model. The pipeline supports counting and parking occupancy detection.

**Setup**:
```bash
python -m pip install -r yolov8_tests/requirements.txt
```

**Running Tests**:
Place media in `yolov8_tests/inputs/` (images or videos).
```bash
python yolov8_tests/run_detection.py [options]
# Options: --images, --videos, --device cuda:0, --conf 0.15
```

**Outputs**:
- Annotated media in `yolov8_tests/outputs/`
- Metadata JSONs for counts and events.

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
├── drivers_side_pwa/    # Driver App (React)
├── yolov8_tests/        # Computer Vision/YOLO Experiments
├── docker/              # Dockerfiles and startup scripts
├── docs/                # Documentation & Ideas
└── .vscode/             # Task & Launch Configs
```

## Collaboration Rules
To keep our workflow clean and consistent:

1. Do not push directly to `main`. Create a branch: `feature/<short-description>` or `fix/<short-description>`.
2. Open a Merge Request/PR when work is ready. Get a review before merging.
3. Write meaningful commit messages (e.g., `feat: add parking recommendation logic`).
4. Keep commits small and clear; avoid giant “everything at once” commits.
5. Use English for all commit messages, variable names, and comments.
