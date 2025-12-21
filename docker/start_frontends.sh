#!/bin/bash
# ---------------------------------------------------------------------------
# Script: start_frontends.sh
# Description: Starts the frontend applications for the IoT Smart City project.
#              Launches the City Dashboard (Admin) and the Driver PWA.
# ---------------------------------------------------------------------------

# Start Frontends

echo "Starting City Dashboard (Port 5000)..."
# Use http-server (Node) to serve the static site
npx http-server city_dashboard -p 5000 --cors &

echo "Starting Driver PWA (Port 5173)..."
# Install dependencies and start the Vite dev server for the PWA
cd drivers_side_pwa
npm install
npm run dev -- --host 0.0.0.0 --port 5173 &

# Keep container alive
wait