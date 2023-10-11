#!/usr/bin/env python3
#this works
# Standard library imports
import os
import sqlite3
import subprocess


import os
import sqlite3
import subprocess
from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
import logging
import json

text_based_main_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'speaker', 'text_based_main.py')


app = Flask(__name__)

db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'speaker', 'gpt_chat_history.db')  
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
db = SQLAlchemy(app)
CORS(app, origins=["http://localhost:3000"])


@app.route("/api/chat-history", methods=["GET"])
def get_chat_history():
    print("Debug: About to access DB")  # Add this line
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM history")
        rows = cursor.fetchall()
    except sqlite3.OperationalError as e:
        print("Debug: Done accessing DB with error")  # Add this line
        print("Operational error:", str(e))
        return jsonify({"error": "Operational error"}), 500  # Internal Server Error
    except Exception as e:  # Catch-all for other exceptions
        print("Debug: Done accessing DB with error")  # Add this line
        print("An error occurred:", str(e))
        return jsonify({"error": "An unexpected error occurred"}), 500
    finally:
        if 'conn' in locals():  
            conn.close()
    print("Debug: Done accessing DB")  # Add this line
    return jsonify(rows), 200




@app.route("/api/send-message", methods=["POST"])
def send_message():
    try:
        data = request.get_json()
        message_content = data.get('message', '')
       
        if not message_content:
            return jsonify({"status": "No message content provided"}), 400

        command = ['python3', text_based_main_path, message_content]
        print(f"Executing command: {command}")  # Log the command being executed

        process = subprocess.run(command, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        if process.returncode != 0:  # Add this line
            print(f"Subprocess failed with return code {process.returncode}")  # And this line

            print(f'Subprocess stdout: {process.stdout}')
            print(f'Subprocess stderr: {process.stderr}')

        return jsonify({"status": "Message processed"}), 200  # Just acknowledging that the message was processed

    except Exception as e:
        print(f"An error occurred: {str(e)}")
        return jsonify({"status": "Message could not be sent"}), 500

if __name__ == '__main__':
    app.run(port=5555, debug=True)
