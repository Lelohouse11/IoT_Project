import random
import json
import paho.mqtt.client as mqtt
import requests

# FIWARE Orion Context Broker details
orion_url = "http://150.140.186.118:1026/v2/entities"
fiware_service_path = "/week4_upxxxxxxx" # Replace with your FIWARE Service Path
entity_id = "test_noisemeter_upxxxxxxx"  # Entity ID in FIWARE where data will be updated
entity_type = "noisemeter"  # Entity Type

# MQTT broker details
broker = '150.140.186.118'
port = 1883
client_id = 'rand_id' + str(random.random())
topic = 'json/Environmental/dutch-sensor-systems-ranos-db-2:1'

def process_func(message):
    """Process the incoming message and extract noise data."""
    try:
        # Load the JSON message
        data = json.loads(message)
        
        # Extract noise from measurements
        measurements = data.get('object', {}).get('measurements', [])
        if measurements:
            # Assuming we are interested in the first measurement's LAeq as the noise value
            noise = measurements[0].get('LAeq')  # Modify if you need a different value
            if noise is not None:
                return round(float(noise), 2)
    except json.JSONDecodeError:
        print("Received message is not valid JSON.")
    except (IndexError, ValueError):
        print("Error extracting noise from measurements.")
    
    return None

def check_and_create_entity():
    """Check if the entity exists in FIWARE, and create it if it does not."""
    headers = {
        
        
        'Fiware-ServicePath': fiware_service_path
    }
    # Check if the entity exists
    response = requests.get(f"{orion_url}/{entity_id}", headers=headers)
    if response.status_code == 404:
        print(f"Entity {entity_id} not found. Creating entity...")
        # Define the payload to create the entity
        payload = {
            "id": entity_id,
            "type": entity_type,
            "noise": {
                "type": "Number",
                "value": 0
            }
        }
        # Send the creation request
        create_response = requests.post(orion_url, headers=headers, json=payload)
        if create_response.status_code == 201:
            print("Entity created successfully.")
        else:
            print(f"Failed to create entity: {create_response.status_code} - {create_response.text}")
    elif response.status_code == 200:
        print("Entity exists in FIWARE.")
    else:
        print(f"Error checking entity existence: {response.status_code} - {response.text}")

def send_to_fiware(noise):
    """Send noise data to FIWARE Orion Context Broker, checking entity existence each time."""
    headers = {
        'Content-Type': 'application/json',
        
        'Fiware-ServicePath': fiware_service_path
    }

    # Construct the payload to update the entity in FIWARE
    payload = {
        "noise": {
            "type": "Number",
            "value": noise
        }
    }

    # Check if the entity exists before trying to patch
    check_and_create_entity()

    # Make a PATCH request to update the entity's noise attribute
    url = f"{orion_url}/{entity_id}/attrs"
    response = requests.patch(url, headers=headers, json=payload)
    
    if response.status_code == 204:
        print(f"Successfully updated noise data in FIWARE: {noise}")
    else:
        print(f"Failed to send data to FIWARE: {response.status_code} - {response.text}")

def on_connect(client, userdata, flags, rc):
    """Callback function for when the client connects to the MQTT broker."""
    if rc == 0:
        print("Connected to MQTT broker successfully.")
        client.subscribe(topic)
        print(f"Subscribed to topic: {topic}")
    else:
        print(f"Failed to connect, return code {rc}")

def on_subscribe(client, userdata, mid, granted_qos):
    """Callback function for when the client subscribes to a topic."""
    print(f"Subscription successful with QoS {granted_qos}")

def on_disconnect(client, userdata, rc):
    """Callback function for handling disconnections."""
    if rc != 0:
        print("Unexpected disconnection from MQTT broker.")
    else:
        print("Disconnected from MQTT broker.")

def on_message(client, userdata, message):
    """Callback function for processing received messages."""
    print(f"Message received on topic {message.topic}: {message.payload.decode()}")
    noise = process_func(message.payload.decode())
    if noise is not None:
        send_to_fiware(noise)

def on_log(client, userdata, level, buf):
    """Callback function for logging MQTT client events."""
    pass
    #print(f"MQTT Log: {buf}")

def main():
    # Create an MQTT client instance
    mqtt_client = mqtt.Client(client_id=client_id)

    # Assign event callbacks for connection, disconnection, and message handling
    mqtt_client.on_connect = on_connect
    mqtt_client.on_disconnect = on_disconnect
    mqtt_client.on_message = on_message
    mqtt_client.on_subscribe = on_subscribe
    mqtt_client.on_log = on_log  # Enables detailed logging from the MQTT client


    # Connect to the MQTT broker
    print("Attempting to connect to MQTT broker...")
    mqtt_client.connect(broker, port)

    # Start the MQTT client loop
    mqtt_client.loop_forever()

if __name__ == "__main__":
    main()