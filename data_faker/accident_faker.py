"""
Generate synthetic accident events and write them to InfluxDB.

This faker reuses the exact same InfluxDB connection settings as sensor_faker.py
so that both tools write into the same bucket/org. It simulates a simple event
life-cycle per accident ID:

  - create: new accident appears (status=active)
  - update: position and/or severity refined (status=active)
  - clear:  accident resolved (status=cleared)

Why this structure?
  - Grafana can easily count "create" events per time window for KPIs
  - The map can track latest state per ID and hide cleared items
"""

import time
import random
import argparse
from influxdb_client import InfluxDBClient, Point, WritePrecision

# Reuse the same InfluxDB configuration from sensor_faker.py
#from sensor_faker import influxdb_url, bucket, org, token

influxdb_url = "http://150.140.186.118:8086"
bucket = "LeandersDB"
org = "students"
token = "8fyeafMyUOuvA5sKqGO4YSRFJX5SjdLvbJKqE2jfQ3PFY9cWkeQxQgpiMXV4J_BAWqSzAnI2eckYOsbYQqICeA=="
# Measurement name for accidents (single measurement keeps queries simple)
measurement = "accidents"


def random_severity() -> str:
    """Return a severity with a simple weighted distribution.

    We slightly favor "minor" to avoid flooding the map with majors.
    """
    r = random.random()
    # Weighted distribution: minor (65%), medium (20%), major (15%)
    if r < 0.15:
        return "major"
    if r < 0.35:
        return "medium"
    return "minor"


def generate_accident_data(
    center_lat: float = 38.2464,
    center_lng: float = 21.7346,
    max_offset_deg: float = 0.02,
    interval_sec: float = 3.0,
    prob_new: float = 0.6,
    prob_update: float = 0.25,
    prob_clear: float = 0.15,
):
    """Continuously emit fake accident events to InfluxDB.

    Coordinates are generated around a configurable center point (default: Patras).
    Three actions occur per tick with configurable probabilities: create, update, clear.

    Schema
    - Measurement: accidents
    - Tags:   type=accident, severity ∈ {minor, medium, major}
    - Fields: id (str), desc (str), lat (float), lng (float), event (str), status (str)
    - Time:   WritePrecision.NS
    """

    # Create InfluxDB client
    client = InfluxDBClient(url=influxdb_url, token=token, org=org)
    write_api = client.write_api()

    # Track active accidents in-memory by ID to simulate updates/clear actions
    active = {}
    next_id = 1
    descriptions = [
        "Rear-end collision",
        "Multi-vehicle accident",
        "Blocked lane",
        "Minor fender bender",
        "Vehicle breakdown",
        "Debris on road",
    ]

    def rnd_coord():
        lat = center_lat + random.uniform(-max_offset_deg, max_offset_deg)
        lng = center_lng + random.uniform(-max_offset_deg, max_offset_deg)
        return lat, lng

    while True:
        # Normalize probabilities in case of rounding differences
        _sum = prob_new + prob_update + prob_clear
        p_new = prob_new / _sum
        p_update = prob_update / _sum
        # p_clear = 1 - (p_new + p_update)

        choice = random.random()
        now_ns = time.time_ns()

        if not active or choice < p_new:
            # Create a new accident
            lat, lng = rnd_coord()
            severity = random_severity()
            desc = random.choice(descriptions)
            aid = f"A{next_id:05d}"
            next_id += 1
            active[aid] = {"lat": lat, "lng": lng, "severity": severity, "desc": desc}

            point = (
                Point(measurement)
                .tag("type", "accident")
                .tag("severity", severity)
                .field("id", aid)
                .field("desc", desc)
                .field("lat", float(lat))
                .field("lng", float(lng))
                .field("count", 1)
                .field("event", "create")
                .field("status", "active")
                .time(now_ns, WritePrecision.NS)
            )
            write_api.write(bucket=bucket, org=org, record=point)
            print(f"[create] {aid} {severity} at ({lat:.5f}, {lng:.5f})")

        elif choice < (p_new + p_update) and active:
            # Update an existing accident (slight movement or severity change)
            aid = random.choice(list(active.keys()))
            rec = active[aid]

            # Slight jitter to simulate refined location updates
            rec["lat"] += random.uniform(-0.001, 0.001)
            rec["lng"] += random.uniform(-0.001, 0.001)

            # Occasionally update severity
            if random.random() < 0.2:
                rec["severity"] = random_severity()

            point = (
                Point(measurement)
                .tag("type", "accident")
                .tag("severity", rec["severity"])
                .field("id", aid)
                .field("desc", rec["desc"])
                .field("lat", float(rec["lat"]))
                .field("lng", float(rec["lng"]))
                .field("count", 1)
                .field("event", "update")
                .field("status", "active")
                .time(now_ns, WritePrecision.NS)
            )
            write_api.write(bucket=bucket, org=org, record=point)
            print(
                f"[update] {aid} {rec['severity']} at ({rec['lat']:.5f}, {rec['lng']:.5f})"
            )

        else:
            # Clear an accident
            aid = random.choice(list(active.keys()))
            rec = active.pop(aid)

            point = (
                Point(measurement)
                .tag("type", "accident")
                .tag("severity", rec["severity"])
                .field("id", aid)
                .field("desc", rec["desc"])
                .field("lat", float(rec["lat"]))
                .field("lng", float(rec["lng"]))
                .field("count", 1)
                .field("event", "clear")
                .field("status", "cleared")
                .time(now_ns, WritePrecision.NS)
            )
            write_api.write(bucket=bucket, org=org, record=point)
            print(f"[clear]  {aid} cleared")

        time.sleep(interval_sec)


def main():
    """CLI wrapper for the accident faker with helpful defaults."""
    parser = argparse.ArgumentParser(description="Accident data faker (InfluxDB)")
    parser.add_argument("--center-lat", type=float, default=38.2464, help="Center latitude")
    parser.add_argument("--center-lng", type=float, default=21.7346, help="Center longitude")
    parser.add_argument("--offset", type=float, default=0.02, help="Max random offset in degrees")
    parser.add_argument("--interval", type=float, default=3.0, help="Interval between events (seconds)")
    parser.add_argument("--new", type=float, default=0.6, help="Probability of a new accident per tick")
    parser.add_argument("--update", type=float, default=0.25, help="Probability of an update per tick")
    parser.add_argument("--clear", type=float, default=0.15, help="Probability of a clear per tick")
    args = parser.parse_args()

    generate_accident_data(
        center_lat=args.center_lat,
        center_lng=args.center_lng,
        max_offset_deg=args.offset,
        interval_sec=args.interval,
        prob_new=args.new,
        prob_update=args.update,
        prob_clear=args.clear,
    )


if __name__ == "__main__":
    main()
