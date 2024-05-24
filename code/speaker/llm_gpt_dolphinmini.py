import openai
import ollama
import re
import json
import requests
import logging
import time
import subprocess
import threading  # Import threading module
from dont_tell import OPENAI_API_KEY
import db_operations 
import expressive_light

MODEL_NAME = "gpt_dolphinmini"

def is_model_running(model_name=MODEL_NAME):
    try:
        result = subprocess.run(["pgrep", "-f", model_name], capture_output=True, text=True)
        return result.returncode == 0
    except Exception as e:
        print(f"Error: {e}")
        return False

def start_model(model_name=MODEL_NAME):
    try:
        subprocess.run(["ollama", "run", model_name], capture_output=True)
        print(f"{model_name} model started.")
        time.sleep(30)
    except Exception as e:
        print(f"Error: {e}")

def initialize_ollama_model(model=MODEL_NAME):
    if not is_model_running(model):
        print(f"Model {model} is not running. Starting now...")
        start_model(model)
    else:
        print(f"Model {model} is already running. No need to restart.")

def start_ollama_in_background(model=MODEL_NAME):
    # Define a thread to run model initialization in the background
    thread = threading.Thread(target=initialize_ollama_model, args=(model,))
    thread.start()
    print(f"Starting {model} initialization in background.")

# Call to start the model initialization in background when module loads
start_ollama_in_background()

def llm_model(command_text_stripped, model=MODEL_NAME, timeout=60):
    formatted_message = [{"role": "user", "content": command_text_stripped}]
    try:
        response = ollama.chat(model=model, messages=formatted_message)
        message_content = response.get('message', {}).get('content', '')
        print(f"raw llm output: {message_content}")
        if message_content:
            if isinstance(message_content, (list, tuple)):
                message_content = message_content[0] if message_content else ''
            formatted_content = json.dumps(message_content, ensure_ascii=False) if not isinstance(message_content, str) else message_content
            print("Tagged Content:", formatted_content)
            return formatted_content
        else:
            print("No content found in the response.")
            return ""
    except requests.RequestException as e:
        logging.error(f"Request failed: {e}")
        time.sleep(retry_interval)
        return "Failed to get a response from Ollama API"
