#!/usr/bin/env python3
# app.py

from flask import Flask, request, jsonify
from flask_cors import CORS # type: ignore


app = Flask(__name__)
CORS(app)

@app.route('/', methods=['POST'])
def handle_request():
    # Retrieve fields from POST form data
    command = request.form.get('command')
    code = request.form.get('code')

    # Print the received fields to the console
    print("Received command:", command)
    print("Received code:", code)

    # Respond to the client
    return "Fields printed to console.", 200

if __name__ == '__main__':
    # Run the Flask app on port 3440
    app.run(host='0.0.0.0', port=3440, debug=True)