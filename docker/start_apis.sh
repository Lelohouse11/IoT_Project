#!/bin/bash
# Start all APIs in the background

echo "Waiting for DB..."
python db_init/migrate_to_db.py

echo "Starting Map Data API..."
python -m uvicorn api.map_data_api:app --host 0.0.0.0 --port 8000 &

echo "Starting Auth API..."
python -m uvicorn api.auth_server:app --host 0.0.0.0 --port 8002 &

echo "Starting Orion Notification Server..."
python api/orion_notification_server.py &

echo "Starting LLM Server..."
python api/llm_server.py &

# Keep container alive
wait