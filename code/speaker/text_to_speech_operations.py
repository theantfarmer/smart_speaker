import os
import uuid
from time import sleep
import json
import traceback
import re
from queue import Queue, Empty
import threading
import logging
import pygame.mixer
from google.cloud import texttospeech
from google.oauth2 import service_account
from smart_home_parser import is_home_assistant_available, home_assistant_request
from dont_tell import GOOGLE_CLOUD_CREDENTIALS
from smart_home_parser import is_home_assistant_available, home_assistant_request
from gtts_tts import gtts_tts
from google_cloud_tts import google_cloud_tts


# Initialize logging
logging.basicConfig(level=logging.INFO)

# Initialize Pygame Mixer
pygame.mixer.init()

# Initialize mp3_queue as thread-safe
mp3_queue = Queue()
credentials = service_account.Credentials.from_service_account_info(GOOGLE_CLOUD_CREDENTIALS)

def talk_with_tts(text=None, command=None, pitch=0.0):
    print("Inside talk_with_tts function.")

    # If both text and command are None, enqueue (None, None)
    if text is None and command is None:
        mp3_queue.put((None, None))
        return
    
    # If there's no text but there is a command, don't create a placeholder text
    if text is None and command is not None:
        mp3_queue.put((None, command))
        return

    # Process text only if it is not None or empty
    if text and text.strip() != "":
        logging.info(f"Inside talk_with_tts with text: {text}, command: {command}")
        try:
            audio_content = google_cloud_tts(text, pitch, credentials)
        except Exception as e:
            logging.error(f"Error in google_cloud_tts: {e}")
        #     audio_content = gtts_tts(text, pitch, credentials)  # Replace with your TTS function
        # except Exception as e:
        #     logging.error(f"Error in gtts_tts: {e}")
            return

        file_name = f'response_{uuid.uuid4().hex}.mp3'
        mp3_path = os.path.join(os.path.dirname(__file__), file_name)
        
        with open(mp3_path, "wb") as out:
            out.write(audio_content)
        
        logging.info(f"Saved MP3 file to {mp3_path}")
        
        mp3_queue.put((file_name, command))

    else:
        # If the text is None or empty, add a None entry for the file name in the queue
        mp3_queue.put((None, command))

def play_playlist():
    script_dir = os.path.dirname(__file__)

    def execute_command(command):
        if command:
            success, response_message = handle_home_assistant_command(command)
            logging.info(f"Command execution result: {response_message}")

    def play_mp3(mp3_file):
        if mp3_file:
            mp3_path = os.path.join(script_dir, mp3_file)
            pygame.mixer.music.load(mp3_path)
            pygame.mixer.music.play()
            while pygame.mixer.music.get_busy():
                sleep(1)
            os.remove(mp3_path)
            logging.info(f"Deleted MP3 file: {mp3_path}")

    while True:
        try:
            queue_item = mp3_queue.get(timeout=5)

            if queue_item is None:
                continue

            mp3_file, command = queue_item

            # Create threads for command execution and MP3 playback
            command_thread = threading.Thread(target=execute_command, args=(command,))
            mp3_thread = threading.Thread(target=play_mp3, args=(mp3_file,))

            # Start both threads
            command_thread.start()
            mp3_thread.start()

            # Join MP3 thread to ensure it completes before moving to the next item
            # Command thread can complete independently
            mp3_thread.join()

            mp3_queue.task_done()

        except Empty:
            logging.info("Queue was empty.")
        except Exception as e:
            logging.error(f"Exception occurred: {e}")



# Run play_playlist in a separate daemon thread
playlist_thread = threading.Thread(target=play_playlist)
playlist_thread.daemon = True
playlist_thread.start()

def handle_home_assistant_command(command):
    try:
        command_dict = json.loads(command)
        response = home_assistant_request('services/light/turn_on', 'post', payload=command_dict)
        
        if response is None:
            return False, "No response received from Home Assistant."

        if isinstance(response, tuple) and len(response) == 2:
            return response
        else:
            return False, "Unexpected response format from Home Assistant."

    except json.JSONDecodeError as e:
        logging.error(f"Invalid JSON command: {e}")
        return False, "Invalid JSON command."
    except Exception as e:
        logging.error(f"Exception occurred in handle_home_assistant_command: {e}")
        return False, f"Exception occurred: {e}"
