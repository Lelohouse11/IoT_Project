# IoT_Project – Live Map, Accident Faker, and Grafana

This repo contains a simple city admin UI (Leaflet), an accident data faker that writes to InfluxDB, and a tiny FastAPI service that exposes recent accidents for the map. You can serve the frontend with Live Server while running the backend locally.

## Overview
- Frontend (Leaflet): `city_side/public/index.html` loads `city_side/src/js/app.js` and the map with clustering and layers.
- Accident Faker (InfluxDB): `accident_faker.py` writes fake accident events into the same database used by `sensor_faker.py`.
- API (FastAPI): `accidents_api.py` serves recent active accidents for the map.
- Grafana: Create a panel “Accidents per Hour” and embed it into the existing iframe on the city-side dashboard.
