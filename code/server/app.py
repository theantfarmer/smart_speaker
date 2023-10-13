#!/usr/bin/env python3

# Standard library imports
import os
import sqlite3
import subprocess
import sys
import os
import sqlite3
import subprocess
from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
import logging
import json
import traceback
from concurrent.futures import ThreadPoolExecutor

print(sys.executable)

text_based_main_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'speaker', 'text_based_main.py')


app = Flask(__name__)

db_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'speaker', 'gpt_chat_history.db'))
  
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
db = SQLAlchemy(app)
CORS(app, origins=["http://localhost:3000"])
executor = ThreadPoolExecutor(max_workers=2)

def fetch_chat_history_from_db():
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM history")
        rows = cursor.fetchall()
        return rows, 200
    except sqlite3.OperationalError as e:
        print("Operational error:", str(e))
        return {"error": "Operational error"}, 500
    except Exception as e:
        print("An error occurred:", str(e))
        return {"error": "An unexpected error occurred"}, 500
    finally:
        if 'conn' in locals():
            conn.close()

@app.route("/api/chat-history", methods=["GET"])
def get_chat_history():
    print("Debug: About to access DB")
    
    future = executor.submit(fetch_chat_history_from_db)
    result, status_code = future.result()

    print("Debug: Done accessing DB")
    return jsonify(result), status_code

#send new chat message
@app.route("/api/send-message", methods=["POST"])
def send_message():
    try:
        data = request.get_json()
        message_content = data.get('message', '')
        print(f"Debug: Received message content: {message_content}")

        if not message_content:
            return jsonify({"status": "No message content provided"}), 400

        cmd = f'{sys.executable} speaker/text_based_main.py "{message_content}"'
        process = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = process.communicate()

        print(f"Debug: Subprocess stdout: {stdout.decode()}")
        print(f"Debug: Subprocess stderr: {stderr.decode()}")

        if process.returncode != 0:
            print(f"Command failed with error: {stderr}")
            return jsonify({"status": "Message could not be sent"}), 500
        else:
            print(f"Command succeeded with output: {stdout}")
            return jsonify({"status": "Message processed"}), 200

    except Exception as e:
        print(f"An error occurred: {str(e)}")
        return jsonify({"status": "Message could not be sent"}), 500


        if process.returncode != 0:
            print(f"Command failed with error: {stderr}")
            return jsonify({"status": "Message could not be sent"}), 500
        else:
            print(f"Command succeeded with output: {stdout}")
            return jsonify({"status": "Message processed"}), 200

    except Exception as e:
        print(f"An error occurred: {str(e)}")
        return jsonify({"status": "Message could not be sent"}), 500

# Get custom instructions
@app.route("/api/get-custom-instructions", methods=["GET"])
def get_custom_instructions():
    file_path = 'speaker/custom_instructions.txt'  # Relative path to the file
    try:
        # Check if the file exists; if not, create it
        if not os.path.exists(file_path):
            with open(file_path, 'w') as f:
                f.write('')

        # Read the file contents
        with open(file_path, 'r') as f:
            content = f.read()
        return jsonify({"instructions": content}), 200
    except Exception as e:
        print("An exception occurred: ", e)
        return jsonify({"error": "Could not read or create file"}), 500

# Update custom instructions
@app.route("/api/update-custom-instructions", methods=["POST"])
def update_custom_instructions():
    try:
        data = request.get_json()
        new_content = data.get('instructions', '')
        with open('speaker/custom_instructions.txt', 'w') as f:
            f.write(new_content)
        return jsonify({"status": "Instructions updated"}), 200
    except Exception as e:
        return jsonify({"error": "Could not update file"}), 500


if __name__ == '__main__':
    app.run(port=5555, debug=True)
