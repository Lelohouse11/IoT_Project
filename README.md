# IoT Project Overview

Compact toolkit for simulating, collecting, and visualizing city traffic incidents.

## Modules & Tech
- City Map (Leaflet + vanilla JS) – `city_side` renders live accidents, pulls data from the REST API, and embeds Grafana widgets.
- Accident Faker (Python + requests) – `data_faker/accident_faker.py` synthesizes NGSI v2 `TrafficAccident` entities.
- Traffic Violation Faker (Python + requests) – `data_faker/traffic_violation_faker.py` emits Smart Data Models `TrafficViolation` detections (double parking, red light, no stopping, etc.) aligned to Patras roads.
- Parking Faker (Python + requests) – `data_faker/parking_faker.py` simulates `OnStreetParking` occupancy.
- Traffic Flow Faker (Python + requests) – `data_faker/traffic_faker.py` drives `TrafficFlowObserved` entities.
- MQTT → Influx Bridge (Python) – `api/orion_notification_server.py` listens to Orion MQTT notifications and writes them into InfluxDB.
- Map Data REST API (FastAPI) – `api/map_data_api.py` exposes `/api/accidents/recent` and `/api/parking/recent`.
- Orion Subscription Helper (Flask) – `api/orion_subscription_server.py` ensures an Orion subscription exists and dumps notifications.
- LLM Proxy (Flask) – `api/llm_server.py` lightweight relay to upstream chat models.
- Debug Utilities (Python) – `debug/print_context.py` prefixes every `print()` with `[module.function]` for traceable logs.

## Data & Infra
- FIWARE Orion Context Broker – central NGSI v2 endpoint for simulated entities.
- InfluxDB 2.x – stores accident time series written by the MQTT bridge.
- Grafana – visualizes KPIs (e.g., accidents per hour) and is embedded inside the Leaflet dashboard.

## Running the Stack
1. Install Python dependencies:
```
python -m pip install -r requirements.txt
```
2. Start the data fakers (`/data_faker`): `accident_faker.py`, `parking_faker.py`, `traffic_faker.py`, `traffic_violation_faker.py`.
3. Launch APIs (`/api`): `map_data_api.py`, `llm_server.py`, `orion_notification_server.py` (not `orion_subscription_server.py`).
4. Serve the frontends: host `city_side/public` (e.g., `python -m http.server 5000`) and run `npm install` once then `npm run dev` in `drivers_side_pwa`.

### VS Code Start (recommended)
- In Run and Debug pick **Start IoT Stack** to launch all services/frontends via `.vscode/tasks.json` / `.vscode/launch.json`.
- Individual tasks are available from the Terminal panel dropdown if you want to start components separately.

## Collaboration Rules
To keep our workflow clean and consistent:

1. Do not push directly to `main`. Create a branch: `feature/<short-description>` or `fix/<short-description>`.
2. Open a Merge Request/PR when work is ready. Get a review before merging.
3. Write meaningful commit messages (e.g., `feat: add parking recommendation logic`).
4. Keep commits small and clear; avoid giant “everything at once” commits.
5. Use English for all commit messages, variable names, and comments.
