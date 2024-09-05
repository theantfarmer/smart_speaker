import os
import uuid
import hashlib
from flask import current_app
from werkzeug.utils import secure_filename
import shutil

SANDBOX_DIR = 'sandbox'

def get_stored_files():
    files = []
    sandbox_path = os.path.join(current_app.config['UPLOAD_FOLDER'], SANDBOX_DIR)
    if os.path.exists(sandbox_path):
        for filename in os.listdir(sandbox_path):
            file_path = os.path.join(sandbox_path, filename)
            if os.path.isfile(file_path):
                file_id = str(uuid.uuid4())  # Generate a unique ID for each file
                files.append({
                    'id': file_id,
                    'filename': filename,
                    'path': file_path
                })
    return files

def delete_stored_file_by_id(file_id):
    files = get_stored_files()
    for file in files:
        if file['id'] == file_id:
            try:
                os.remove(file['path'])
                return True, "File successfully deleted"
            except OSError as e:
                return False, f"Error deleting file: {str(e)}"
    return False, "File not found"

def store_file(file):
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        file_hash = hashlib.sha256(file.read()).hexdigest()
        file.seek(0)  # Reset file pointer after reading
        
        sandbox_path = os.path.join(current_app.config['UPLOAD_FOLDER'], SANDBOX_DIR)
        os.makedirs(sandbox_path, exist_ok=True)
        
        file_path = os.path.join(sandbox_path, f"{file_hash}_{filename}")
        file.save(file_path)
        
        # Set less restrictive permissions (owner read/write, group read, others read)
        os.chmod(file_path, 0o644)
        
        return True, "File stored successfully"
    return False, "Invalid file type"

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in current_app.config['ALLOWED_EXTENSIONS']

def sandbox_cleanup():
    sandbox_path = os.path.join(current_app.config['UPLOAD_FOLDER'], SANDBOX_DIR)
    if os.path.exists(sandbox_path):
        shutil.rmtree(sandbox_path)
    os.makedirs(sandbox_path, exist_ok=True)
    # Set directory permissions to allow listing (owner all, group read/execute, others read/execute)
    os.chmod(sandbox_path, 0o755)

# Call this function when initializing the app
def init_sandbox():
    # Ensure the main stored_files directory exists
    stored_files_path = current_app.config['UPLOAD_FOLDER']
    os.makedirs(stored_files_path, exist_ok=True)
    # Set permissions for the stored_files directory
    os.chmod(stored_files_path, 0o755)
    # Then initialize the sandbox within it
    sandbox_cleanup()
    # You might want to restore necessary files here if needed