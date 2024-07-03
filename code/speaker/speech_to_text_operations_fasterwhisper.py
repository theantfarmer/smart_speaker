# almost!  very close!  just some issues with transcription interupting recording

# This is the recording and transcription module.  It is called
# by the capture_speech function.  It calls startup_items which
# launches threads and processes and other things.  

# The buffer_manager is responsable for recording and processing 
# audio vwdiew transcription. It the most complicated function.  
# It creates small chunks of audio and tests each one for the
# likely presence of speech.  If there is no speech, it is sent
# to the chunk buffer where it is stored until it is pushed out 
# by successive chunks.  If speech is detected, continuous mode 
# turns on.  At this point, the current chunk, subsequent chunks,
# and the contents are given ID numbers and moved to the continuous
# buffer.  When a pause in speech is detected, the contents of 
# the continuous buffer is sorted, merged and sent to transcription.
# A longer pause will end continuous mode and send a flag that the speaker 
# is done speaking.

# The transcriber function is pretty straight forward.  It receives the 
# audio from buffer_manager.  It can save the audio temporarily if the 
# save section is uncommented.  This is helpful because most transcription 
# problems are related to problems with the audio.  Next is transcription. 
# Keep in mind that the actual transcription process takes place during
# iteration.  The transcribed text is sent to the transcription queue 
# and held there.  When the finished flag from continuous buffer passes 
# here, a notification is sent to release the contents from the queue.

# capture_speech gets the transcription queue contents, merges it,
# and returns it to the function that called it.  


import sounddevice as sd
import numpy as np
# from scipy.io.wavfile import write
# from scipy.signal import butter, lfilter, get_window
# from scipy.fftpack import fft
from scipy import signal
import threading
import tempfile
import wave
import pyaudio
import soundfile as sf
from pydub import AudioSegment
import tempfile
import time
import os
import tempfile
import logging
import pdb
import collections
import queue
import multiprocessing
from multiprocessing import Process, Queue, Manager, Lock, Value
from faster_whisper import WhisperModel
from faster_whisper.vad import get_speech_timestamps, VadOptions
from shared_variables import user_response_en_route, user_response_window, tts_is_speaking, tts_lock


print("Speech module imports completed")
logging.basicConfig(level=logging.DEBUG)
print("Initializing global variables")
global samplerate
samplerate = 16000 
print(f"Global samplerate variable before audio_device_loop: {samplerate}")
duration = .25 # duration of each audio buffer in seconds
print("Global variables initialized")

is_speech = False

# continuous mode refers to continuous recording
# when someone is speaking
# as opposed to chunk mode when someone is not.
# we export it so other modules know when someone is speaking.
continuous_recording = Value('b', False)


is_audio_system_running = False
whisper_model_loaded = False
merged_chunks = None

# the variables below are for transcriber when running as a thread
# you also must swap the thread and process starters in teh Startup Items function
merged_chunks_queue = Queue()
transcription_condition = threading.Condition()
transcribed_text_queue = queue.Queue()
merged_chunks_condition = threading.Condition()

# these variables are for the transcrriber process instead of the thread
# merged_chunks_queue = multiprocessing.Queue()
# merged_chunks_condition = multiprocessing.Condition()
# transcription_condition = multiprocessing.Condition()
# transcribed_text_queue = multiprocessing.Queue()

transcription_lock = Lock()
notification_counter = 0
background_noise_profile = None

def background_noise_profiler(audio_chunk, alpha=0.1):
    global background_noise_profile
    
    # Check input
    if np.any(np.isnan(audio_chunk)):
        print("Warning: NaN values in input audio chunk")
        return background_noise_profile

    # Check for zero values
    if np.all(audio_chunk == 0):
        print("Warning: All zero values in audio chunk")
        return background_noise_profile

    # Compute spectrum
    chunk_spectrum = np.abs(np.fft.rfft(audio_chunk))
    
    # Check FFT output
    if np.any(np.isnan(chunk_spectrum)):
        print("Warning: NaN values after FFT")
        return background_noise_profile

    if background_noise_profile is None:
        background_noise_profile = chunk_spectrum
        print("Noise profile initialized")
    else:
        # Update profile
        new_profile = (1 - alpha) * background_noise_profile + alpha * chunk_spectrum
        
        # Check for NaN in new profile
        if np.any(np.isnan(new_profile)):
            print("Warning: NaN values in updated noise profile")
            # print(f"Alpha: {alpha}")
            # print(f"Max background_noise_profile: {np.max(background_noise_profile)}")
            # print(f"Min background_noise_profile: {np.min(background_noise_profile)}")
            # print(f"Max chunk_spectrum: {np.max(chunk_spectrum)}")
            # print(f"Min chunk_spectrum: {np.min(chunk_spectrum)}")
        else:
            background_noise_profile = new_profile

    mean_profile = np.mean(background_noise_profile)
    # print(f"Current noise profile mean: {mean_profile:.4f}")
    # print(f"Max value in profile: {np.max(background_noise_profile):.4f}")
    # print(f"Min value in profile: {np.min(background_noise_profile):.4f}")
    
    return background_noise_profile

