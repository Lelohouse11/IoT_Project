import paho.mqtt.client as mqtt_client
import random 

broker = '150.140.186.118'
port = 1883
client_id = 'rand_id' +str(random.random())
topic = "Group09_10"  # Specify the topic you'd like to subscribe to
# username = 'your_username'  # Optional: Use if your broker requires a username
# password = 'your_password'  # Optional: Use if your broker requires a password

def connect_mqtt():
    def on_connect(client, userdata, flags, rc):
        if rc == 0:
            print("Connected to MQTT Broker!")
        else:
            print(f"Failed to connect, return code {rc}\n")

    client = mqtt_client.Client(client_id)
    # client.username_pw_set(username, password)  # Uncomment if username/password is required
    client.on_connect = on_connect
    client.connect(broker, port)
    return client

def subscribe(client):
    def on_message(client, userdata, msg):
        print(f"Received `{msg.payload.decode()}` from `{msg.topic}` topic")

    client.subscribe(topic)
    client.on_message = on_message

def run():
    client = connect_mqtt()
    subscribe(client)
    client.loop_forever()  # Keep the client connected and listening for messages

if __name__ == '__main__':
    run()
