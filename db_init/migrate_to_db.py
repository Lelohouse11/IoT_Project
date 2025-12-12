import json
import sys
import time
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from api import database
from data_faker import geo_helpers, parking_zones_init

def wait_for_db(timeout=30, interval=2):
    """Wait for the database to become available."""
    print("Waiting for database connection...")
    start_time = time.time()
    while time.time() - start_time < timeout:
        conn = database.get_db_connection()
        if conn:
            conn.close()
            print("Database is ready.")
            return True
        time.sleep(interval)
        print("Retrying database connection...")
    print("Timed out waiting for database.")
    return False

def migrate_parking():
    """Migrate legacy parking entities from JSON if needed."""
    json_path = PROJECT_ROOT / "seed_data" / "parking_entities.json"
    if not json_path.exists():
        return

    # Only run if DB is empty to avoid conflicts with rich init
    count = database.fetch_all("SELECT COUNT(*) as c FROM parking_entities")[0]["c"]
    if count > 0:
        return

    print("Migrating legacy parking entities...")
    try:
        data = json.loads(json_path.read_text())
        inserted = 0
        for item in data:
            entity_id = item.get("id")
            url = item.get("url")
            
            existing = database.fetch_all("SELECT id FROM parking_entities WHERE entity_id = %s", (entity_id,))
            if not existing:
                database.execute_query(
                    "INSERT INTO parking_entities (entity_id, url) VALUES (%s, %s)",
                    (entity_id, url)
                )
                inserted += 1
        print(f"Migrated {inserted} legacy parking entities.")
    except Exception as e:
        print(f"Error migrating parking: {e}")

def init_rich_parking():
    """Initialize rich parking zones if table is empty."""
    try:
        count = database.fetch_all("SELECT COUNT(*) as c FROM parking_entities")[0]["c"]
        if count > 0:
            print(f"Parking entities already populated ({count} rows). Skipping initialization.")
            return

        print("Initializing rich parking zones...")
        zones = parking_zones_init._default_zones()
        parking_zones_init.seed_parking_zones(zones)
        print("Rich parking zones initialized.")
    except Exception as e:
        print(f"Error initializing parking zones: {e}")

def migrate_roads():
    geojson_path = PROJECT_ROOT / "seed_data" / "patras_roads.geojson"
    if not geojson_path.exists():
        print("Roads GeoJSON file not found.")
        return

    # Check if already populated
    try:
        count = database.fetch_all("SELECT COUNT(*) as c FROM road_segments")[0]["c"]
        if count > 0:
            print(f"Road segments already populated ({count} rows). Skipping migration.")
            return
    except Exception as e:
        print(f"Error checking road segments: {e}")
        return

    print("Migrating road segments...")
    try:
        data = json.loads(geojson_path.read_text())
        batch_data = []
        BATCH_SIZE = 5000
        total_count = 0
        
        # No truncate needed as we checked count
        # database.execute_query("TRUNCATE TABLE road_segments") 

        for feature in data.get("features", []):
            geom = feature.get("geometry") or {}
            if geom.get("type") != "LineString":
                continue
            
            coords = geom.get("coordinates") or []
            if not coords:
                continue
                
            for i in range(len(coords) - 1):
                lng1, lat1 = coords[i]
                lng2, lat2 = coords[i + 1]
                
                # Skip zero-length segments
                if lat1 == lat2 and lng1 == lng2:
                    continue

                batch_data.append((lat1, lng1, lat2, lng2))
                
                # Execute batch when full
                if len(batch_data) >= BATCH_SIZE:
                    database.execute_batch(
                        "INSERT INTO road_segments (lat1, lng1, lat2, lng2) VALUES (%s, %s, %s, %s)",
                        batch_data
                    )
                    total_count += len(batch_data)
                    batch_data = [] # Reset list

        # Insert remaining items
        if batch_data:
            database.execute_batch(
                "INSERT INTO road_segments (lat1, lng1, lat2, lng2) VALUES (%s, %s, %s, %s)",
                batch_data
            )
            total_count += len(batch_data)
            
        print(f"Migrated {total_count} road segments.")
    except Exception as e:
        print(f"Error migrating roads: {e}")

if __name__ == "__main__":
    print("Starting database setup...")
    if wait_for_db():
        migrate_roads()
        init_rich_parking()
        # migrate_parking() # Legacy fallback
        print("Database setup complete.")
    else:
        print("Database setup failed: Could not connect to database.")
        sys.exit(1)
