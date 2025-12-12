import os

# InfluxDB Settings
INFLUX_URL = os.getenv("INFLUX_URL", "http://150.140.186.118:8086")
INFLUX_BUCKET = os.getenv("INFLUX_BUCKET", "LeandersDB")
INFLUX_ORG = os.getenv("INFLUX_ORG", "students")
INFLUX_TOKEN = os.getenv("INFLUX_TOKEN", "8fyeafMyUOuvA5sKqGO4YSRFJX5SjdLvbJKqE2jfQ3PFY9cWkeQxQgpiMXV4J_BAWqSzAnI2eckYOsbYQqICeA==")

# MQTT Settings
MQTT_BROKER = os.getenv("MQTT_BROKER", "150.140.186.118")
MQTT_PORT = int(os.getenv("MQTT_PORT", "1883"))
MQTT_TOPIC = os.getenv("MQTT_TOPIC", "orion_updates")

# Orion Settings
ORION_URL = os.getenv("ORION_URL", "http://150.140.186.118:1026")
FIWARE_SERVICE = os.getenv("FIWARE_SERVICE", "default")
FIWARE_SERVICE_PATH = os.getenv("FIWARE_SERVICE_PATH", "/week4_up1125093")
SUBSCRIPTION_CALLBACK_URL = os.getenv("SUBSCRIPTION_CALLBACK_URL", "http://localhost:8080/orion")

# LLM Settings
LLM_MODEL = os.getenv("MODEL", "deepseek-r1:8b")
LLM_UPSTREAM_URL = os.getenv("LLM_UPSTREAM_URL", "http://labserver.sense-campus.gr:7080/chat")
LLM_API_KEY = os.getenv("LLM_API_KEY", "studentpassword")
LLM_BIND_HOST = os.getenv("LLM_BIND_HOST", "0.0.0.0")
LLM_BIND_PORT = int(os.getenv("LLM_BIND_PORT", "9090"))

# Measurements
MEASUREMENT_ACCIDENTS = "accidents"
MEASUREMENT_PARKING = "parking_zones"
MEASUREMENT_TRAFFIC = "traffic_flow"
MEASUREMENT_VIOLATIONS = "traffic_violations"

# MySQL Settings
MYSQL_HOST = os.getenv("MYSQL_HOST", "localhost")
MYSQL_PORT = int(os.getenv("MYSQL_PORT", "3306"))
MYSQL_USER = os.getenv("MYSQL_USER", "iot_user")
MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD", "iot_password")
MYSQL_DB = os.getenv("MYSQL_DB", "iot_city_db")

