import threading
import subprocess
import socket
import atexit
import time
import json
import redis
import os
import re
from flask_cors import CORS
from flask_sse import sse
from flask import Flask, render_template, request, jsonify, send_from_directory, redirect, url_for, Response
from werkzeug.utils import secure_filename
from queue_handling import user_input_queue, user_input_condition
from db_operations import connect_db, initialize_db
from default_settings import DEFAULT_SETTINGS
from settings_manager import load_settings, save_settings, get_setting, update_setting
from file_operations import get_allowed_extensions, get_stored_files, delete_stored_file_by_id, store_file, init_sandbox, create_new_file

current_dir = os.path.dirname(os.path.abspath(__file__))
frontend_dir = os.path.join(os.path.dirname(current_dir), 'frontend')
static_folder = os.path.join(frontend_dir, 'build')
app = Flask(__name__, static_folder=static_folder)
CORS(app)

number_of_messages_to_display = 25 # this number stays static
current_message_display_count = number_of_messages_to_display # this number will be updated

web_server_thread = None
redis_process = None

UPLOAD_FOLDER = 'stored_files'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['ALLOWED_EXTENSIONS'] = get_allowed_extensions()
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def start_redis_server():
    global redis_process
    # Check if Redis is already running
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    result = sock.connect_ex(('localhost', 6379))
    sock.close()
    if result == 0:
        print("Redis server is already running")
        return True
    # If Redis is not running, start it
    print("Starting Redis server...")
    redis_process = subprocess.Popen(['redis-server'])
    # Wait for Redis to start
    start_time = time.time()
    while True:
        if time.time() - start_time > 5:  # 5 seconds timeout
            print("Failed to start Redis server")
            return False
        # Check if Redis is now running
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        result = sock.connect_ex(('localhost', 6379))
        sock.close()
        if result == 0:
            print("Redis server started successfully")
            return True
        time.sleep(0.1)
        
def start_web_server():
    global web_server_thread
    if web_server_thread is None or not web_server_thread.is_alive():
        with app.app_context():
            initialize_db()
            init_sandbox()
        web_server_thread = threading.Thread(target=app.run, kwargs={
            'debug': False,
            'host': '0.0.0.0',
            'port': 5000,
            'threaded': True
        })
        web_server_thread.start()

def initialize_sse():
    if start_redis_server():
        app.config["REDIS_URL"] = "redis://localhost:6379"
        if 'sse_blueprint' not in app.blueprints:
            app.register_blueprint(sse, url_prefix='/stream', name='sse_blueprint')
        else:
            print("SSE blueprint already registered")
    else:
        print("Failed to initialize SSE due to Redis server issues")

def build_react_app():
    try:
        # Adjust the path to run npm in the frontend directory
        subprocess.run(["npm", "run", "build"], cwd=frontend_dir, check=True)
        print("React app built successfully")
    except subprocess.CalledProcessError as e:
        print(f"Error building React app: {e}")
        
def fetch_messages():
    try:
        with connect_db() as conn:
            cursor = conn.cursor()
            query = """
                SELECT database_id, role, content, request_id, function_request, input_source, timestamp 
                FROM (
                    SELECT database_id, role, content, request_id, function_request, input_source, timestamp 
                    FROM history 
                    ORDER BY timestamp DESC 
                    LIMIT ?
                ) sub 
                ORDER BY timestamp ASC
            """
            # app.logger.info(f"Executing query: {query} with limit {current_message_display_count}")
            cursor.execute(query, (current_message_display_count,))
            messages = cursor.fetchall()
        # app.logger.info(f"Fetched {len(messages)} messages from database")

        formatted_messages = [
            {
                "database_id": msg[0],
                "role": msg[1],
                "content": msg[2],
                "request_id": msg[3],
                "function_request": msg[4],
                "input_source": msg[5],
                "timestamp": str(msg[6])
            } for msg in messages
        ]

        # app.logger.info(f"Publishing SSE event with {len(formatted_messages)} messages")
        event_data = json.dumps({"messages": formatted_messages})
        sse.publish({"messages": formatted_messages}, type='messages_update')

        return formatted_messages 
    except Exception as e:
        app.logger.error(f"An error occurred while fetching messages: {str(e)}")
        return []
    
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def shutdown():
    global redis_process
    print("Shutting down web server...")
    if redis_process:
        try:
            redis_process.terminate()
            redis_process.wait(timeout=5)  
        except Exception as e:
            print(f"Error shutting down Redis: {e}")
    print("Web server shutdown complete")

atexit.register(shutdown)

