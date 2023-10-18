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

def play_playlist():
    script_dir = os.path.dirname(__file__)
    while True:
        try:
            print("Checking mp3_queue")
            print("Before reading from mp3_queue")
            mp3_file, command = mp3_queue.get()
            print("After reading from mp3_queue")  

            # Handle the command
            if command:
                print(f"Executing command: {command}")
                if is_home_assistant_available():
                    response = home_assistant_request('your_endpoint_here', 'post', payload={'command': command})
                    print(f"Home Assistant response: {response}")
                else:
                    print("Home Assistant is not available.")

            # Handle the mp3_file
            if mp3_file:
                mp3_path = os.path.join(script_dir, mp3_file)
                pygame.mixer.music.load(mp3_path)
                pygame.mixer.music.play()
                while pygame.mixer.music.get_busy():
                    sleep(1)
                
                # Delete the MP3 file after playing
                os.remove(mp3_path)
                print(f"Deleted MP3 file: {mp3_path}")
            else:
                print("Received None or empty mp3_file. Skipping playback.")
            
            mp3_queue.task_done()
        except Empty:
            print("Queue was empty.")
        except Exception as e:
            print(f"Exception: {e}")
            
        # Clear the queue if needed
        with mp3_queue.mutex:
            mp3_queue.queue.clear()
        print("Cleared mp3_queue.")


# Run play_playlist in a separate daemon thread
playlist_thread = threading.Thread(target=play_playlist)
playlist_thread.daemon = True
playlist_thread.start()

def talk_with_tts(text=None, command=None, pitch=-2.0):
    print("Inside talk_with_tts function.") 
    # Both are None, enqueue (None, None)
    if text is None and command is None:
        mp3_queue.put((None, None))
        return
    
    # Solo command, pair with an empty string for text
    if text is None and command is not None:
        text = " "
    
    if text is None and command is None:
        mp3_queue.put((None, None))
        return

    if text:  # Process text only if it is not None or empty
        logging.info(f"Inside talk_with_tts with text: {text}, command: {command}")
     
        try:
        #     audio_content = google_cloud_tts(text, pitch, credentials)
        # except Exception as e:
        #     logging.error(f"Error in google_cloud_tts: {e}")
            audio_content = gtts_tts(text, pitch, credentials)
        except Exception as e:
            logging.error(f"Error in gtts_tts: {e}")
            return

        file_name = f'response_{uuid.uuid4().hex}.mp3'
        mp3_path = os.path.join(os.path.dirname(__file__), file_name)
        
        with open(mp3_path, "wb") as out:
            out.write(audio_content)

        
        logging.info(f"Saved MP3 file to {mp3_path}")
        mp3_queue.put((file_name, command))  # Pair the filename with the command and add it to the queue
        logging.info(f"Queue size after put: {mp3_queue.qsize()}")
    else:
        mp3_queue.put((None, command))  # If the text is None, add a None entry for the file name in the queue