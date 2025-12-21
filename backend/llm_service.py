"""Flask server acting as a proxy to the LLM, enriching prompts with city data."""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
from debug import print_context  # noqa: F401

import requests
from flask import Flask, jsonify, request
from flask_cors import CORS
from influxdb_client import InfluxDBClient

from backend import config


def get_city_stats(start_time, end_time, bounds=None):
    """Query InfluxDB for stats within time range and optional map bounds."""
    client = InfluxDBClient(url=config.INFLUX_URL, token=config.INFLUX_TOKEN, org=config.INFLUX_ORG)
    query_api = client.query_api()
    
    # Helper to add geo filter if bounds exist
    geo_filter = ""
    if bounds:
        # bounds: {north, south, east, west}
        geo_filter = f'|> filter(fn: (r) => r["lat"] >= {bounds["south"]} and r["lat"] <= {bounds["north"]} and r["lng"] >= {bounds["west"]} and r["lng"] <= {bounds["east"]})'

    stats = {}

    # 1. Traffic Flow
    # Use user-provided Flux query logic
    q_traffic = f'''
    from(bucket: "{config.INFLUX_BUCKET}")
      |> range(start: {start_time}, stop: {end_time})
      |> filter(fn: (r) => r["_measurement"] == "{config.MEASUREMENT_TRAFFIC}")
      |> filter(fn: (r) => r["_field"] == "intensity" or r["_field"] == "avg_speed" or r["_field"] == "lat" or r["_field"] == "lng")
      |> pivot(rowKey:["_time"], columnKey: ["_field"], valueColumn: "_value")
      {geo_filter}
      |> group()
      |> reduce(
          identity: {{count_speed: 0.0, sum_speed: 0.0, count_intensity: 0.0, sum_intensity: 0.0}},
          fn: (r, accumulator) => ({{
            count_speed: accumulator.count_speed + (if exists r.avg_speed then 1.0 else 0.0),
            sum_speed: accumulator.sum_speed + (if exists r.avg_speed then float(v: r.avg_speed) else 0.0),
            count_intensity: accumulator.count_intensity + (if exists r.intensity then 1.0 else 0.0),
            sum_intensity: accumulator.sum_intensity + (if exists r.intensity then float(v: r.intensity) else 0.0)
          }})
      )
    '''
    try:
        tables = query_api.query(q_traffic)
        if tables and tables[0].records:
            rec = tables[0].records[0]
            
            # Use separate counts to avoid skewing averages if fields are missing in some rows
            count_speed = rec["count_speed"]
            count_intensity = rec["count_intensity"]
            
            stats["avg_speed"] = (rec["sum_speed"] / count_speed) if count_speed > 0 else 0
            stats["avg_intensity"] = (rec["sum_intensity"] / count_intensity) if count_intensity > 0 else 0
        else:
            stats["avg_speed"] = 0
            stats["avg_intensity"] = 0
    except Exception as e:
        print(f"Error querying traffic: {e}")
        stats["avg_speed"] = 0
        stats["avg_intensity"] = 0
    
    # Congestion count is not directly available in the new query structure, 
    # but we can infer or just set to N/A if not critical, or run a separate query if needed.
    # For now, removing it or setting to 0 as it wasn't in the user's "correct" query.
    stats["congestion_count"] = 0

    # 2. Accidents
    # Keeping existing logic but ensuring field names match if necessary. 
    # User didn't provide specific accident query correction, but mentioned "metrics/ data is collected wrong".
    # Assuming accidents logic was okay or user didn't complain about it specifically besides the count being high.
    # But wait, user said "A total accident count of 354 is alarmingly high".
    # Maybe I should check if I'm counting correctly.
    # The previous query was counting "id". If there are multiple updates for the same accident, 
    # counting all records would be wrong. I should probably count UNIQUE ids.
    
    q_accidents = f'''
    from(bucket: "{config.INFLUX_BUCKET}")
      |> range(start: {start_time}, stop: {end_time})
      |> filter(fn: (r) => r["_measurement"] == "{config.MEASUREMENT_ACCIDENTS}")
      |> pivot(rowKey:["_time"], columnKey: ["_field"], valueColumn: "_value")
      {geo_filter}
      |> group(columns: ["id"])
      |> unique(column: "id")
      |> group()
      |> count(column: "id")
    '''
    
    try:
        # Total accidents
        tables = query_api.query(q_accidents)
        stats["total_accidents"] = tables[0].records[0]["id"] if (tables and tables[0].records) else 0
        
        # Major accidents query - similar unique logic
        q_major = f'''
        from(bucket: "{config.INFLUX_BUCKET}")
          |> range(start: {start_time}, stop: {end_time})
          |> filter(fn: (r) => r["_measurement"] == "{config.MEASUREMENT_ACCIDENTS}")
          |> pivot(rowKey:["_time"], columnKey: ["_field"], valueColumn: "_value")
          {geo_filter}
          |> filter(fn: (r) => r["severity"] == "major")
          |> group(columns: ["id"])
          |> unique(column: "id")
          |> group()
          |> count(column: "id")
        '''
        tables_major = query_api.query(q_major)
        stats["major_accidents"] = tables_major[0].records[0]["id"] if (tables_major and tables_major[0].records) else 0
    except Exception as e:
        print(f"Error querying accidents: {e}")
        stats["total_accidents"] = 0
        stats["major_accidents"] = 0

    # 3. Parking
    # User provided query: filter by available_spots, occupied_spots, lat, lng.
    # We want a list of zones.
    q_parking = f'''
    from(bucket: "{config.INFLUX_BUCKET}")
      |> range(start: {start_time}, stop: {end_time})
      |> filter(fn: (r) => r["_measurement"] == "{config.MEASUREMENT_PARKING}")
      |> filter(fn: (r) => r["_field"] == "available_spots" or r["_field"] == "occupied_spots" or r["_field"] == "lat" or r["_field"] == "lng" or r["_field"] == "entity_id")
      |> pivot(rowKey:["_time"], columnKey: ["_field"], valueColumn: "_value")
      {geo_filter}
      |> group(columns: ["entity_id"])
      |> sort(columns: ["_time"], desc: true)
      |> limit(n: 1)
    '''
    
    parking_zones = []
    total_occupancy = 0
    zone_count = 0

    try:
        tables = query_api.query(q_parking)
        for table in tables:
            for record in table.records:
                # FluxRecord behaves like a dict but .get() might not be available on the object itself depending on version
                # Accessing via record["field"] is safer or record.values.get()
                eid = record.values.get("entity_id", "Unknown")
                name = eid.split(":")[-1] if ":" in eid else eid
                
                occupied = float(record.values.get("occupied_spots", 0))
                available = float(record.values.get("available_spots", 0))
                total = occupied + available
                
                occ_pct = (occupied / total * 100) if total > 0 else 0
                
                parking_zones.append(f"{name} ({int(available)} spots available, {int(occupied)} occupied)")
                
                total_occupancy += occ_pct
                zone_count += 1
        
        stats["parking_list"] = parking_zones
        stats["avg_occupancy"] = (total_occupancy / zone_count) if zone_count > 0 else 0.0

    except Exception as e:
        print(f"Error querying parking: {e}")
        stats["parking_list"] = []
        stats["avg_occupancy"] = 0.0

    # 4. Violations
    # User provided query: filter lat, lng, entity_id. Group by violation. Count entity_id.
    q_violations = f'''
    from(bucket: "{config.INFLUX_BUCKET}")
      |> range(start: {start_time}, stop: {end_time})
      |> filter(fn: (r) => r["_measurement"] == "{config.MEASUREMENT_VIOLATIONS}")
      |> filter(fn: (r) => r["_field"] == "lat" or r["_field"] == "lng" or r["_field"] == "entity_id")
      |> pivot(rowKey:["_time"], columnKey: ["_field"], valueColumn: "_value")
      {geo_filter}
      |> group(columns: ["violation"])
      |> count(column: "entity_id")
      |> rename(columns: {{entity_id: "_value"}}) 
    '''
    try:
        tables = query_api.query(q_violations)
        total_violations = 0
        top_violation = "None"
        max_count = 0
        
        for table in tables:
            if table.records:
                # Each table is a violation group
                rec = table.records[0]
                count = rec.get_value() # Since we renamed to _value
                violation_type = rec.values.get("violation", "Unknown")
                
                total_violations += count
                if count > max_count:
                    max_count = count
                    top_violation = violation_type
        
        stats["total_violations"] = total_violations
        stats["top_violation_type"] = top_violation
            
    except Exception as e:
        print(f"Error querying violations: {e}")
        stats["total_violations"] = 0
        stats["top_violation_type"] = "None"

    client.close()
    return stats


