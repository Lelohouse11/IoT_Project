import time
import random
from influxdb_client import InfluxDBClient, Point, WritePrecision

# Define connection details
influxdb_url = "http://150.140.186.118:8086"
bucket = "LeandersDB"
org = "students"
token = "8fyeafMyUOuvA5sKqGO4YSRFJX5SjdLvbJKqE2jfQ3PFY9cWkeQxQgpiMXV4J_BAWqSzAnI2eckYOsbYQqICeA=="
measurement = "sensor_data"

# Create InfluxDB client
client = InfluxDBClient(url=influxdb_url, token=token, org=org)
write_api = client.write_api()  # No need to pass WritePrecision here

def generate_sensor_data():
    while True:
        # Generate random temperature value
        temperature = round(random.uniform(20.0, 30.0), 2)

        # Create a data point
        point = Point(measurement).tag("sensor", "temperature").field("value", temperature).time(time.time_ns(), WritePrecision.NS)

        # Write the point to the database
        write_api.write(bucket=bucket, org=org, record=point)
        print(f"Written temperature data: {temperature}°C")

        # Sleep for 2 seconds before generating the next point
        time.sleep(2)

if __name__ == "__main__":
    generate_sensor_data()
