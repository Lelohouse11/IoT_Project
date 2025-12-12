#!/bin/bash
# Start all data fakers in the background

echo "Waiting for DB..."
python db_init/migrate_to_db.py

echo "Starting Accident Faker..."
python data_faker/accident_faker.py &

echo "Starting Parking Faker..."
python data_faker/parking_faker.py &

echo "Starting Traffic Faker..."
python data_faker/traffic_faker.py &

echo "Starting Traffic Violation Faker..."
python data_faker/traffic_violation_faker.py &

# Keep container alive
wait