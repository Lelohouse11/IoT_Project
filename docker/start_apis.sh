#!/bin/bash
# ---------------------------------------------------------------------------
# Script: start_apis.sh
# Description: Starts all backend API services for the IoT Smart City project.
#              Includes Map API, Auth API, Orion Bridge, and LLM Service.
#              Waits for the database migration to complete before starting.
# ---------------------------------------------------------------------------

# Start all APIs in the background

echo "Waiting for DB..."
# Ensure database schema is up to date
python db_init/migrate_to_db.py

echo "Starting Map Data API..."
# Serves map data (accidents, traffic, parking)
python -m uvicorn backend.map_service:app --host 0.0.0.0 --port 8000 &

echo "Starting Auth API..."
# Handles user authentication and profile management
python -m uvicorn backend.auth_service:app --host 0.0.0.0 --port 8002 &

echo "Starting Frontend Map API..."
# Dedicated PWA-facing API
python backend/frontend_map_api.py &

echo "Starting Orion Notification Server..."
# Bridges Orion Context Broker updates to the system
python backend/orion_bridge_service.py &

echo "Starting LLM Server..."
# Provides AI analysis capabilities
python backend/llm_service.py &

# Keep container alive
wait