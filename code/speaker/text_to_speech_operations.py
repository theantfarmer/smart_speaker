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
    next_mp3_preloaded = False

    def execute_command_async(command):
        if command:
            threading.Thread(target=execute_command, args=(command,), daemon=True).start()

    def execute_command(command):
        try:
            command_dict = json.loads(command)
            response = home_assistant_request('services/light/turn_on', 'post', payload=command_dict)
            logging.info(f"Light command executed: {command}, Response: {response}")
        except Exception as e:
            logging.error(f"Error executing light command: {e}")

    def load_and_play_mp3(mp3_file):
        nonlocal next_mp3_preloaded
        mp3_path = os.path.join(script_dir, mp3_file)
        if os.path.exists(mp3_path):
            try:
                pygame.mixer.music.load(mp3_path)
                pygame.mixer.music.play()
                logging.info(f"Playing MP3: {mp3_path}")
                next_mp3_preloaded = False  # Reset the flag
            except Exception as e:
                logging.error(f"Error playing MP3 file: {e}")
        else:
            logging.error(f"MP3 file not found: {mp3_path}")

    while True:
        try:
            current_mp3, command = mp3_queue.get(timeout=5)

            # Play current MP3 first to avoid delays
            if current_mp3:
                load_and_play_mp3(current_mp3)

            # Execute associated light command asynchronously
            execute_command_async(command)

            # Preload next MP3 if not already preloaded
            if not next_mp3_preloaded:
                try:
                    next_mp3, _ = mp3_queue.get_nowait()
                    if next_mp3:
                        pygame.mixer.music.queue(os.path.join(script_dir, next_mp3))
                        next_mp3_preloaded = True
                except Empty:
                    pass

            while pygame.mixer.music.get_busy():
                sleep(0.1)

            mp3_queue.task_done()
        except Empty:
            continue
        except Exception as e:
            logging.error(f"Error in play_playlist: {e}")
            mp3_queue.task_done()

# Run play_playlist in a separate daemon thread
playlist_thread = threading.Thread(target=play_playlist)
playlist_thread.daemon = True
playlist_thread.start()


            
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
