# gpt_operations.py
import openai
from dont_tell import OPENAI_API_KEY

openai.api_key = OPENAI_API_KEY

import os

def load_custom_instructions(file_path=None):
    
    if file_path is None:
        # Get the directory where the script is located
        dir_path = os.path.dirname(os.path.abspath(__file__))
        file_path = os.path.join(dir_path, 'custom_instructions.txt')

    with open(file_path, 'r') as f:
        return f.read().strip()

def talk_to_gpt(messages):
    custom_instructions = load_custom_instructions()
    messages.insert(0, {"role": "system", "content": custom_instructions})
    
    model_engine = "gpt-3.5-turbo"
    response = openai.ChatCompletion.create(
        model=model_engine, messages=messages, temperature=0.9
    )
    return response.choices[0].message['content'].strip()

def handle_conversation(messages):
    return talk_to_gpt(messages)
