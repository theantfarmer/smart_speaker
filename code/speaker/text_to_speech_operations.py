import os
import re
import time
import json
import re
import magic
import emoji
from queue import Queue
import threading
import logging
import wave
import io
import uuid
import tempfile
import mimetypes
import numpy as np
import vlc
import soundfile as sf
from home_assistant_interactions import home_assistant_request
from tts_google_cloud import tts_model
from multiprocessing import Value, Lock
from queue_handling import send_to_tts_queue, send_to_tts_condition
from shared_variables import user_response_window, most_recent_wake_word, user_response_en_route, tts_is_speaking, tts_lock, tts_is_speaking_notification


# Initialize tts_playlist_queue as thread-safe
tts_playlist_queue = Queue()
tts_playlist_notify = threading.Event()

tts_outputs = {}  # Dictionary to store text and timestamps for echo cancellation



# individual_audio_is_playing turns true at the beginning of each indavidual audio file
# it turns false at the end of that file
# which triggers the next loop iteration and the next file to play
# In otherwords, it turns false bewteen each file
# while tts_is_speaking remains true accross playback of a series of files

individual_audio_is_playing = Value('b', False)
individual_audio_finished_notification = threading.Event()

vlc_instance = vlc.Instance()
player = vlc_instance.media_player_new()
playback_finished = threading.Event()

def talk_with_tts():
    while True:
        
        command = None
        text = None
        
        # Wait for and retrieve an item from the queue
        with send_to_tts_condition:
            while send_to_tts_queue.empty():
                send_to_tts_condition.wait()
            
            speech_data = send_to_tts_queue.get()

        print(f"talk_with_tts received: {speech_data}")
    
        # tuples should contain (command, text) and must be broken apart
        # text can be a None, a populated string, or an empty string

        try:
            if isinstance(speech_data, str):
                text = speech_data
            elif isinstance(speech_data, tuple):
                if len(speech_data) == 2:
                    command, text = speech_data
                elif len(speech_data) == 1 and isinstance(speech_data[0], tuple):
                    command, text = speech_data[0]
                else:
                    raise ValueError("Invalid tuple format. Expected (command, text) or ((command, text)).")
            else:
                raise ValueError("Invalid input type. Expected string or tuple.")
        except ValueError as e:
            print(f"Error in talk_with_tts: {str(e)}")
        
        # if text is a string, we attempt to remove characters
        # that TTS can't read or are unpleasant to listen to
        # if the string arrives empty or becomes empty after
        # it is cleaned, we set it to None
            
        if text is not None:
            try:
                # Convert emojis to their text representation
                text = emoji.demojize(text)
                # Remove HTML tags
                text = re.sub(r'<[^>]*>', '', text)
                # Remove line break characters
                text = text.replace('\n', ' ').replace('\r', '')
                text = text.replace('*', ' ')
                text = re.sub(r'http\S+', 'online', text)
            except Exception as e:
                print(" ")
            
            # empty string check!
            if not text.strip():
                print("Text is empty after processing, setting to None")
                text = None
            else:
                # if we make it to this point, the string contains
                # clean text ready to be read aloud
                # we send the text to the TTS model to
                # be converted to audio

                try:
                    print(f"Passing text to TTS model: {text}")
                    audio_content = tts_model(text)
                    print(f"Generated audio content. Length: {len(audio_content)} bytes")
              
                    # because we can easily swap models, we need to determine
                    # and handle whatever audio format the model returns.  
                    
                    file_type = magic.from_buffer(audio_content, mime=True)
                    print(f"File format: {file_type}")

                    # currently, we save the tts return as a file and pass the address
                    file_extension = mimetypes.guess_extension(file_type)
                    if file_extension:
                        file_name = str(uuid.uuid4()) + file_extension
                    else:
                        file_name = str(uuid.uuid4()) + "text_to_speech.wav"
                    tmp_filepath = os.path.join("/tmp", file_name)
                    with open(tmp_filepath, "wb") as f:
                        f.write(audio_content)

                    print(f"Audio content saved to file: {tmp_filepath}")
                    
                    # we still use the text variable because
                    # that is what we pass to the next queue
                    text = tmp_filepath
                    
                except Exception as e:
                    logging.error(f"Error in tts service script: {e}")
                    # Add error placeholder to maintain order
                    continue  # Move to the next item in the queue

        # finally, we put the text in the playlist queue
        # as a tuple, even if there is no command.
        # in that case, the command will be None
        print(f"Added to tts_playlist_queue: {command}, {text}")
        tts_playlist_queue.put((command, text))
        tts_playlist_notify.set()

