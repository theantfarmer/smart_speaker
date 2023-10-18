#!/usr/bin/env python3

# Standard library imports
import os
import sqlite3
import subprocess
import sys
from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from concurrent.futures import ThreadPoolExecutor

# Constants
text_based_main_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'speaker', 'text_based_main.py')
db_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'speaker', 'gpt_chat_history.db'))

# Initialize Flask app and configurations
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
db = SQLAlchemy(app)
CORS(app, origins=["http://localhost:3000"])
executor = ThreadPoolExecutor(max_workers=2)

# Utility function to fetch chat history from the database
def fetch_chat_history_from_db():
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM history")
        rows = cursor.fetchall()
        return rows, 200
    except sqlite3.OperationalError as e:
        print(f"Operational error: {str(e)}")
        return {"error": "Operational error"}, 500
    except Exception as e:
        print(f"An error occurred: {str(e)}")
        return {"error": "An unexpected error occurred"}, 500
    finally:
        if 'conn' in locals():
            conn.close()

# API Endpoint to get chat history
@app.route("/api/chat-history", methods=["GET"])
def get_chat_history():
    future = executor.submit(fetch_chat_history_from_db)
    result, status_code = future.result()
    return jsonify(result), status_code

# API Endpoint to send new chat message
@app.route("/api/send-message", methods=["POST"])
def send_message():
    try:
        data = request.get_json()
        message_content = data.get('message', '')

        if not message_content:
            return jsonify({"status": "No message content provided"}), 400

        cmd = f'{sys.executable} speaker/text_based_main.py "{message_content}"'
        process = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = process.communicate()

        if process.returncode != 0:
            return jsonify({"status": "Message could not be sent"}), 500
        else:
            return jsonify({"status": "Message processed"}), 200

    except Exception as e:
        return jsonify({"status": "Message could not be sent"}), 500

# API Endpoint to get custom instructions
@app.route("/api/get-custom-instructions", methods=["GET"])
def get_custom_instructions():
    file_path = 'speaker/custom_instructions.txt'
    try:
        if not os.path.exists(file_path):
            with open(file_path, 'w') as f:
                f.write('')

        with open(file_path, 'r') as f:
            content = f.read()
        return jsonify({"instructions": content}), 200

    except Exception as e:
        return jsonify({"error": "Could not read or create file"}), 500

# API Endpoint to update custom instructions
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