def noise_reducer(audio_data, noise_profile, reduction_factor=0.4, threshold=0.2):
    # print(f"Audio data shape before noise reduction: {audio_data.shape}")
    # print(f"Noise profile shape: {noise_profile.shape}")

    # Convert audio to frequency domain
    audio_spectrum = np.fft.rfft(audio_data)
    audio_magnitude = np.abs(audio_spectrum).astype(np.float32)
    audio_phase = np.angle(audio_spectrum).astype(np.float32)

    # Ensure noise_profile and audio_magnitude have the same shape
    if noise_profile.shape != audio_magnitude.shape:
        print(f"Warning: Noise profile shape {noise_profile.shape} does not match audio magnitude shape {audio_magnitude.shape}")
        noise_profile = np.resize(noise_profile, audio_magnitude.shape)

    # Compute the noise reduction gain
    gain = np.maximum(1 - (noise_profile / (audio_magnitude + 1e-10)) * reduction_factor, threshold)
    gain = gain.astype(np.float32)

    # Apply the gain and reconstruct the signal
    enhanced_magnitude = (audio_magnitude * gain).astype(np.float32)
    enhanced_spectrum = enhanced_magnitude * np.exp(1j * audio_phase).astype(np.complex64)
    enhanced_audio = np.fft.irfft(enhanced_spectrum).astype(np.float32)

    # print(f"Audio data shape after noise reduction: {enhanced_audio.shape}")
    
    return enhanced_audio

def merged_chunk_enhancer(merged_chunks, samplerate):
    # this is for processes better applied to merged chunks
    # to improve transcription
    
    # Normalize audio
    max_amplitude = np.max(np.abs(merged_chunks))
    enhanced_speech = merged_chunks / max_amplitude

    # echo reduction
    # Parameters for echo reduction (adjust these for lighter effect)
    delay = int(0.05 * samplerate)  # 50 ms delay
    decay = 0.1  # Very low decay factor for minimal effect

    # Create echo kernel
    echo_kernel = np.zeros(delay + 1)
    echo_kernel[0] = 1  # Original signal
    echo_kernel[-1] = -decay  # Delayed and inverted echo

    # Apply echo reduction
    enhanced_speech = signal.convolve(enhanced_speech, echo_kernel, mode='same')

    # Renormalize after echo reduction
    enhanced_speech /= np.max(np.abs(enhanced_speech))

    return enhanced_speech

def but_is_it_speech(audio_chunk, samplerate, stream_id):
    # various parameters to check audio for speech
    # I designed my own system which is still in place,
    # but commented out in favor of the vad
    
    global keep_recording

    def vad(audio_chunk):
        if len(audio_chunk.shape) > 1:
            audio_chunk = np.mean(audio_chunk, axis=1)

        # Define VAD options with increased sensitivity
        vad_options = VadOptions(
            threshold=0.11, 
            min_speech_duration_ms=10,
            max_speech_duration_s=float('inf'),
            min_silence_duration_ms=10,
            window_size_samples=512, 
            speech_pad_ms=10
        )

        # Detect speech
        speech_timestamps = get_speech_timestamps(audio_chunk, vad_options)
        vad_speech = len(speech_timestamps) > 0

        return vad_speech

    def db_level(audio_chunk):
        """Calculate the dB level of the audio data and return True if it indicates speech (above 70 dB)."""
        intensity = np.sqrt(np.mean(np.square(audio_chunk)))
        db = 20 * np.log10(intensity) if intensity > 0 else -np.inf
        calibrated_db = db + 110
        print(f"Calibrated dB level: {calibrated_db:.2f} dB")  # Print the calibrated dB level
        return calibrated_db >= 58

    def frequency_analysis(audio_chunk, samplerate):
        audio_chunk = audio_chunk.astype(np.float32) / 32768.0  # Convert audio data to float32
        fft_data = np.fft.fft(audio_chunk)
        fft_freqs = np.fft.fftfreq(len(audio_chunk), 1/samplerate)
        min_freq = 100
        max_freq = 3000
        freq_indices = np.where((fft_freqs >= min_freq) & (fft_freqs <= max_freq))[0]
        speech_energy = np.sum(np.abs(fft_data[freq_indices])**2)
        total_energy = np.sum(np.abs(fft_data)**2)
        speech_ratio = speech_energy / total_energy
        threshold = 0.35
        is_speech = speech_ratio > threshold
        return is_speech 
    
    def energy_detector(audio_chunk, threshold=0.003): 
        energy = np.sum(audio_chunk**2) / len(audio_chunk)
        return energy > threshold

    vad_speech = vad(audio_chunk)
    print(f"vad: {vad_speech}")

    db_speech = db_level(audio_chunk)
    # print(f"db: {db_speech}")

    freqanal_speech = frequency_analysis(audio_chunk, samplerate)
    # print(f"freq: {freqanal_speech}")
    
    energy_speech = energy_detector(audio_chunk)
    # print(f"energy_speech: {energy_speech}")
    
    # speech_detected = db_speech
    # speech_detected = freqanal_speech
    speech_detected = vad_speech

    # inputs = [db_speech, energy_speech, freqanal_speech, vad_speech]
    # speech_detected = sum(inputs) >= 2

    # print(f"But is it speech?: {speech_detected}")
    return speech_detected

