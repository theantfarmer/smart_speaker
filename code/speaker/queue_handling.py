# this module handles inter module queues and avoids circular errors

import queue
import threading
import multiprocessing
import time

llm_response_queue = queue.Queue()
llm_response_condition = threading.Condition()

send_to_tts_queue = queue.Queue()
send_to_tts_condition = threading.Condition()

# Queue for sending commands to Home Assistant
send_to_ha = queue.Queue()

# Notification event for TTS readiness
ready_to_speak = threading.Event()
