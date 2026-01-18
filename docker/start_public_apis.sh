#!/bin/bash
# ---------------------------------------------------------------------------
# Script: start_public_apis.sh
# Description: Starts public-facing API services accessible to driver PWA.
#              Includes Frontend Map API for traffic/parking data.
#              This is the ONLY backend service the driver PWA can access.
# ---------------------------------------------------------------------------

echo "Starting Public Frontend Map API..."
# PWA-only API serving limited traffic and parking data
python backend/public/frontend_map_api.py &

echo "Public APIs started successfully"

# Keep container alive
wait