def transcriber(merged_chunks_queue, transcribed_text_queue, transcription_condition, merged_chunks_condition):
    global whisper_model_loaded, samplerate, is_audio_system_running, notification_counter

    print(f"Transcriber process: {multiprocessing.current_process().name}")
    print(f"Transcription condition: {transcription_condition}")

    while True:
        print("Transcriber waiting for audio data...")
        
        with merged_chunks_condition:
            print("Transcriber waiting for new chunks...")
            while merged_chunks_queue.empty() and notification_counter == 0:
                merged_chunks_condition.wait()


        while True:
            if merged_chunks_queue.empty() and notification_counter < 1:
                break

            merged_chunks, samplerate = merged_chunks_queue.get()
            notification_counter -= 1
            # print(f"Transcriber received merged chunks: size={len(merged_chunks)}, samplerate={samplerate}")

# most transcription issues are due to audio quality
# uncomment this save section and check /tmp to listen
    
        # with tempfile.NamedTemporaryFile(delete=False, suffix='_speech_to_text.wav', dir='/tmp') as tmp_file:
        #     print(f"Temporary file created: {tmp_file.name}")
        #     print(f"Audio data shape: {merged_chunks.shape}, type: {merged_chunks.dtype}")
        #     sf.write(tmp_file.name, merged_chunks, int(samplerate))
        #     print(f"Audio data saved to {tmp_file.name}")

            try:
             
                print("Transcribing audio data...")
                start_time = time.time()
                segments, info = whisper_model.transcribe(merged_chunks.flatten(), beam_size=5, language="en")
                end_time = time.time()
                transcription_time = end_time - start_time
                print(f"Transcription completed in {transcription_time:.2f} seconds.")
                                
                # print("Detected language:", info.language)
                # print("Language probability:", info.language_probability)
                # print("Detected language '%s' with probability %f" % (info.language, info.language_probability))

                # print("segments:", segments)
                # print("Type of segments:", type(segments))
                captured_text = ""
                # print("Iterating over segments...")
                decompress_times = []
                captured_texts = []
                start_time_iteration = time.time()
                segments = list(segments)
                for i, segment in enumerate(segments, start=1):
                    segment_text = segment.text
                    segment_tokens = segment.tokens
                    segment_words = segment.words
                    captured_text += segment_text
                end_time_iteration = time.time()
                iteration_time = end_time_iteration - start_time_iteration
                print(f"Iteration time: {iteration_time:.2f} seconds")
                print(f"Captured text: {captured_text}")
                
            except KeyboardInterrupt:
                print("Transcription interrupted by the user.")
            except Exception as e:
                print(f"Error during transcription: {str(e)}")

            print(f"Captured text after transcription: {captured_text}")

            if captured_text:
                # print(f"Transcription condition in transcriber: {id(transcription_condition)}")
                with transcription_condition:
                    # print(f"Sound channel thread {threading.current_thread().name} acquired the lock")
                    # print("inside with condition")
                    if not captured_text or captured_text.isspace():
                        continue
                    else: 
                        transcribed_text_queue.put(captured_text)
                        # print(f"Transcribed text added to the queue. Queue size: {transcribed_text_queue.qsize()}")
                        # print(f"Transcriber process: {multiprocessing.current_process().name}")
                        # print(f"Transcription condition in transcriber before notify: {id(transcription_condition)}")
                        # print("Before notify")
                        transcription_condition.notify()
                        # print(f"Transcription process {multiprocessing.current_process().name} released the lock")
                        # print("After notify")
                    print(f"Transcription successful. Text: {captured_text}")
            else:                        
                with user_response_en_route.get_lock():
                    user_response_en_route.value = False
                    print("user_response_en_route set to False in transcriber")
                    
