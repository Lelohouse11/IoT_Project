# IoT_Project – Live Map, Accident Faker, and Grafana

This repo contains a simple city admin UI (Leaflet), an accident data faker that writes to InfluxDB, and a tiny FastAPI service that exposes recent accidents for the map. You can serve the frontend with Live Server while running the backend locally.

## Overview
- Frontend (Leaflet): `city_side/public/index.html` loads `city_side/src/js/app.js` and the map with clustering and layers.
- Accident Faker (InfluxDB): `accident_faker.py` writes fake accident events into the same database used by `sensor_faker.py`.
- API (FastAPI): `accidents_api.py` serves recent active accidents for the map.
- Grafana: Create a panel “Accidents per Hour” and embed it into the existing iframe on the city-side dashboard.

## Prerequisites
- Python 3.9+
- InfluxDB instance and credentials (see `sensor_faker.py`)
- Grafana (for dashboard panel)
- Live Server extension (e.g., VS Code “Live Server”) to serve the web UI

## Install Python Dependencies
```bash
pip install influxdb-client fastapi uvicorn[standard]
```

## Configure InfluxDB
- Configuration is currently defined in `sensor_faker.py:5`–`sensor_faker.py:12` and reused by other components.
- Consider moving these to environment variables in production.

## Run the Accident Faker
Writes fake accident events (`_measurement = accidents`) with fields including `event` (create|update|clear) and `status` (active|cleared).
```bash
python accident_faker.py --interval 3 \
  --center-lat 38.2464 --center-lng 21.7346 --offset 0.02
```

## Run the Accidents API (FastAPI)
Serves recent active accidents from InfluxDB at `/api/accidents/recent`.
```bash
python accidents_api.py
# or
uvicorn accidents_api:app --host 0.0.0.0 --port 8000
```

## Start the Web App with Live Server
1. Open the folder in VS Code.
2. Right‑click `city_side/public/index.html` and choose “Open with Live Server”.
3. Live Server typically runs at `http://127.0.0.1:5500` (or a similar port).

### Point the Frontend to the API
The map polls the backend every 15s using `window.APP_API_BASE` if provided.

Add this snippet near the end of `city_side/public/index.html` before the app script tag or in the `<head>`:
```html
<script>window.APP_API_BASE = 'http://localhost:8000';</script>
```
The request will target `http://localhost:8000/api/accidents/recent`. CORS is already enabled in `accidents_api.py`.

## Grafana – Accidents per Hour Panel
Create a panel using your InfluxDB datasource and the following Flux to count new accidents per hour:
```flux
from(bucket: "LeandersDB")
  |> range(start: -24h)
  |> filter(fn: (r) => r._measurement == "accidents")
  |> filter(fn: (r) => r._field == "event" and r._value == "create")
  |> map(fn: (r) => ({ r with _value: 1.0 }))
  |> aggregateWindow(every: 1h, fn: sum, createEmpty: false)
  |> yield(name: "accidents_per_hour")
```
Then copy the panel’s share/iframe URL and set it as the `src` of the iframe in `city_side/public/index.html:87`.

## Data Model (InfluxDB)
- Measurement: `accidents`
- Tags: `type=accident`, `severity ∈ {minor, medium, major}`
- Fields: `id (string)`, `desc (string)`, `lat (float)`, `lng (float)`, `event (string)`, `status (string)`
- Time: `WritePrecision.NS`

## Frontend Notes
- Map code and clustering live in `city_side/src/js/map.js`.
- Public API available in the browser console via `window.MapAPI` (e.g., `MapAPI.replaceAccidents([...])`).

## Troubleshooting
- Empty map: ensure the API returns items from Influx (`/api/accidents/recent`).
- CORS issues: `accidents_api.py` enables `allow_origins=["*"]`; verify the API URL matches `APP_API_BASE`.
- No data in Grafana: confirm the faker is running and the Flux query filters match the measurement/fields.

