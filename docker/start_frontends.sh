#!/bin/bash
set -e

# ---------------------------------------------------------------------------
# Script: start_frontends.sh
# Description: Starts the frontend applications for the IoT Smart City project.
#              Launches the City Dashboard (Admin) and the Driver PWA.
# ---------------------------------------------------------------------------

echo "Starting City Dashboard (Port 5000)..."
cd /app/city_dashboard
npx http-server . -p 5000 --cors &
DASHBOARD_PID=$!

echo "Starting Driver PWA (Port 5173)..."
cd /app/drivers_side_pwa
if [ ! -d node_modules ]; then
    echo "Installing dependencies..."
    npm ci --prefer-offline --no-audit
fi
npm run dev -- --host 0.0.0.0 --port 5173 &
PWA_PID=$!

echo "Frontends started (Dashboard PID: $DASHBOARD_PID, PWA PID: $PWA_PID)"
wait $DASHBOARD_PID $PWA_PID