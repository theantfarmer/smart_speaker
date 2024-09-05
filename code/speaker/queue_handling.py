# this module handles inter module queues and avoids circular errors

import queue
import threading
import multiprocessing
import time

user_input_queue = queue.Queue()
user_input_condition = threading.Condition()

llm_response_queue = queue.Queue()
llm_response_condition = threading.Condition()

tool_response_to_llm_claude_queue = queue.Queue()
tool_response_to_llm_claude_condition = threading.Condition()

send_to_tts_queue = queue.Queue()
send_to_tts_condition = threading.Condition()

# Queue for sending commands to Home Assistant
send_to_ha = queue.Queue()

# Notification event for TTS readiness
ready_to_speak = threading.Event()