def create_app():
    app = Flask("llm-proxy")
    CORS(app)

    @app.route('/api/llm/analyze', methods=['POST'])
    def llm_analyze():
        try:
            data = request.get_json(force=True, silent=False) or {}
        except Exception:
            return jsonify({"error": "Invalid JSON body"}), 400

        start_time = data.get('startTime', '-1h')
        end_time = data.get('endTime', 'now()')
        bounds = data.get('bounds') # Expected {north, south, east, west} or None

        # Gather stats
        stats = get_city_stats(start_time, end_time, bounds)

        # Construct Prompt
        parking_details = "\n".join([f"  - {z}" for z in stats.get('parking_list', [])])
        
        prompt = f"""
You are a City Data Analyst for a university smart city project. Analyze the sensor data below for the selected city sector.
Time Range: {start_time} to {end_time}

[METRICS]
- Traffic Flow:
  - Average Speed: {stats.get('avg_speed', 0):.1f} km/h
  - Intensity: {stats.get('avg_intensity', 0):.1f} vehicles/hour

- Safety & Incidents:
  - Total Accidents: {stats.get('total_accidents', 0)} (Major: {stats.get('major_accidents', 0)})
  - Traffic Violations: {stats.get('total_violations', 0)}
  - Most Common Violation: {stats.get('top_violation_type', 'None')}

- Parking:
  - Average Occupancy: {stats.get('avg_occupancy', 0):.1f}%
  - Zones Details:
{parking_details}

[INSTRUCTIONS]
Provide a concise report with the following structure:

1. **Current State Overview**:
   - **Accidents**: [One short sentence summary]
   - **Traffic Flow**: [One short sentence summary]
   - **Traffic Violations**: [One short sentence summary]
   - **Parking Zones**: [One short sentence summary]

2. **Improvement Suggestions**:
   - Provide practical, low-cost suggestions to improve the situation (e.g., adjusting traffic light timing, changing parking fees, adding signage).
   - Do NOT suggest buying more sensors or changing how data is measured.
   - Keep in mind this is a university project demonstrating theoretical viability.
"""

        # Send to LLM
        model = config.LLM_MODEL
        upstream = config.LLM_UPSTREAM_URL
        api_key = config.LLM_API_KEY
        headers = {
            "Content-Type": "application/json",
            "X-API-Key": api_key,
        }
        payload = {"prompt": prompt, "model": model}

        try:
            resp = requests.post(upstream, headers=headers, json=payload, timeout=120) # Longer timeout for analysis
        except requests.RequestException as e:
            return jsonify({"error": f"upstream network error: {e}"}), 502

        text = resp.text
        try:
            body = resp.json()
        except ValueError:
            body = {"raw": text}

        if resp.status_code >= 400:
            return jsonify({"error": body.get('error') or body.get('message') or body}), resp.status_code

        output = body.get('output') or body.get('text') or body.get('answer') or text
        return jsonify({"output": output, "model": model, "stats": stats})

    @app.route('/api/llm/chat', methods=['POST'])
    def llm_chat():
        try:
            data = request.get_json(force=True, silent=False) or {}
        except Exception:
            return jsonify({"error": "Invalid JSON body"}), 400

        prompt = (data.get('prompt') or '').strip()
        model = config.LLM_MODEL
        if not prompt:
            return jsonify({"error": "Missing prompt"}), 400

        upstream = config.LLM_UPSTREAM_URL
        api_key = config.LLM_API_KEY

        headers = {
            "Content-Type": "application/json",
            "X-API-Key": api_key,
            }
       

        payload = {"prompt": prompt, "model": model}

        try:
            resp = requests.post(upstream, headers=headers, json=payload, timeout=60)
        except requests.RequestException as e:
            return jsonify({"error": f"upstream network error: {e}"}), 502

        text = resp.text
        try:
            body = resp.json()
        except ValueError:
            body = {"raw": text}

        if resp.status_code >= 400:
            return jsonify({"error": body.get('error') or body.get('message') or body}), resp.status_code

        output = body.get('output') or body.get('text') or body.get('answer') or text
        return jsonify({"output": output, "model": model})

    return app


if __name__ == '__main__':
    # Configure host/port via env if desired
    host = config.LLM_BIND_HOST
    port = config.LLM_BIND_PORT
    create_app().run(host=host, port=port)

