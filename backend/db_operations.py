import sqlite3
import logging
import time 
import threading
import os
import requests
from flask_sse import sse
from flask import current_app

script_dir = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(script_dir, 'chat_history.db')

db_watcher_thread = None

def db_watcher():
    def watch_db():
        print("Database watcher started")
        last_mtime = os.path.getmtime(DB_PATH)
        last_database_id = 0  # To keep track of the last message we've sent

        while True:
            time.sleep(1)  # Check every second
            current_mtime = os.path.getmtime(DB_PATH)
            if current_mtime != last_mtime:
                print("Database update detected!")
                
                # Fetch the new messages
                with connect_db() as conn:
                    cursor = conn.cursor()
                    cursor.execute("SELECT database_id, role, content FROM history WHERE database_id > ? ORDER BY database_id ASC", (last_database_id,))
                    new_messages = cursor.fetchall()

                if new_messages:
                    last_database_id = new_messages[-1][0]  # Update last_id to the most recent message id
                    
                    # Notify server with the new messages
                    notify_server(True, new_messages)
                
                last_mtime = current_mtime

    global db_watcher_thread
    if db_watcher_thread is None:
        print("Starting database watcher thread")
        db_watcher_thread = threading.Thread(target=watch_db, daemon=True)
        db_watcher_thread.start()
    else:
        print("Database watcher thread already running")

def notify_server(change_detected, new_messages=None):
    try:
        data = {
            'change_detected': change_detected,
            'new_messages': new_messages
        }
        requests.post('http://localhost:5000/noticed_database_was_updated', json=data)
    except Exception as e:
        print(f"Failed to notify server: {e}")

def connect_db():
    return sqlite3.connect(DB_PATH)

def initialize_db():
    with connect_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS history (
                database_id INTEGER PRIMARY KEY AUTOINCREMENT,
                role TEXT,
                content TEXT,
                request_id TEXT,
                function_request TEXT,
                input_source TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()
    print("Database initialized, starting watcher")  
    db_watcher()

def save_to_db(role, content, full_request_id, streaming):
    print(f"contnet as delivered: {content}") 
    function_request = None
    input_source = None
    request_id = None 
    roles_that_do_not_save = ["system", "secret"]
    # Override role to 'tool' if 'tool' is in the request_id

    if full_request_id:
        if 'tool' in full_request_id.lower():
            role = 'tool'
        if 'system' in full_request_id.lower():
            role = 'system'
        if 'secret' in full_request_id.lower():
            role = 'secret'

    if isinstance(content, bool): #if the first item is a boolean, it indicates streaming
        if streaming:
            streaming = False
        content = None
        return True
    
    # Handle secret requests
    if role in roles_that_do_not_save:
        if input_source == "speech":
            print("Secret speech request detected. Discarding without saving.")
            return True
        elif input_source == "web_interface":
            print("Secret web interface request detected. Diversion logic to be implemented.")
            # TODO: Implement diversion logic for secret web interface requests
            return True
    
    print(f"contnet before saving block: {content}")    
    # If not secret, continue with normal processing
    if role not in roles_that_do_not_save:
        print(f"role is not in banned roles")
        if content is not None and content.strip() != "":
            with connect_db() as conn:
                print(f"connect with db")
                cursor = conn.cursor()      
                # This is a new entry
                # we unpack variables only for the first save
                matching_entry = None
                # if streaming is true, we must check the db
                # each time for a matching entry.  If there is none,
                # or if streaming is off, we create a new entry.  If
                # there is a match, we update it.  
                if full_request_id:
                    request_id = full_request_id
                    print(f"Full request breaker")
                    if '%' in full_request_id:
                        function_request, request_id = full_request_id.split('%', 1)
                    if '$' in request_id:
                        input_source, request_id = request_id.split('$', 1)
                    if streaming: 
                        cursor.execute("""
                            SELECT database_id, content
                            FROM history
                            WHERE request_id = ? AND role = ?
                            ORDER BY timestamp DESC
                            LIMIT 1
                        """, (request_id, role))
                        
                        matching_entry = cursor.fetchone()
                        if matching_entry:
                            matching_database_id, existing_content = matching_entry
                            print(f"Found matching entry with database_id: {matching_database_id}")
                            # Combine existing content with new content
                            updated_content = existing_content + content
                            # Update the existing entry in the database
                            cursor.execute("""
                                UPDATE history
                                SET content = ?
                                WHERE database_id = ?
                            """, (updated_content, matching_database_id))
                            print(f"Updated existing entry with database_id: {matching_database_id}")
                    if not matching_entry:
                        cursor.execute("""
                            INSERT INTO history (role, content, request_id, function_request, input_source)
                            VALUES (?, ?, ?, ?, ?)
                        """, (role, content, request_id, function_request, input_source))     
                        
                        
                        
                                              
    return True