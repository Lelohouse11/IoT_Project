
import os
import sys
from pathlib import Path
from influxdb_client import InfluxDBClient

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from api import config

client = InfluxDBClient(url=config.INFLUX_URL, token=config.INFLUX_TOKEN, org=config.INFLUX_ORG)
query_api = client.query_api()

def list_measurements():
    query = f'''
    import "influxdata/influxdb/schema"
    schema.measurements(bucket: "{config.INFLUX_BUCKET}")
    '''
    result = query_api.query(query)
    print("Measurements:")
    for table in result:
        for record in table.records:
            print(f" - {record.get_value()}")

def list_fields(measurement):
    query = f'''
    import "influxdata/influxdb/schema"
    schema.measurementFieldKeys(bucket: "{config.INFLUX_BUCKET}", measurement: "{measurement}")
    '''
    result = query_api.query(query)
    print(f"Fields in {measurement}:")
    for table in result:
        for record in table.records:
            print(f" - {record.get_value()}")

def list_buckets():
    buckets_api = client.buckets_api()
    buckets = buckets_api.find_buckets().buckets
    print("Buckets:")
    for bucket in buckets:
        print(f" - {bucket.name}")

def list_tag_keys(measurement):
    query = f'''
    import "influxdata/influxdb/schema"
    schema.measurementTagKeys(bucket: "{config.INFLUX_BUCKET}", measurement: "{measurement}")
    '''
    result = query_api.query(query)
    print(f"Tags in {measurement}:")
    for table in result:
        for record in table.records:
            print(f" - {record.get_value()}")

if __name__ == "__main__":
    try:
        list_fields("parking_zones")
        list_tag_keys("parking_zones")
    except Exception as e:
        print(f"Error: {e}")
