# IoT Project Overview

Compact toolkit for simulating, collecting, and visualizing city traffic incidents.

## Modules & Tech
- **City Dashboard** (`city_dashboard`) – Vanilla JS + Leaflet frontend. Renders live accidents, parking, and traffic data. Features a modular architecture (`config.js`, `layout.js`) and embeds Grafana widgets.
- **Driver Companion App** (`drivers_side_pwa`) – React + Vite PWA. Provides a mobile-first interface for drivers to view alerts and report incidents. Connects to `backend/frontend_map_api.py` for optimized traffic data.
- **Computer Vision** (`yolov8_tests/`) – Vehicle detection pipeline using YOLOv8n. Analyzes video/images for traffic counting and parking occupancy events.
- **Simulation** (`simulation/`) – Python scripts simulating smart city entities:
  - `accident_generator.py`: Synthesizes `TrafficAccident` entities.
  - `traffic_violation_generator.py`: Emits `TrafficViolation` detections (red light, illegal parking).
  - `parking_generator.py`: Simulates `OnStreetParking` occupancy.
  - `traffic_generator.py`: Drives `TrafficFlowObserved` entities.
- **Backend Services** (`backend/`) – Python services bridging data and serving the frontend:
  - `map_service.py` (FastAPI): Serves geo-snapped data for the map and reward endpoints.
  - `reward_service.py`: Calculates driver streaks and reward data.
  - `reward_router.py`: FastAPI router for `/api/rewards/*` endpoints.
  - `auth_service.py` (FastAPI): Dedicated authentication server for login/register.
  - `frontend_map_api.py` (FastAPI): Dedicated PWA-facing API (Port 8010) for serving traffic overlays.
  - `orion_bridge_service.py`: MQTT-to-InfluxDB bridge for persisting Orion updates.
  - `llm_service.py` (Flask): Proxy for the LLM chat assistant.
  - `orion_subscription_server.py`: Helper to manage Orion subscriptions.

## Data & Infra
- **FIWARE Orion Context Broker** – Central NGSI v2 endpoint for simulated entities.
- **MySQL 8.0** – Relational database for static city data (road network, parking entities), user management, and driver profiles for rewards. Runs in Docker.
- **InfluxDB 2.x** – Stores time-series data (accidents, traffic flow) for historical analysis.
- **Grafana** – Visualizes KPIs and is embedded inside the City Dashboard.

### External Services & APIs
- **OpenStreetMap (via Overpass API)** – Source of the Patras road network geometry used by the fakers (`db_init/seed_data/patras_roads.geojson`).
- **GraphHopper API** – Provides routing and navigation for the Driver Companion App (requires API key).
- **Leaflet** – Open-source JavaScript library for interactive maps.

## Configuration
The project uses environment variables for configuration. 
1. Copy `.env.example` to `.env` in the root directory.
2. Update the values in `.env` with your specific credentials (InfluxDB token, API keys, etc.).
   - Add `SECRET_KEY` for JWT signing (optional, defaults to a dev key).
3. The `backend/config.py` module loads these settings automatically.

## Authentication
The system implements a secure, standard-library based JWT authentication mechanism.

- **Registration**: Users can register at `/register.html`. Registration is restricted to a whitelist of email addresses defined in `backend/config.py`.
- **Login**: Users log in at `/login.html` to receive an access token.
- **Account Management**: Users can view their profile and permanently delete their account via the dashboard profile menu.
- **Whitelist**: By default, allowed emails are `admin@smartcity.com`, `leander@smartcity.com`, and `test@test.com`.
- **Security**: Passwords are hashed using PBKDF2 (SHA256). Tokens are signed using HMAC-SHA256.

## Running the Stack

You can run the project in two modes: **Local Development** (best for editing code) or **Full Docker** (best for running the complete system cleanly).

### Option 1: Local Development (Hybrid)
Runs the database in Docker, but executes Python scripts and Node apps locally on your machine. This allows for easy debugging and hot-reloading.

1. **Install Dependencies**:
   ```bash
   # Python
   python -m pip install -r requirements.txt
   
   # Node.js (Driver App)
   cd drivers_side_pwa
   npm install
   cd ..
   ```
2. **Start via VS Code**:
   - Go to **Run and Debug** (Ctrl+Shift+D).
   - Select **Start IoT Stack (Local Dev)**.
   - This launches the DB, runs migrations, and starts all services in separate terminals.

### Option 2: Full Docker Stack (Containerized)
Runs the entire system (Fakers, APIs, Frontends, Database) inside containers. No local Python/Node installation required (except for Docker).

1. **Prerequisites**: Install Docker Desktop.
2. **Start via VS Code**:
   - Go to **Run and Debug**.
   - Select **Start IoT Stack (Docker)**.
   - To stop, select **Stop IoT Stack (Docker)**.
3. **Start via Terminal**:
   ```bash
   docker compose up -d --build
   ```

**Docker Service Ports**:
- **City Dashboard**: [http://localhost:5000](http://localhost:5000)
- **Driver App**: [http://localhost:5173](http://localhost:5173)
- **Auth API**: [http://localhost:8002](http://localhost:8002)
- **Map API**: [http://localhost:8000](http://localhost:8000)
- **Frontend Map API**: [http://localhost:8010](http://localhost:8010)
- **LLM API**: [http://localhost:9090](http://localhost:9090)
- **phpMyAdmin**: [http://localhost:8081](http://localhost:8081)

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
├── city_dashboard/      # Admin Dashboard (JS/HTML)
├── simulation/          # Simulation Scripts
├── db_init/             # SQL Schema & Migration Scripts
│   └── seed_data/       # Raw JSON/GeoJSON Data Files
├── drivers_side_pwa/    # Driver App (React)
├── yolov8_tests/        # Computer Vision/YOLO Experiments
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
