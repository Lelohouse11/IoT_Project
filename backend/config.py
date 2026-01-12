"""Configuration module loading environment variables for the entire backend."""

import os

# InfluxDB Settings
# URL of the InfluxDB instance
INFLUX_URL = os.getenv("INFLUX_URL", "http://150.140.186.118:8086")
# Target bucket for storing time-series data
INFLUX_BUCKET = os.getenv("INFLUX_BUCKET", "LeandersDB")
# Organization name in InfluxDB
INFLUX_ORG = os.getenv("INFLUX_ORG", "students")
# Authentication token for InfluxDB
INFLUX_TOKEN = os.getenv("INFLUX_TOKEN", "8fyeafMyUOuvA5sKqGO4YSRFJX5SjdLvbJKqE2jfQ3PFY9cWkeQxQgpiMXV4J_BAWqSzAnI2eckYOsbYQqICeA==")

# Orion Settings
# Base URL for the Orion Context Broker
ORION_URL = os.getenv("ORION_URL", "http://orion:1026")
# FIWARE Service header (tenant)
FIWARE_SERVICE = os.getenv("FIWARE_SERVICE", "default")
# FIWARE Service Path header (scope)
FIWARE_SERVICE_PATH = os.getenv("FIWARE_SERVICE_PATH", "/")
# Callback URL for Orion subscription notifications
ORION_CALLBACK_URL = os.getenv("ORION_CALLBACK_URL", "http://backend:8001")
# Port for the Orion bridge service
BRIDGE_BIND_HOST = os.getenv("BRIDGE_BIND_HOST", "0.0.0.0")
BRIDGE_BIND_PORT = int(os.getenv("BRIDGE_BIND_PORT", "8001"))

# Auth Settings
# Secret key for signing JWT tokens
SECRET_KEY = os.getenv("SECRET_KEY", "supersecretkey123")
# Algorithm used for JWT signing
ALGORITHM = "HS256"
# Token expiration time in minutes
ACCESS_TOKEN_EXPIRE_MINUTES = 30
# List of emails allowed to register
WHITELISTED_EMAILS = [
    "admin@smartcity.com",
    "leander@smartcity.com",
    "test@test.com",
    "lelohouse11@gmail.com"
]

# LLM Settings
LLM_API_URL = os.getenv("LLM_API_URL", "http://localhost:5001/ask")
LLM_MODEL = os.getenv("MODEL", "mistral:7b-instruct-q4_K_M")
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