def buffer_manager(stream_id, fresh_new_chunk_queue, stream_condition):
    global keep_recording, samplerate, user_response_window, whisper_model_loaded, user_response_en_route, duration, notification_counter, background_noise_profile

    chunk_buffer_size = 2
    number_of_chunks_to_end_phrase = 3 # sends the contents of continuous buffer to be transcribed
    number_of_chunks_to_end_continuous = 3 # holds transcribed text until speaker is fiinsihed speaking
    chunk_buffer = collections.deque(maxlen=chunk_buffer_size)
    continuous_recording = False
    continuous_buffer = Queue()
    speech_false_counter = 0
    continuous_chunk_counter = 0

    p = pyaudio.PyAudio()
    stream = p.open(format=pyaudio.paInt16,
                    channels=1,
                    rate=samplerate,
                    input=True,
                    frames_per_buffer=int(duration * samplerate))
    print(f"Buffer manager started. Initial user_response_en_route value: {user_response_en_route.value}")
    while keep_recording:
        audio_chunk = stream.read(int(duration * samplerate))
        raw_chunk = np.frombuffer(audio_chunk, dtype=np.int16).copy() # for profiling
        numpy_data = raw_chunk.astype(np.float32) / 32768.0  # for transcribing

        if background_noise_profile is not None:
            numpy_data = noise_reducer(numpy_data, background_noise_profile)
            speech_detected = but_is_it_speech(numpy_data, samplerate, stream_id)
        else: 
            speech_detected = False
        print(f"Speech detected: {speech_detected}")

        with tts_lock: 
            if not tts_is_speaking.value:          
                if not continuous_recording:
                    # print("Not in continuous recording mode")
                    if not speech_detected:
                        background_noise_profile = background_noise_profiler(raw_chunk)
                        # print("No speech detected, profiling, appending chunk to buffer")
                        chunk_buffer.append(numpy_data)
                    else:
                        # print("Speech detected, starting continuous recording")
                        if continuous_buffer.empty():
                            continuous_recording = True
                            with user_response_window.get_lock():
                                if user_response_window.value:
                                    with user_response_en_route.get_lock():
                                        print(f"user_response_en_route value before setting: {user_response_en_route.value}")
                                        user_response_en_route.value = True
                                        print(f"user_response_en_route value after setting: {user_response_en_route.value}")
                            print("Continuous recording started")
                            chunk_id = f"chunk_01"
                            print(f"Assigning chunk ID: {chunk_id}")
                            continuous_buffer.put((chunk_id, numpy_data))
                            print(f"Appending chunk {chunk_id} to continuous buffer")
                            continuous_chunk_counter = 2
                            if chunk_buffer:
                                merged_chunk = np.concatenate(chunk_buffer)
                                chunk_id = f"chunk_00"
                                print(f"Assigning chunk ID: {chunk_id}")
                                continuous_buffer.put((chunk_id, merged_chunk))
                                print(f"Appending chunk {chunk_id} to continuous buffer")
                                chunk_buffer.clear()
                else:
                    print("Inside continuous recording loop")
                    chunk_id = f"chunk_{continuous_chunk_counter:02d}"
                    print(f"Assigning chunk ID: {chunk_id}")
                    continuous_buffer.put((chunk_id, numpy_data))
                    print(f"Appending chunk {chunk_id} to continuous buffer")
                    continuous_chunk_counter += 1
                    print(f"Continuous buffer contains {continuous_buffer.qsize()} chunks")

                    if not speech_detected:
                        speech_false_counter += 1
                        print(f"Non-speech chunk count: {speech_false_counter}")
                    else:
                        speech_false_counter = 0

                    if speech_false_counter == number_of_chunks_to_end_phrase:
                        continuous_recording = False
                        print("Continuous recording stopped")

                        if not continuous_buffer.empty():
                            print("Sorting chunks in the continuous buffer...")
                            sorted_chunks = []
                            while not continuous_buffer.empty():
                                chunk = continuous_buffer.get()
                                sorted_chunks.append(chunk)
                            sorted_chunks.sort(key=lambda x: x[0])
                            print(f"Continuous buffer after sorting: {[chunk_id for chunk_id, _ in sorted_chunks]}")
                            
                            # print("Concatenating audio data...")
                            merged_chunks = np.concatenate([chunk for _, chunk in sorted_chunks])
                            print(f"Number of chunks concatenated: {len(sorted_chunks)}")
                            
                            # Pre-process the merged chunks to improve transcription
                            processed_chunks = merged_chunk_enhancer(merged_chunks, samplerate)

                            print("Putting audio data into queue for transcription...")
                            with merged_chunks_condition:
                                merged_chunks_queue.put((processed_chunks, samplerate))
                                # print("Audio data put into queue.")
                                merged_chunks_condition.notify()
                                notification_counter += 1
                                # print("merged chunk notify sent.")

                            # print("Clearing the continuous buffer...")
                            continuous_buffer = Queue()
                            # print("Continuous buffer cleared.")
                            
                            chunk_counter_1 = 0
                        else:
                            print("Continuous buffer is empty.")

                        speech_false_counter = 0
                        continuous_chunk_counter = 0

    stream.stop_stream()
    stream.close()
    p.terminate()
    
