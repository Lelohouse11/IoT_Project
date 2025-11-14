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
from dataclasses import dataclass
from typing import Dict, Optional
from influxdb_client import InfluxDBClient, Point, WritePrecision

# Reuse the same InfluxDB configuration from sensor_faker.py
#from sensor_faker import influxdb_url, bucket, org, token

influxdb_url = "http://150.140.186.118:8086"
bucket = "LeandersDB"
org = "students"
token = "8fyeafMyUOuvA5sKqGO4YSRFJX5SjdLvbJKqE2jfQ3PFY9cWkeQxQgpiMXV4J_BAWqSzAnI2eckYOsbYQqICeA=="
# Measurement name for accidents (single measurement keeps queries simple)
measurement = "accidents"


@dataclass
class GeneratorConfig:
    center_lat: float = 38.2464
    center_lng: float = 21.7346
    max_offset_deg: float = 0.02
    interval_sec: float = 3.0
    prob_new: float = 0.6
    prob_update: float = 0.25
    prob_clear: float = 0.15


@dataclass
class Accident:
    lat: float
    lng: float
    severity: str
    desc: str

    def jitter_location(self, max_delta: float = 0.001) -> None:
        """Apply slight jitter to simulate refined coordinates."""
        self.lat += random.uniform(-max_delta, max_delta)
        self.lng += random.uniform(-max_delta, max_delta)

    def maybe_update_severity(self, probability: float = 0.2) -> None:
        """Occasionally update severity to mimic new reports."""
        if random.random() < probability:
            self.severity = random_severity()


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


def generate_accident_data(config: Optional[GeneratorConfig] = None):
    """Continuously emit fake accident events to InfluxDB.

    Coordinates are generated around a configurable center point (default: Patras).
    Three actions occur per tick with configurable probabilities: create, update, clear.

    Schema
    - Measurement: accidents
    - Tags:   type=accident, severity ∈ {minor, medium, major}
    - Fields: id (str), desc (str), lat (float), lng (float), event (str), status (str)
    - Time:   WritePrecision.NS
    """

    if config is None:
        config = GeneratorConfig()

    actions = ("create", "update", "clear")
    weights = (config.prob_new, config.prob_update, config.prob_clear)

    def next_action(active: Dict[str, Accident]) -> str:
        if not active:
            return "create"
        return random.choices(actions, weights=weights, k=1)[0]

    def rnd_coord():
        lat = config.center_lat + random.uniform(-config.max_offset_deg, config.max_offset_deg)
        lng = config.center_lng + random.uniform(-config.max_offset_deg, config.max_offset_deg)
        return lat, lng

    def write_event(aid: str, accident: Accident, event: str, status: str, now_ns: int):
        point = (
            Point(measurement)
            .tag("type", "accident")
            .tag("severity", accident.severity)
            .field("id", aid)
            .field("desc", accident.desc)
            .field("lat", float(accident.lat))
            .field("lng", float(accident.lng))
            .field("count", 1)
            .field("event", event)
            .field("status", status)
            .time(now_ns, WritePrecision.NS)
        )
        write_api.write(bucket=bucket, org=org, record=point)

    # Track active accidents in-memory by ID to simulate updates/clear actions
    active: Dict[str, Accident] = {}
    next_id = 1
    descriptions = [
        "Rear-end collision",
        "Multi-vehicle accident",
        "Blocked lane",
        "Minor fender bender",
        "Vehicle breakdown",
        "Debris on road",
    ]

    with InfluxDBClient(url=influxdb_url, token=token, org=org) as client:
        write_api = client.write_api()

        while True:
            action = next_action(active)
            now_ns = time.time_ns()

            if action == "create":
                # Create a new accident
                lat, lng = rnd_coord()
                severity = random_severity()
                desc = random.choice(descriptions)
                aid = f"A{next_id:05d}"
                next_id += 1
                accident = Accident(lat=lat, lng=lng, severity=severity, desc=desc)
                active[aid] = accident

                write_event(aid, accident, "create", "active", now_ns)
                print(f"[create] {aid} {severity} at ({lat:.5f}, {lng:.5f})")

            elif action == "update":
                # Update an existing accident (slight movement or severity change)
                aid, accident = random.choice(list(active.items()))
                accident.jitter_location()
                accident.maybe_update_severity()

                write_event(aid, accident, "update", "active", now_ns)
                print(f"[update] {aid} {accident.severity} at ({accident.lat:.5f}, {accident.lng:.5f})")

            else:
                # Clear an accident
                aid, accident = random.choice(list(active.items()))
                active.pop(aid)

                write_event(aid, accident, "clear", "cleared", now_ns)
                print(f"[clear]  {aid} cleared")

            time.sleep(config.interval_sec)


def main():
    """CLI wrapper for the accident faker with helpful defaults."""
    parser = argparse.ArgumentParser(description="Accident data faker (InfluxDB)")
    parser.add_argument("--center-lat", type=float, default=GeneratorConfig.center_lat, help="Center latitude")
    parser.add_argument("--center-lng", type=float, default=GeneratorConfig.center_lng, help="Center longitude")
    parser.add_argument("--offset", type=float, default=GeneratorConfig.max_offset_deg, help="Max random offset in degrees")
    parser.add_argument("--interval", type=float, default=GeneratorConfig.interval_sec, help="Interval between events (seconds)")
    parser.add_argument("--new", type=float, default=GeneratorConfig.prob_new, help="Probability of a new accident per tick")
    parser.add_argument("--update", type=float, default=GeneratorConfig.prob_update, help="Probability of an update per tick")
    parser.add_argument("--clear", type=float, default=GeneratorConfig.prob_clear, help="Probability of a clear per tick")
    args = parser.parse_args()

    config = GeneratorConfig(
        center_lat=args.center_lat,
        center_lng=args.center_lng,
        max_offset_deg=args.offset,
        interval_sec=args.interval,
        prob_new=args.new,
        prob_update=args.update,
        prob_clear=args.clear,
    )

    generate_accident_data(config)


if __name__ == "__main__":
    main()
