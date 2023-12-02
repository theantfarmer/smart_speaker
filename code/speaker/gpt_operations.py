# gpt_operations.py

import openai
import re
import json
import requests
import logging
import time
from dont_tell import OPENAI_API_KEY
import db_operations 
import expressive_light

# Ensure logging is configured at the beginning of your script
logging.basicConfig(level=logging.INFO)

def talk_to_gpt(messages, assistant_id="asst_BPTPmSLF9eaaqyCkVZVCmK07", model=None, max_retries=10, retry_interval=10, timeout=60):
    # API endpoint for creating and running a thread in one request
    api_endpoint = "https://api.openai.com/v1/threads/runs"

    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "Content-Type": "application/json",
        "OpenAI-Beta": "assistants=v1"
    }

    # Construct the data object for thread creation and running
    data = {
        "assistant_id": assistant_id,
        "thread": {
            "messages": messages
        }
    }

    if model:
        data["thread"]["model"] = model

    # Making the API request to create and run the thread
    response = requests.post(api_endpoint, headers=headers, data=json.dumps(data))
    response_data = response.json()
    logging.info("Raw API Response: %s", response.text)

    if response_data.get('status') == 'queued':
        thread_id = response_data['thread_id']
        run_id = response_data['id']

        start_time = time.time()
        while time.time() - start_time < timeout:
            step_url = f"https://api.openai.com/v1/threads/{thread_id}/runs/{run_id}/steps"
            step_response = requests.get(step_url, headers=headers)
            steps_data = step_response.json()
            logging.info(f"Steps Data: {steps_data}")

            for step in steps_data.get('data', []):
                step_status = step.get('status')
                if step_status == 'completed':
                    response_text = process_step_data(step, thread_id, headers)
                    return response_text
                elif step_status in ['failed', 'cancelled', 'expired']:
                    return "Run step ended with status: " + step_status

            time.sleep(retry_interval)

        return "Request timed out."
    else:
        return "Initial response status not queued."


def list_run_steps(thread_id, run_id):
    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "Content-Type": "application/json",
        "OpenAI-Beta": "assistants=v1"
    }
    response = requests.get(f"https://api.openai.com/v1/threads/{thread_id}/runs/{run_id}/steps", headers=headers)
    steps_data = response.json()
    logging.info(f"Steps Data for Run ID {run_id}: {steps_data}")

    # Extract step IDs, even if the step status is not 'completed'
    step_ids = [step['id'] for step in steps_data.get('data', [])]
    return step_ids

def process_step_data(step_data, thread_id, headers):
    """
    Process the step data to extract and retrieve the GPT model's response.
    """
    if 'step_details' in step_data and 'message_creation' in step_data['step_details']:
        message_id = step_data['step_details']['message_creation']['message_id']

        # API endpoint to retrieve the message
        message_url = f"https://api.openai.com/v1/threads/{thread_id}/messages/{message_id}"

        # Make the API call to retrieve the message content
        message_response = requests.get(message_url, headers=headers)
        message_data = message_response.json()

        # Extracting the message content
        if 'content' in message_data and len(message_data['content']) > 0:
            message_content = message_data['content'][0]['text']['value']
            return message_content
        else:
            return "Message content not found."
    else:
        return "No message content found in step data."


def handle_conversation(messages):
    gpt_response = talk_to_gpt(messages)
    print(f"Received GPT response: {gpt_response}")

    if '@[' in gpt_response and ']@' in gpt_response:
        print("Lighting commands found. Parsing and sending to expressive_light.")
        command_text_list = expressive_light.create_command_text_list(gpt_response)
        for command, text in command_text_list:
            print(f"Sending command: {command} to lighting control.")
        
        stripped_response = re.sub(r'@\[.*?\]@', '', gpt_response)
        print(f"Stripped Response: {stripped_response}")
        db_operations.save_to_db('Agent', stripped_response)

        return command_text_list, None  # return the command_text_list and a None for the text

    else:
        db_operations.save_to_db('Agent', gpt_response)
        return None, gpt_response  # return a None for the command_text_list and the text
