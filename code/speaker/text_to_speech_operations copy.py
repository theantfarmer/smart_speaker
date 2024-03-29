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
import logging
from queue import Queue


# Initialize logging
logging.basicConfig(level=logging.INFO)

# Initialize Pygame Mixer
pygame.mixer.init()

# Initialize mp3_queue as thread-safe
mp3_queue = Queue()
credentials = service_account.Credentials.from_service_account_info(GOOGLE_CLOUD_CREDENTIALS)

def talk_with_tts(text=None, command=None):
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
            # Call the google_cloud_tts function
            audio_content = google_cloud_tts(text)
        except Exception as e:
            logging.error(f"Error in TTS generation: {e}")
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
    """
    Play the playlist of mp3 files and delete them after playing.
    """
    # script_dir = os.path.dirname(__file__)

    while True:
        try:
            print("Checking mp3_queue")
            queue_item = mp3_queue.get(timeout=5)  # 5 seconds timeout

            if queue_item is None:
                print("Received None queue item. Skipping.")
                continue

            mp3_file, command = (queue_item if len(queue_item) == 2 else (queue_item[0], None))

            if mp3_file is None and command is None:
                print("Both mp3_file and command are None. Skipping.")
                continue

            if mp3_file:
                mp3_path = os.path.join(script_dir, mp3_file)
                pygame.mixer.music.load(mp3_path)
                pygame.mixer.music.play()
                while pygame.mixer.music.get_busy():
                    time.sleep(1)

                pygame.mixer.music.stop()
                print("Before deletion check:", mp3_path)
                # Attempt to delete the MP3 file
                if os.path.exists(mp3_path):
                    print("Attempting to delete MP3 file: %s", mp3_path)
                    
                    try:
                        os.remove(mp3_path)
                        print("os.remove")
                        logging.info("Deleted MP3 file: %s", mp3_path)
                    except Exception as e:
                        print("deletion error"
                        logging.error("Failed to delete MP3 file %s: %s", mp3_path, e)
                else:
                    logging.warning(f"File not found for deletion: {mp3_path}")

            mp3_queue.task_done()

        except Empty:
            logging.info("Queue was empty.")
        except Exception as e:
            logging.error("Exception occurred: %s", e)




# Run play_playlist in a separate daemon thread
playlist_thread = threading.Thread(target=play_playlist)
playlist_thread.daemon = True
playlist_thread.start()



def handle_home_assistant_command(command):
    light_on_patterns = [r'\b(turn\s+on\s+the\s+light|turn\s+the\s+light\s+on|light\s+on)\b']
    light_off_patterns = [r'\b(turn\s+off\s+the\s+light|turn\s+the\s+light\s+off|light\s+off|dark)\b']

    try:
        command_dict = json.loads(command)
        if any(re.search(pattern, command_dict.get('command_text', ''), re.IGNORECASE) for pattern in light_on_patterns):
            response = home_assistant_request('services/light/turn_on', 'post', payload=command_dict)
            if response and response.status_code == 200:
                return True, "Successfully turned on the light."
            else:
                return False, f"Failed with status code {response.status_code}" if response else "No response received"

        elif any(re.search(pattern, command_dict.get('command_text', ''), re.IGNORECASE) for pattern in light_off_patterns):
            response = home_assistant_request('services/light/turn_off', 'post', payload={"entity_id": "light.your_light"})
            if response and response.status_code == 200:
                return True, "done"
            else:
                return False, f"Failed with status code {response.status_code}" if response else "No response received"
    except json.JSONDecodeError:
        print("Invalid JSON command.")
        return False, "Invalid JSON command."