@app.route('/', methods=['GET', 'POST'])
def home():
    if request.method == 'POST':
        fetch_messages()  
        return jsonify({"status": "success"}), 200
    else:
        return send_from_directory(app.static_folder, 'index.html')

@app.route('/<path:path>')
def serve(path):
    if os.path.exists(app.static_folder + '/' + path):
        return send_from_directory(app.static_folder, path)
    else:
        return send_from_directory(app.static_folder, 'index.html')
    
# API route for fetching messages
@app.route('/api/messages', methods=['GET', 'POST'])
def handle_messages():
    if request.method == 'POST':
        fetch_messages()  
        return jsonify({"status": "success"}), 200
    else:
        messages = fetch_messages()
        return jsonify(messages)

@app.route('/scrolled_to_top', methods=['POST'])
def scrolled_to_top():
    global current_message_display_count
    # app.logger.info(f"Scrolled to top endpoint hit. Current count: {current_message_display_count}")
    current_message_display_count += number_of_messages_to_display
    fetch_messages()
    return jsonify({"status": "processed"}), 200

@app.route('/noticed_database_was_updated', methods=['POST'])
def noticed_database_was_updated():
    data = request.json
    if data.get('change_detected'):
        global current_message_display_count
        current_message_display_count += 1
        fetch_messages()
        return jsonify({"status": "processed"}), 200
    
@app.route('/query', methods=['POST'])
def query():
    user_input = request.json['input']
    with user_input_condition:
        user_input_queue.put((user_input, "web_interface"))
        user_input_condition.notify()
    return jsonify({'response': "Input processed"})

@app.route('/homepage')
def homepage():
    return render_template('home.html')

@app.route('/settings')
def settings():
    # Load the actual settings
    actual_settings = load_settings()
    # Pass both the structure and the actual settings to the template
    return render_template('settings.html', settings_structure=DEFAULT_SETTINGS, actual_settings=actual_settings)

@app.route('/api/settings', methods=['GET', 'POST'])
def handle_settings():
    if request.method == 'GET':
        # Return all settings
        all_settings = load_settings()
        return jsonify(all_settings)
    elif request.method == 'POST':
        setting_type = request.args.get('type')
        new_settings = request.json
        update_setting(setting_type, new_settings)
        return jsonify({"message": f"{setting_type.replace('_', ' ').capitalize()} updated successfully"}), 200

with app.app_context():
    init_sandbox()

@app.route('/file_management')
def file_management():
    files = get_stored_files()
    allowed_extensions = ','.join(f'.{ext}' for ext in app.config['ALLOWED_EXTENSIONS'])
    return render_template('file_management.html', files=files, allowed_extensions=allowed_extensions)

@app.route('/upload_file', methods=['POST'])
def upload_file():
    if 'files' not in request.files:
        return redirect(url_for('file_management'))
    
    files = request.files.getlist('files')
    
    if not files or files[0].filename == '':
        return redirect(url_for('file_management'))
    
    for file in files:
        success, message = store_file(file)
        if not success:
            return jsonify({'success': False, 'message': message}), 400
    
    return redirect(url_for('file_management'))

@app.route('/create_new_file', methods=['POST'])
def create_new_file():
    filename = request.form.get('filename')
    code_content = request.form.get('codeContent')
    if not filename or not code_content:
        return jsonify({'success': False, 'message': 'Filename and code content are required'}), 400
    
    success, message = create_new_file(filename, code_content)
    if success:
        return redirect(url_for('file_management'))
    return jsonify({'success': False, 'message': message}), 400

@app.route('/delete_stored_file/<file_id>', methods=['POST'])
def delete_file(file_id):
    success, message = delete_stored_file_by_id(file_id)
    return jsonify({'success': success, 'message': message})

@app.route('/stream')
def stream():
    def event_stream():
        yield "data: {\"test\":\"SSE Connection Test\"}\n\n"
        
        red = redis.Redis()
        pubsub = red.pubsub()
        pubsub.subscribe('sse')
        for message in pubsub.listen():
            if message['type'] == 'message':
                try:
                    data = json.loads(message['data'])
                    # app.logger.info(f"Sending SSE message: {str(data)[:200]}...")
                    yield f"data: {json.dumps(data)}\n\n"
                except json.JSONDecodeError:
                    app.logger.error(f"Failed to decode message: {message['data']}")

    return Response(event_stream(), content_type='text/event-stream')
        
initialize_sse()

def run_flask():
    app.run(debug=False, use_reloader=False, host='0.0.0.0', port=5000, threaded=True)

# Start Flask in a separate thread
flask_thread = threading.Thread(target=run_flask)
flask_thread.start()

# Function to build React app
build_react_app()
start_web_server()

print("Web server started. Access the app at http://localhost:5000")