#!/bin/bash
# ---------------------------------------------------------------------------
# Script: start_admin_apis.sh
# Description: Starts all admin-only backend API services.
#              Includes Map API, Auth API, Orion Bridge, and LLM Service.
#              These services are NOT accessible to the driver PWA.
# ---------------------------------------------------------------------------

echo "Waiting for DB..."
# Ensure database schema is up to date
python db_init/migrate_to_db.py

echo "Starting Map Data API (Admin)..."
# Serves map data (accidents, traffic, parking, violations) + rewards
python -m uvicorn backend.admin.map_service:app --host 0.0.0.0 --port 8000 &

echo "Starting Auth API (Admin)..."
# Handles user authentication and profile management
python -m uvicorn backend.admin.auth_service:app --host 0.0.0.0 --port 8002 &

echo "Starting Orion Bridge Service..."
# Bridges Orion Context Broker updates to InfluxDB
python backend/admin/orion_bridge_service.py &

echo "Starting LLM Service (Admin)..."
# Provides AI analysis capabilities for city dashboard
python backend/admin/llm_service.py &

echo "Admin APIs started successfully"

# Keep container alive
wait
