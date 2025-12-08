# IoT Project Overview

Compact toolkit for simulating, collecting, and visualizing city traffic incidents.

## Modules & Tech
- **City Dashboard** (`city_side`) – Vanilla JS + Leaflet frontend. Renders live accidents, parking, and traffic data. Features a modular architecture (`config.js`, `layout.js`) and embeds Grafana widgets.
- **Driver Companion App** (`drivers_side_pwa`) – React + Vite PWA. Provides a mobile-first interface for drivers to view alerts and report incidents.
- **Data Fakers** (`data_faker/`) – Python scripts simulating smart city entities:
  - `accident_faker.py`: Synthesizes `TrafficAccident` entities.
  - `traffic_violation_faker.py`: Emits `TrafficViolation` detections (red light, illegal parking).
  - `parking_faker.py`: Simulates `OnStreetParking` occupancy.
  - `traffic_faker.py`: Drives `TrafficFlowObserved` entities.
- **Backend Services** (`api/`) – Python services bridging data and serving the frontend:
  - `map_data_api.py` (FastAPI): Serves geo-snapped data for the map.
  - `orion_notification_server.py`: MQTT-to-InfluxDB bridge for persisting Orion updates.
  - `llm_server.py` (Flask): Proxy for the LLM chat assistant.
  - `orion_subscription_server.py`: Helper to manage Orion subscriptions.

## Data & Infra
- **FIWARE Orion Context Broker** – Central NGSI v2 endpoint for simulated entities.
- **InfluxDB 2.x** – Stores time-series data (accidents, traffic flow) for historical analysis.
- **Grafana** – Visualizes KPIs and is embedded inside the City Dashboard.

### External Services & APIs
- **OpenStreetMap (via Overpass API)** – Source of the Patras road network geometry used by the fakers (`data_faker/patras_roads.geojson`).
- **GraphHopper API** – Provides routing and navigation for the Driver Companion App (requires API key).
- **Leaflet** – Open-source JavaScript library for interactive maps.

## Configuration
The project uses environment variables for configuration. 
1. Copy `.env.example` to `.env` in the root directory.
2. Update the values in `.env` with your specific credentials (InfluxDB token, API keys, etc.).
3. The `api/config.py` module loads these settings automatically.

## Running the Stack
1. **Install Python dependencies**:
   ```bash
   python -m pip install -r requirements.txt
   ```
2. **Install Node dependencies** (for the PWA):
   ```bash
   cd drivers_side_pwa
   npm install
   cd ..
   ```
3. **Start the Stack**:
   - **VS Code (Recommended)**: Go to "Run and Debug" and select **Start IoT Stack**. This launches all fakers, APIs, and frontends simultaneously.
   - **Manual**:
     - Run fakers: `python data_faker/accident_faker.py`, etc.
     - Run APIs: `python -m uvicorn api.map_data_api:app --reload`, `python api/llm_server.py`.
     - Serve City Side: `python -m http.server 5000 --directory city_side`.
     - Serve Driver PWA: `npm run dev` inside `drivers_side_pwa`.

## Project Structure
```
IoT_Project/
├── api/                 # Backend APIs & Bridges
├── city_side/           # Admin Dashboard (JS/HTML)
├── data_faker/          # Simulation Scripts
├── drivers_side_pwa/    # Driver App (React)
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
