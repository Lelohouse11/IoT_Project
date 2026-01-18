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

echo "Initializing Traffic Segments..."
# Create initial traffic entities in Orion
python backend/simulation/traffic_segments_init.py

echo "Initializing Parking Zones..."
# Create initial parking entities in Orion
python backend/simulation/parking_zones_init.py

echo "Starting Accident Faker..."
# Simulates random traffic accidents
python backend/simulation/accident_generator.py &

echo "Starting Parking Faker..."
# Simulates parking spot occupancy changes
python backend/simulation/parking_generator.py &

echo "Starting Traffic Faker..."
# Simulates traffic flow speed and density
python backend/simulation/traffic_generator.py &

echo "Starting Traffic Violation Faker..."
# Simulates various traffic violations
python backend/simulation/traffic_violation_generator.py &

# Keep container alive
wait