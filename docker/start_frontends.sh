#!/bin/bash
# Start Frontends

echo "Starting City Dashboard (Port 5000)..."
# Use http-server (Node) to serve the static site
npx http-server city_side -p 5000 --cors &

echo "Starting Driver PWA (Port 5173)..."
cd drivers_side_pwa
npm install
npm run dev -- --host 0.0.0.0 --port 5173 &

# Keep container alive
wait