from flask import Flask, request, jsonify
from flask_cors import CORS
import json
import os
import sys

app = Flask("my server")
CORS(app)  # This enables CORS for all routes

# Define the path for our local JSON database file
JSON_FILE = "storage.json"

# POST method to handle adding new JSON data
@app.route('/', methods=['POST'])
def add_json_data():
    new_data = request.get_json()
    if not new_data:
        return jsonify({"error": "No JSON data provided"}), 400
        
    print(f"Received new data: {new_data}", file=sys.stderr)
    
    # Read existing data
    current_data = []
    if os.path.exists(JSON_FILE):
        try:
            with open(JSON_FILE, 'r') as f:
                current_data = json.load(f)
                # Ensure data is a list, reset if not
                if not isinstance(current_data, list):
                    current_data = []
        except json.JSONDecodeError:
            current_data = [] # Treat corrupt file as empty
            
    # Append new data
    current_data.append(new_data)
    
    # Write all data back
    try:
        with open(JSON_FILE, 'w') as f:
            json.dump(current_data, f, indent=4)
    except IOError as e:
        print(f"Error writing to file: {e}", file=sys.stderr)
        return jsonify({"error": "Could not save data"}), 500
    
    return jsonify({"status": "success", "added_data": new_data}), 201

# GET method to return the whole JSON database
@app.route('/', methods=['GET'])
def get_all_data():
    print("GET request received, returning all data.", file=sys.stderr)
    
    if not os.path.exists(JSON_FILE):
        return jsonify([]) # Return empty list if no file
        
    try:
        with open(JSON_FILE, 'r') as f:
            data = json.load(f)
            # Ensure data is a list, return empty if not
            if not isinstance(data, list):
                return jsonify([])
            return jsonify(data)
    except (json.JSONDecodeError, FileNotFoundError):
        return jsonify([]) # Return empty list on error

if __name__ == '__main__':
    # Initialize the file with an empty list if it doesn't exist
    if not os.path.exists(JSON_FILE):
        try:
            with open(JSON_FILE, 'w') as f:
                json.dump([], f)
            print(f"Initialized empty database at {JSON_FILE}", file=sys.stderr)
        except IOError as e:
            print(f"Error initializing database: {e}", file=sys.stderr)
            
    app.run(host='0.0.0.0', port=8080)

