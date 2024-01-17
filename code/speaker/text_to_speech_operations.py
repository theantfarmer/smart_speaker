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
from home_assistant_interactions import is_home_assistant_available, home_assistant_request
from gtts_tts import gtts_tts
from tts_google_cloud import tts_google_cloud
from tts_piper import tts_piper

# Initialize logging
logging.basicConfig(level=logging.INFO)

# Initialize Pygame Mixer
pygame.mixer.init()

# Initialize mp3_queue as thread-safe
mp3_queue = Queue()

def is_mp3(audio_content):
    return audio_content[:2] == b'ID'

def talk_with_tts(text=None, command=None):
    print("Inside talk_with_tts function.")
    
    if text is None and command is None:
        mp3_queue.put((None, None))
        return
    
    if text is None and command is not None:
        mp3_queue.put((None, command))
        return

    if text and text.strip() != "":
        logging.info(f"Inside talk_with_tts with text: {text}, command: {command}")
        try:
            audio_content = tts_piper(text)  
        except Exception as e:
            logging.error(f"Error in tts service script: {e}")
            return

        file_extension = 'mp3' if is_mp3(audio_content) else 'wav'
        file_name = f'response_{uuid.uuid4().hex}.{file_extension}'
        audio_path = os.path.join(os.path.dirname(__file__), file_name)
        
        with open(audio_path, "wb") as out:
            out.write(audio_content)
        
        logging.info(f"Saved {file_extension.upper()} file to {audio_path}")
        
        mp3_queue.put((file_name, command))
    else:
        mp3_queue.put((None, command))

def load_and_play_audio(audio_file):
    script_dir = os.path.dirname(__file__)
    audio_path = os.path.join(script_dir, audio_file)
    
    if os.path.exists(audio_path):
        try:
            pygame.mixer.music.load(audio_path)
            pygame.mixer.music.play()
            logging.info(f"Playing audio file: {audio_path}")
            
            # Attempt to delete the audio file
            try:
                os.remove(audio_path)
                logging.info("Deleted audio file: %s", audio_path)
            except Exception as e:
                logging.error("Failed to delete audio file %s: %s", audio_path, e)
        except Exception as e:
            logging.error(f"Error playing audio file: {e}")
    else:
        logging.error(f"Audio file not found: {audio_path}")

def play_playlist():
    next_audio_preloaded = False

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

    while True:
        try:
            current_audio, command = mp3_queue.get(timeout=5)

            if current_audio:
                load_and_play_audio(current_audio)

            execute_command_async(command)

            if not next_audio_preloaded:
                try:
                    next_audio, _ = mp3_queue.get_nowait()
                    if next_audio:
                        pygame.mixer.music.queue(os.path.join(os.path.dirname(__file__), next_audio))
                        next_audio_preloaded = True
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
       
