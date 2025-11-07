from flask import Flask, request
from flask_cors import CORS

app = Flask("my server")
CORS(app)  # This enables CORS for all routes

# GET method to return a response based on the 'student' query parameter
@app.route('/', methods=['GET'])
def hello_student():
    # Retrieve the 'student' parameter from the query string
    student_type = request.args.get('academic_status')

    print(student_type)
    
    # Check the value of 'student' parameter and respond accordingly
    if student_type == "teacher":
        return "Hello Teacher\n"
    elif student_type == "student":
        return "Hello Student\n"
    else:
        return "Unrecognized\n"

app.run(host='0.0.0.0', port=8080)  # Host changed for local network exposure
