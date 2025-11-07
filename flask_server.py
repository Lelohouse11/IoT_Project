from flask import Flask, request
from flask_cors import CORS
import json, sys

app = Flask("my server")
#CORS(app)  # This enables CORS for all routes


# POST method to handle JSON data
@app.route('/', methods=['POST'])
def receive_json():
    data = request.get_json()
    print("Received JSON data:", json.dumps(data, indent=4), file=sys.stderr)
    return "Received and processed JSON data\n"

# GET method to return a simple "Hello Student" response
@app.route('/', methods=['GET'])
def hello_student():
    return "Hello Student\n"

app.run(host='0.0.0.0', port=8080) #Host needs to change for local network exposure 