def set_response_window():
    # we set the user response window to true for a few
    # seconds after TTS finishes.  If the useer begins
    # speaking during that window, en_route becomes True
    # in the speech to tech module.  If it does not become
    # true, the most_recent_wake_word, set in main, must be
    # reset
    window_duration = 10  # seconds
    check_interval = 0.1  # seconds

    with user_response_window.get_lock():
        user_response_window.value = True
    print("User response window opened")

    for _ in range(int(window_duration / check_interval)):
        time.sleep(check_interval)
        with user_response_en_route.get_lock():
            if user_response_en_route.value:
                print("User response detected, ending response window")
                break
    
    with user_response_window.get_lock():
        user_response_window.value = False
    print("User response window closed")

    with user_response_en_route.get_lock():
        if not user_response_en_route.value:
            with most_recent_wake_word.get_lock():
                most_recent_wake_word.value = b' ' * 150 
            print("No user response detected, most recent wake word cleared")
        else:
            print("user_response_en_route is True, keeping most recent wake word")

            
# play_audio is called later by iterate_playlist
# the play list of tuples must be iterated
# before calling play_audio

def playback_finished_callback(event):
    playback_finished.set()

event_manager = player.event_manager()
event_manager.event_attach(vlc.EventType.MediaPlayerEndReached, playback_finished_callback)

def play_audio(audio_file):
    global individual_audio_is_playing
    
    try:
        with individual_audio_is_playing.get_lock():
            individual_audio_is_playing.value = True
        
        print(f"Starting playback of {audio_file}")
        media = vlc_instance.media_new_path(audio_file)
        player.set_media(media)
        player.play()
        
        # Wait for playback to finish or timeout after 30 seconds
        playback_finished.wait(timeout=30)
        playback_finished.clear()
        
        if player.get_state() == vlc.State.Ended:
            print(f"Playback of {audio_file} completed")
        else:
            print(f"Playback of {audio_file} did not complete normally")
    except Exception as e:
        print(f"Error during audio playback: {str(e)}")
    finally:
        with individual_audio_is_playing.get_lock():
            individual_audio_is_playing.value = False
        individual_audio_finished_notification.set()
        
        player.stop()
        
        try:
            os.unlink(audio_file)
            print(f"Temporary file {audio_file} deleted.")
        except Exception as e:
            print(f"Error deleting temporary file: {str(e)}")
        
def iterate_playlist():
    global individual_audio_is_playing
    to_play = None # play this item
   
    # Timeout settings
    audio_timeout_finish = 3  # seconds
    playlist_wait_timeout = 15  # seconds

    queue_items_processed = 0
    last_queue_check_time = time.time()
    while True:
        try:

            if tts_playlist_queue.empty():
                with tts_lock:
                    if tts_is_speaking.value:
                        threading.Thread(target=set_response_window).start()
                        tts_is_speaking.value = False    
                tts_playlist_notify.wait()  
                tts_playlist_notify.clear()        
            print(f"Queue size before get: {tts_playlist_queue.qsize()}")
            to_play = tts_playlist_queue.get(block=False)
            print(f"Retrieved from tts_playlist_queue: {to_play}")
            print(f"Queue size after get: {tts_playlist_queue.qsize()}")


            if to_play is not None:
                command, audio_content = to_play
                print(f"Processing playlist item: command={command}, audio={audio_content}")

                # we hold iteration while audio is playing
                # We iterate once per audio file and playback
                # must complete for iteration to complete

                if individual_audio_is_playing.value:
                    print("Waiting for previous audio to finish...")
                    individual_audio_finished_notification.wait(timeout=audio_timeout_finish)
                    individual_audio_finished_notification.clear()

                if command is not None:
                    print(f"Processing command: {command}")
                    handle_home_assistant_command(command)

                if audio_content is not None:
                    print("Calling play_audio function")
                    with tts_lock:
                        if not tts_is_speaking.value:
                            tts_is_speaking.value = True  
                    play_audio(audio_content)
                else:
                    continue

        except Exception as e:
            print(f"An exception occurred in iterate_playlist: {str(e)}")

def handle_home_assistant_command(command):
    try:
        command_dict = json.loads(command)
        response = home_assistant_request('services/light/turn_on', 'post', payload=command_dict)
    except Exception as e:
        logging.error(f"Error executing light command: {e}")
        
                
tts_thread = threading.Thread(target=talk_with_tts)
tts_thread.daemon = True
tts_thread.start()

playlist_thread = threading.Thread(target=iterate_playlist)
playlist_thread.daemon = True
playlist_thread.start()

