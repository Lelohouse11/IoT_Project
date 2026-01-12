#!/bin/bash
# ---------------------------------------------------------------------------
# Script: start_fakers.sh
# Description: Starts all simulation generators (fakers) for the IoT Smart City project.
#              Generates synthetic data for accidents, parking, traffic flow,
#              and traffic violations.
# ---------------------------------------------------------------------------

# Start all data fakers in the background

echo "Waiting for DB..."
# Ensure database schema is up to date
python db_init/migrate_to_db.py

echo "Waiting for Orion to be ready..."
# Wait for Orion to be accessible
until curl -s http://orion:1026/version > /dev/null 2>&1; do
  echo "Orion is unavailable - sleeping"
  sleep 2
done
echo "Orion is ready!"

echo "Initializing parking zones in Orion..."
# Create initial OnStreetParking entities
python simulation/parking_zones_init.py

echo "Initializing traffic segments in Orion..."
# Create initial TrafficFlowObserved entities
python simulation/traffic_segments_init.py

echo "Starting Accident Faker..."
# Simulates random traffic accidents
python simulation/accident_generator.py &

echo "Starting Parking Faker..."
# Simulates parking spot occupancy changes
python simulation/parking_generator.py &

echo "Starting Traffic Faker..."
# Simulates traffic flow speed and density
python simulation/traffic_generator.py &

echo "Starting Traffic Violation Faker..."
# Simulates various traffic violations
python simulation/traffic_violation_generator.py &

# Keep container alive
wait