#!/bin/bash
# ---------------------------------------------------------------------------
# Script: start_admin_apis.sh
# Description: Starts all admin-only backend API services.
#              Includes Map API, Auth API, Orion Bridge, and LLM Service.
#              These services are NOT accessible to the driver PWA.
# ---------------------------------------------------------------------------

echo "========================================="
echo "Admin APIs Container Starting..."
echo "========================================="

echo "Waiting for database and running migrations..."
# Ensure database schema is up to date
python db_init/migrate_to_db.py

if [ $? -ne 0 ]; then
    echo "ERROR: Database migration failed!"
    exit 1
fi

echo ""
echo "Initializing Fiware entities..."
# Initialize Fiware entities (parking, traffic, camera monitoring)
python -c "from backend.admin.fiware_entities_init import ensure_fiware_entities; ensure_fiware_entities()"

if [ $? -ne 0 ]; then
    echo "WARNING: Fiware entity initialization failed, but continuing..."
fi

echo ""
echo "========================================="
echo "Starting Admin API Services..."
echo "========================================="

echo "[1/6] Starting Map Data API (Admin) on port 8000..."
# Serves map data (accidents, traffic, parking, violations) + rewards
python -m uvicorn backend.admin.map_service:app --host 0.0.0.0 --port 8000 &

echo "[2/6] Starting Auth API (Admin) on port 8002..."
# Handles user authentication and profile management
python -m uvicorn backend.admin.auth_service:app --host 0.0.0.0 --port 8002 &

echo "[3/6] Starting Camera Event API (Admin) on port 8003..."
# Processes camera events with VLM and updates Fiware
python -m uvicorn backend.admin.camera_event_service:app --host 0.0.0.0 --port 8003 &

echo "[4/6] Starting Orion Bridge Service..."
# Bridges Orion Context Broker updates to InfluxDB
python backend/admin/orion_bridge_service.py &

echo "[5/6] Starting LLM Service (Admin) on port 9090..."
# Provides AI analysis capabilities for city dashboard
python backend/admin/llm_service.py &

echo ""
echo "========================================="
echo "All Admin APIs started successfully!"
echo "========================================="
echo "Available services:"
echo "  - Map API:          http://localhost:8000"
echo "  - Auth API:         http://localhost:8002"
echo "  - Camera Event API: http://localhost:8003"
echo "  - LLM Service:      http://localhost:9090"
echo "  - Orion Bridge:     Running in background"
echo "========================================="

# Keep container alive
wait
