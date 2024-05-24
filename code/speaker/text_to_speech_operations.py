import os
import re
import uuid
import time
import json
import string
import traceback
import re
import magic
import shlex
import emoji
from queue import Queue, Empty
import threading
import logging
import pygame.mixer
from home_assistant_interactions import is_home_assistant_available, home_assistant_request
from tts_google_cloud import tts_model
from multiprocessing import Value, Lock


# Initialize logging
logging.basicConfig(level=logging.INFO)

# Initialize Pygame Mixer
pygame.mixer.init()

# Initialize mp3_queue as thread-safe
mp3_queue = Queue()
playlist_event = threading.Event()

tts_outputs = {}  # Dictionary to store text and timestamps for echo cancellation
tts_is_speaking = Value('b', False) 
tts_lock = Lock()


def is_mp3(audio_content):
    return audio_content[:2] == b'ID'

def talk_with_tts(text=None, command=None):
    global tts_outputs
    print("Inside talk_with_tts function.")

    if text is None and command is None:
        mp3_queue.put((None, None))
        playlist_event.set()
        return

    if text is None and command is not None:
        mp3_queue.put((None, command))
        playlist_event.set()
        return

    if isinstance(text, tuple):
        print(f"text is a tuple: {text}")
        text, command = text
        print(f"After unpacking - text: {text}")
        print(f"After unpacking - command: {command}")

    if text is not None:
        print(f"Before demojize - text: {text}")
        print(f"Before demojize - type of text: {type(text)}")

        # Convert emojis to their text representation
        text = emoji.demojize(text)

        print(f"After demojize - text: {text}")
        print(f"After demojize - type of text: {type(text)}")
        text = text.replace('*', ' ')
        text = re.sub(r'http\S+', 'online', text)

        # Use json.dumps() to serialize the text into a JSON-formatted string
        json_text = json.dumps(text)

        # Use json.loads() to deserialize the JSON-formatted string back into a regular string
        deserialized_text = json.loads(json_text)

        try:
            audio_content = tts_model(deserialized_text)
        except Exception as e:
            logging.error(f"Error in tts service script: {e}")
            return

        # Check file format
        file_type = magic.from_buffer(audio_content, mime=True)
        print(f"File format: {file_type}")  # Print the file format to the terminal

        if file_type == 'audio/mpeg':
            file_extension = 'mp3'
        else:
            # Handle other formats or set a default
            file_extension = 'wav'

        file_name = f'response_{uuid.uuid4().hex}.{file_extension}'
        audio_path = os.path.join(os.path.dirname(__file__), file_name)

        with open(audio_path, "wb") as out:
            print(f"Audio file saved: {audio_path}")
            out.write(audio_content)
            logging.info(f"Saved {file_extension.upper()} file to {audio_path}")

        print(f"Adding to mp3_queue: {file_name}, {command}")
        mp3_queue.put((file_name, command))
        playlist_event.set()
    else:
        mp3_queue.put((None, command))
        playlist_event.set()

def load_and_play_audio(file_path):
    global tts_is_speaking
    try:
        pygame.mixer.music.load(file_path)
        if not pygame.mixer.music.get_busy():
            with tts_lock:
                tts_is_speaking.value = True
                print(f"[load_and_play_audio] Set tts_is_speaking to True before playing audio")
                
            pygame.mixer.music.play()
            print(f"Playing audio file: {file_path}")
        else:
            pygame.mixer.music.queue(file_path)
            print(f"Queued audio file: {file_path}")

        while pygame.mixer.music.get_busy():
            pygame.time.wait(100)  # Wait for 100 milliseconds

        try:
            os.remove(file_path)
            print(f"Deleted audio file: {file_path}")
        except Exception as e:
            print(f"Failed to delete audio file {file_path}: {e}")
    except Exception as e:
        print(f"Error playing audio file: {e}")

def play_playlist():
    global tts_is_speaking
    while True:
        try:
            print("[play_playlist] Waiting for playlist_event to be set...")
            playlist_event.wait()
            print("[play_playlist] playlist_event set, proceeding...")
            playlist_event.clear()

            print("[play_playlist] Entering while loop to check mp3_queue...")
            while not mp3_queue.empty():
                item = mp3_queue.get(timeout=5)
                file_name, command = item

                if file_name:
                    load_and_play_audio(file_name)

                    try:
                        next_file_name, _ = mp3_queue.get(block=False)
                        if next_file_name:
                            pygame.mixer.music.queue(next_file_name)
                    except Empty:
                        pass

                if command is not None:
                    handle_home_assistant_command(command)

                mp3_queue.task_done()

                if mp3_queue.empty() and not pygame.mixer.music.get_busy():
                    with tts_lock:
                        tts_is_speaking.value = False
                        print(f"[play_playlist] Set tts_is_speaking to False after processing all items from queue")

        except Empty:
            print("[play_playlist] Queue is empty")
            continue
        except Exception as e:
            print(f"Error in play_playlist: {e}")
            mp3_queue.task_done()


playlist_thread = threading.Thread(target=play_playlist)
playlist_thread.daemon = True
playlist_thread.start()

def handle_home_assistant_command(command):
    try:
        command_dict = json.loads(command)
        response = home_assistant_request('services/light/turn_on', 'post', payload=command_dict)
        logging.info(f"Light command executed: {command}, Response: {response}")
    except Exception as e:
        logging.error(f"Error executing light command: {e}")