def startup_items(transcribed_text_queue, transcription_condition):
    print("Entering startup_items function.")
    global keep_recording, merged_chunks_queue, whisper_model, whisper_model_loaded, samplerate, duration, transcription_process
    frames_per_buffer = int(duration * samplerate)
    print(f"Frames per buffer: {frames_per_buffer}")
    keep_recording = True
    
    if not whisper_model_loaded:
        print("Loading Whisper model...")
        whisper_model = WhisperModel("tiny.en", device="cpu", compute_type="int8")
        print("Whisper model loaded.")
        whisper_model_loaded = True



    print("Selecting default input device...")
    device_info = sd.query_devices(None, 'input')
    print(f"Default input device: {device_info['name']}")

    print("Creating audio queue...")
    fresh_new_chunk_queue = multiprocessing.Queue()
    print("Audio queue created.")

    new_chunk_lock = threading.Lock()
    stream_condition = threading.Condition(new_chunk_lock)

    print("Starting audio thread...")
    buffer_manager_thread = threading.Thread(target=buffer_manager, args=(1, fresh_new_chunk_queue, stream_condition))
    buffer_manager_thread.start()
    print("Audio thread started.")
    

    print(f"Sound channel thread: {threading.current_thread().name}")
    print(f"Transcription condition: {transcription_condition}")

    #transcriber is nice in thread, but takes 4 times as long to transcribe.  So thread is preferred now.   
    print("Creating transcription thread...")
    transcription_thread = threading.Thread(target=transcriber,
                                            args=(merged_chunks_queue, transcribed_text_queue, transcription_condition, merged_chunks_condition))
    transcription_thread.start()
    print("Transcription thread started.")
    
    # print("Creating transcription process...")
    # transcription_process = multiprocessing.Process(target=transcriber,
    #                                                 args=(merged_chunks_queue, transcribed_text_queue, transcription_condition, merged_chunks_condition))
    # transcription_process.start()
    # print("Transcription process started.")


def capture_speech():
    global is_audio_system_running, transcription_condition, transcribed_text_queue, transcription_process
    print("in cap speech")
    if not is_audio_system_running:
        startup_items(transcribed_text_queue, transcription_condition)
        is_audio_system_running = True
    # print("after if not audio")
    # print(f"after with: {threading.current_thread().name}")
    # print(f"Transcription condition in capture_speech: {id(transcription_condition)}")
    # print("before with transcription cap speech")
    with transcription_condition:
        # print(f"Main thread: {threading.current_thread().name}")
        
        if transcribed_text_queue.empty():
            # print("Before wait")
            # print(f"Transcription condition: {transcription_condition}")
            # print("Waiting...")
            transcription_condition.wait()
            # print("After wait")
        
        queue_size = transcribed_text_queue.qsize()
        transcribed_texts = []
        for _ in range(queue_size):
            transcribed_text = transcribed_text_queue.get()
            transcribed_texts.append(transcribed_text)
        # print(f"Capture text complete.")
        return transcribed_texts[-1]

def stop_recording():
    # print("Entering stop_recording function.")
    global keep_recording
    keep_recording = False
    thread1.join()
    speech_detection_thread.join()
    print("Leaving stop_recording function.")

if __name__ == "__main__":
    # print("Running speech to text module directly.")
    capture_speech()
    # print("System initialized. Enter 'q' to quit...")
    while input() != 'q':
        pass
    stop_recording()
    # print("Recording stopped. Exiting system...")