import os
import uuid
from time import sleep
import json
from queue import Queue, Empty
import threading
import logging
from time import sleep
import pygame.mixer
from google.cloud import texttospeech
from google.oauth2 import service_account
from smart_home_parser import is_home_assistant_available, home_assistant_request
from dont_tell import GOOGLE_CLOUD_CREDENTIALS

# Initialize logging
logging.basicConfig(level=logging.INFO)

# Initialize Pygame Mixer and Google Cloud TTS client
pygame.mixer.init()
if not pygame.mixer.get_init():
    print("Pygame Mixer not initialized")
credentials = service_account.Credentials.from_service_account_info(GOOGLE_CLOUD_CREDENTIALS)
mp3_queue = Queue()

import uuid
from queue import Queue, Empty
from time import sleep

mp3_queue = Queue()

def talk_with_tts(text, command=None):
    print(f"INSIDE TTS Entered talk_with_tts with command: {command} and text: {text}")
    # rest of the function

    print(f"Inside talk_with_tts with text: {text}, command: {command}")  # Debug log
    print(f"mp3_queue before putting item: {list(mp3_queue.queue)}")
    file_name = f'response_{uuid.uuid4().hex}.mp3'
    print(f"Generated unique filename: {file_name}")
    mp3_queue.put((file_name, command or None))  # Always put a tuple
    print(f"Successfully put {file_name} and {command or None} into mp3_queue")
    print(f"mp3_queue after putting item: {list(mp3_queue.queue)}")

    # Loop to check the queue (from the play_queue function)
    while True:
        try:
            print(f"Queue before get: {list(mp3_queue.queue)}")
            sleep(1)  # Add a sleep to slow the loop down
            mp3_file, command = mp3_queue.get(True, 10)
            print(f"Received mp3_file: {mp3_file}, command: {command} from mp3_queue")
            print(f"Queue after get: {list(mp3_queue.queue)}")
        except Empty:
            print("Queue was empty.")


    
    
# def talk_with_tts(text, command=None, pitch=-2.0):
#     print(f"Inside talk_with_tts with text: {text}, command: {command}")  # Debug log
  
#     client = texttospeech.TextToSpeechClient(credentials=credentials)
#     input_text = texttospeech.SynthesisInput(text=text)
#     voice = texttospeech.VoiceSelectionParams(
#         language_code='en-GB',
#         name='en-GB-Standard-f',
#     )
#     audio_config = texttospeech.AudioConfig(
#         audio_encoding=texttospeech.AudioEncoding.MP3,
#         pitch=pitch
#     )
#     response = client.synthesize_speech(input=input_text, voice=voice, audio_config=audio_config)
#     file_name = f'response_{hash(text)}.mp3'
#     with open(file_name, 'wb') as out:
#         out.write(response.audio_content)
#     print(f"MP3 File saved at: {file_name}")  # Add this line
#     print(f"TTS will speak: {text}")
#     print(f"Putting {file_name} and {command} into mp3_queue")  
#     mp3_queue.put((file_name, command or None))  # Always put a tuple
#     print(f"Successfully put {file_name} and {command or None} into mp3_queue")      
#     print(f"mp3_queue after putting item: {list(mp3_queue.queue)}")



# def play_queue():
#     global mp3_queue  # Access the global mp3_queue
#     while True:
#         try:
#             print(f"Queue before get: {list(mp3_queue.queue)}")
#             mp3_file, command = mp3_queue.get(True, 10)
#             print(f"Received mp3_file: {mp3_file}, command: {command} from mp3_queue")
#             print(f"Queue after get: {list(mp3_queue.queue)}")

        
#             if mp3_file:  # Only proceed if mp3_file is not None
#                 print(f"About to play mp3 file: {mp3_file}")  # Debug log
#                 pygame.mixer.music.load(mp3_file)

#             if os.path.exists(mp3_file):
#                 print(f"{mp3_file} exists.")
#             else:
#                 print(f"{mp3_file} does not exist.")
                
#         except Empty:
#             print("Queue was empty.")

            
#             if os.path.exists(mp3_file):
#                 print(f"{mp3_file} exists.")
#             else:
#                 print(f"{mp3_file} does not exist.")

#             if mp3_file is None:
#                 print("Received a None mp3_file. Skipping TTS.")

#             if command is None:
#                 print("Received a None command. Skipping command processing.")
#             else:
#                 print(f"Received a command: {command}. Execute it here.")
#             if command:
#                 print("Command exists, about to execute it.")
#                 try:
#                     endpoint = "/services/light/turn_on"
#                     method = "post"
#                     payload = json.loads(command)
#                     payload['entity_id'] = "light.school_show"
#                     if is_home_assistant_available():
#                         response = home_assistant_request('services/light/turn_on', 'post', payload={"entity_id": "light.school_show"})
#                         print(f"Home Assistant response: {response.json()}") 
#                         if response and response.status_code == 200:
#                             print("Successfully sent command to Home Assistant")
#                         else:
#                             print(f"Failed to send command to Home Assistant: {response}")
#                     else:
#                         print("Home Assistant is not available.")
#                 except Exception as e:
#                     logging.error(f"Failed to send command to Home Assistant: {e}")

#         except Empty:
#             print("Queue was empty.")
#             continue
#         except Exception as e:
#             print(f"An unexpected error occurred: {e}")
#             import traceback
#             traceback.print_exc()


#         try:
#             if mp3_file:  # Only proceed if mp3_file is not None
#                 pygame.mixer.music.load(mp3_file)
#                 pygame.mixer.music.play()
#                 while pygame.mixer.music.get_busy():
#                     sleep(0.1)
#                 os.remove(mp3_file)
#         except Exception as e:
#             print(f"Failed to play MP3: {e}")
            
# if __name__ == "__main__":
#     play_thread = threading.Thread(target=play_queue, args=(mp3_queue,))
#     play_thread.start()
#     print(f"Is play_thread alive?: {play_thread.is_alive()}")
