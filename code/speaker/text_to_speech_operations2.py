import os
import uuid
from time import sleep
import json
from queue import Queue, Empty
import threading
import logging
import pygame.mixer
from google.cloud import texttospeech
from google.oauth2 import service_account
from smart_home_parser import is_home_assistant_available, home_assistant_request
from dont_tell import GOOGLE_CLOUD_CREDENTIALS

# Initialize logging
logging.basicConfig(level=logging.INFO)

# Initialize Pygame Mixer
pygame.mixer.init()

# Initialize mp3_queue as thread-safe
mp3_queue = Queue()
credentials = service_account.Credentials.from_service_account_info(GOOGLE_CLOUD_CREDENTIALS)

def play_playlist():
    while True:
        try:
            print("Checking mp3_queue...")
            print("Before reading from mp3_queue...")
            mp3_file, command = mp3_queue.get()
            print(f"After reading from mp3_queue: mp3_file={mp3_file}, command={command}")

            # Handle the command
            if command:
                print(f"Executing command: {command}")
                if is_home_assistant_available():
                    print("Home Assistant is available. Sending command...")
                    response = home_assistant_request('your_endpoint_here', 'post', payload={'command': command})
                    if response:
                        print(f"Home Assistant response: {response.json()}")  # Assuming the response is JSON
                    else:
                        print("No response from Home Assistant.")
                else:
                    print("Home Assistant is not available.")


            if mp3_file and not block_google:
                mp3_path = os.path.join(script_dir, mp3_file)
                pygame.mixer.music.load(mp3_path)
                pygame.mixer.music.play()
                while pygame.mixer.music.get_busy():
                    sleep(1)

                # Delete the MP3 file after playing
                os.remove(mp3_path)
                print(f"Deleted MP3 file: {mp3_path}")
            else:
                print("Skipping MP3 playback due to block_google flag.")
            print("Marking task as done in mp3_queue.")
            mp3_queue.task_done()

        except Empty:
            print("Queue was empty.")
        except Exception as e:
            print(f"Exception: {e}")

        # Clear the queue if needed
        with mp3_queue.mutex:
            print("Clearing mp3_queue...")
            mp3_queue.queue.clear()
        print("Cleared mp3_queue.")


print("Populating mp3_queue with test commands...")

# Populate mp3_queue with None for mp3_file and actual command for lighting
mp3_queue.put((None, '{"xy": [0.46, 0.49], "brightness": 254, "transition": 1.0}'))

# Debugging print statement
print("mp3_queue populated. Starting playlist_thread...")

# Start the playlist_thread
playlist_thread = threading.Thread(target=play_playlist)
playlist_thread.daemon = True
playlist_thread.start()

# Add a delay to keep the program running
import time
time.sleep(60)  # Keeps the program running for 60 seconds




# Debugging print statement
print("playlist_thread started.")





block_google = True

def talk_with_tts(text=None, command=None, pitch=-5.0):
    print("Inside talk_with_tts function.") 
    # Both are None, enqueue (None, None)
    if text is None and command is None:
        mp3_queue.put((None, None))
        return
    
    # Solo command, pair with an empty string for text
    if text is None and command is None:
        mp3_queue.put((None, None))
        return
    if text is None and command is not None:
        text = " "
    
    # Revised code to conditionally handle Google Cloud Service
    if not block_google and text:
        logging.info(f"Inside talk_with_tts with text: {text}, command: {command}")
        
        client = texttospeech.TextToSpeechClient(credentials=credentials)
        input_text = texttospeech.SynthesisInput(text=text)
        voice = texttospeech.VoiceSelectionParams(
            language_code='en-GB',
            name='en-GB-Standard-f',
        )
        audio_config = texttospeech.AudioConfig(
            audio_encoding=texttospeech.AudioEncoding.MP3,
            pitch=pitch
        )
        
        response = client.synthesize_speech(input=input_text, voice=voice, audio_config=audio_config)
        
        file_name = f'response_{uuid.uuid4().hex}.mp3'
        mp3_path = os.path.join(os.path.dirname(__file__), file_name)
        
        with open(mp3_path, "wb") as out:
            out.write(response.audio_content)
        
        logging.info(f"Saved MP3 file to {mp3_path}")
        mp3_queue.put((file_name, command))
        logging.info(f"Queue size after put: {mp3_queue.qsize()}")

    elif block_google and command:  # If block_google is True, still execute the command
        print(f"Executing command without Google Cloud: {command}")
        if is_home_assistant_available():
            response = home_assistant_request('your_endpoint_here', 'post', payload={'command': command})
            print(f"Home Assistant response: {response}")
        else:
            print("Home Assistant is not available.")
        mp3_queue.put((None, command))