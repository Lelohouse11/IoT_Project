import paho.mqtt.client as mqtt_client
import random

broker = '150.140.186.118'
port = 1883
client_id = 'rand_id' +str(random.random())
topic = "Environmental/barani-meteohelix-iot-pro:1"  # Specify the topic you'd like to publish to
# username = 'your_username'  # Optional: Use if your broker requires a username
# password = 'your_password'  # Optional: Use if your broker requires a password
message="Hello World"




def run():
    def on_connect(client, userdata, flags, rc):
        if rc == 0:
            print("Connected to MQTT Broker!")
        else:
            print(f"Failed to connect, return code {rc}\n")

    client = mqtt_client.Client(client_id)
    # client.username_pw_set(username, password)  # Uncomment if username/password is required
    client.on_connect = on_connect
    client.connect(broker, port)
    
    client.publish(topic, message)
    client.disconnect()

if __name__ == '__main__':
    run()
