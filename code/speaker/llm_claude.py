import anthropic
import re
import json
import requests
import logging
import time
from dont_tell import CLAUDE_KEY
import db_operations
import expressive_light

logging.basicConfig(level=logging.INFO)

def llm_model(command_text_stripped, max_retries=10, retry_interval=10, timeout=60):
    client = anthropic.Anthropic(
        api_key=CLAUDE_KEY
    )

    messages = [{"content": f"{anthropic.HUMAN_PROMPT} {command_text_stripped} {anthropic.AI_PROMPT}"}]

    response = client.messages.create(
        model="claude-v1",
        max_tokens=2048,
        temperature=0,
        messages=messages,
    )

    response_text = response.content.strip()
    print("Raw response text format:", repr(response_text))

    return response_text