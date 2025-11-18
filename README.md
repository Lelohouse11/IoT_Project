# IoT Project Overview

Compact toolkit for simulating, collecting, and visualizing city traffic incidents.

## Modules & Tech
- **City Map (Leaflet + vanilla JS)** – `city_side/…` renders live accidents, pulls data from the REST API, and embeds Grafana widgets.
- **Accident Faker (Python + requests)** – `data_faker/accident_faker.py` synthesizes NGSI v2 `TrafficAccident` entities, posts them to the FIWARE Orion Context Broker, and handles collision retries automatically.
- **MQTT → Influx Bridge (Python + paho + influxdb-client)** – `api/orion_notification_server.py` listens to Orion MQTT notifications, filters entities by service path, and writes them into InfluxDB.
- **Accidents REST API (FastAPI + InfluxDB)** – `api/accidents_api.py` exposes `/api/accidents/recent`, querying Influx for the latest active accidents used by the frontend.
- **Orion Subscription Helper (Flask + requests)** – `api/orion_subscription_server.py` spins up a public webhook, ensures an Orion subscription exists for your service path, and dumps notifications for debugging.
- **LLM Proxy (Flask)** – `api/llm_server.py` lightweight relay to upstream chat models; useful for experimenting with Copilot-style hints in the UI.
- **Debug Utilities (Python)** – `debug/print_context.py` prefixes every `print()` with `[module.function]` for traceable logs.

## Data & Infra
- **FIWARE Orion Context Broker** – central NGSI v2 endpoint for accidents created by the faker.
- **InfluxDB 2.x** – stores accident time series written by the MQTT bridge; retention/measurements documented in `api/orion_notification_server.py`.
- **Grafana** – visualizes KPIs (e.g., accidents per hour) and is embedded inside the Leaflet dashboard.

## Running the Stack
1. Install dependencies: `pip install` (`requests`, `paho-mqtt`, `influxdb-client`, `fastapi`, `uvicorn`, `flask`).
2. Start the data fakers (`/data_faker`): run `accident_faker.py`.
3. Launch APIs (`/api`): `accidents_api.py`,`llm_server.py`,`orion_notification_server.py` (not `orion_subscription_server.py`).
4. Serve the frontend (Live Server or any static host).
