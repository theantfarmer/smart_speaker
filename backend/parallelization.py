import sounddevice as sd
import numpy as np
from scipy.io.wavfile import write
from scipy.signal import butter, lfilter, get_window
from scipy.fftpack import fft
import threading
import tempfile
import wave
import pyaudio
import soundfile as sf
from pydub import AudioSegment
import tempfile
import librosa
import time
import os
import tempfile
import logging
import pdb
import collections
import queue
import multiprocessing
from multiprocessing import Process, Queue, Manager, Lock
from faster_whisper import WhisperModel
from parallelization import transcribe_audio


print("Speech module imports completed")
logging.basicConfig(level=logging.DEBUG)
print("Initializing global variables")
global samplerate
samplerate = 16000 
print(f"Global samplerate variable before audio_device_loop: {samplerate}")
duration = .25 # duration of each audio buffer in seconds
print("Global variables initialized")


is_speech = False

is_audio_system_running = False
whisper_model_loaded = False
transcription_condition = multiprocessing.Condition()
transcribed_text_queue = multiprocessing.Queue()
merged_chunks = None
merged_chunks_queue = multiprocessing.Queue()
merged_chunks_condition = multiprocessing.Condition()
transcription_lock = Lock()


# def centroid(audio_chunk, samplerate):
#     n_fft = 2048
#     hop_length = 512
#     spectral_centroid = librosa.feature.spectral_centroid(y=merged_chunks, sr=samplerate, n_fft=n_fft, hop_length=hop_length)
#     mean_centroid = np.mean(spectral_centroid)
#     threshold_low = 1000
#     threshold_high = 5000
#     is_speech = threshold_low <= mean_centroid <= threshold_high
#     return is_speech

# def mfcc(audio_chunk, samplerate):
#     n_mfcc = 13
#     n_fft = 2048
#     hop_length = 512

#     mfccs = librosa.feature.mfcc(y=audio_chunk, sr=samplerate, n_mfcc=n_mfcc, n_fft=n_fft, hop_length=hop_length)
    
#     # Calculate the mean and standard deviation of MFCCs
#     mean_mfccs = np.mean(mfccs, axis=1)
#     std_mfccs = np.std(mfccs, axis=1)
    
#     # Calculate the mean and standard deviation of MFCC deltas
#     if mfccs.shape[1] > 9:  # Check if there are enough frames for delta calculation
#         delta_mfccs = librosa.feature.delta(mfccs)
#         mean_delta_mfccs = np.mean(delta_mfccs, axis=1)
#         std_delta_mfccs = np.std(delta_mfccs, axis=1)
#     else:
#         mean_delta_mfccs = np.zeros_like(mean_mfccs)
#         std_delta_mfccs = np.zeros_like(std_mfccs)

#     # Combine the features
#     features = np.concatenate((mean_mfccs, std_mfccs, mean_delta_mfccs, std_delta_mfccs))

#     # Apply normalization
#     features = (features - np.mean(features)) / np.std(features)

#     # Define thresholds for different features
#     threshold_mean_mfccs = 131
#     threshold_std_mfccs = 20
#     threshold_mean_delta_mfccs = 5
#     threshold_std_delta_mfccs = 2

#     # Check if any of the features exceed their respective thresholds
#     is_speech = (
#         np.any(mean_mfccs > threshold_mean_mfccs) or
#         np.any(std_mfccs > threshold_std_mfccs) or
#         np.any(mean_delta_mfccs > threshold_mean_delta_mfccs) or
#         np.any(std_delta_mfccs > threshold_std_delta_mfccs)
#     )

#     return is_speech
     


def but_is_it_speech(audio_chunk, samplerate, chunk_buffer_1, chunk_buffer_2, stream_id):
    global keep_recording


    def db_level(audio_chunk):
        """Calculate the dB level of the audio data and return True if it indicates speech (above 70 dB)."""
        intensity = np.sqrt(np.mean(np.square(audio_chunk)))
        db = 20 * np.log10(intensity) if intensity > 0 else -np.inf
        calibrated_db = db + 110 
        return calibrated_db >= 75 

    def frequency_analysis(audio_chunk, samplerate):
        fft_data = np.fft.fft(audio_chunk)
        fft_freqs = np.fft.fftfreq(len(audio_chunk), 1/samplerate)
        min_freq = 100
        max_freq = 3000
        freq_indices = np.where((fft_freqs >= min_freq) & (fft_freqs <= max_freq))[0]
        speech_energy = np.sum(np.abs(fft_data[freq_indices])**2)
        total_energy = np.sum(np.abs(fft_data)**2)
        speech_ratio = speech_energy / total_energy
        threshold = 0.4
        is_speech = speech_ratio > threshold
        return is_speech


    db_speech = db_level(audio_chunk)
    print(f"db: {db_speech}")

    freqanal_speech = frequency_analysis(audio_chunk, samplerate)
    print(f"freq: {freqanal_speech}")

    # centroid_checker = centroid(audio_chunk, samplerate)
    # print(f"centroid: {centroid_checker}")

    # mfcc_speech = mfcc(audio_chunk, samplerate)
    # print(f"mfcc: {mfcc_speech}")

    # speech_detected = db_speech
    # speech_detected = freqanal_speech
    # speech_detected = centroid_checker
    # speech_detected = mfcc_speech

    # inputs = [db_speech, freqanal_speech, centroid_checker, mfcc_speech]
    inputs = [db_speech, freqanal_speech]
    speech_detected = sum(inputs) >= 2

    print(f"But is it speech?: {speech_detected}")
    return speech_detected

def preprocess(file, sample_rate=16000):
    sound = AudioSegment.from_file(file, format='wav', frame_rate=sample_rate)
    sound = sound.set_frame_rate(sample_rate)
    samples = sound.get_array_of_samples()
    samples = np.array(samples).flatten().astype(np.float32) / 32768.0
    return samples

def transcriber(merged_chunks_queue, transcribed_text_queue, transcription_condition, merged_chunks_condition):
    while True:
        print("inside transcriber while true")
        print("Waiting for audio data...")
        with merged_chunks_condition:
            print("Thread waiting for new chunks...")
            merged_chunks_condition.wait()
            print("Thread awakened. Processing chunks...")
            merged_chunks, samplerate = merged_chunks_queue.get()

            with tempfile.NamedTemporaryFile(delete=False, suffix='_mono.wav', dir='/tmp') as tmp_file:
                print(f"Temporary file created: {tmp_file.name}")
                expanded_merged_chunks = np.expand_dims(merged_chunks, axis=-1).astype('float32')
                print(f"Expanded audio data shape: {expanded_merged_chunks.shape}, type: {type(expanded_merged_chunks)}")
                sf.write(tmp_file.name, expanded_merged_chunks, int(samplerate))
                print(f"Audio data saved to {tmp_file.name}")

                def preprocess(file, sample_rate=16000):
                    sound = AudioSegment.from_file(file, format='wav', frame_rate=sample_rate)
                    sound = sound.set_frame_rate(sample_rate)
                    samples = sound.get_array_of_samples()
                    samples = np.array(samples).flatten().astype(np.float32) / 32768.0
                    return samples

                start_time = time.time()
                max_processes = 4
                model = WhisperModel("tiny", device="cpu", compute_type="int8")
                # audio_samples = preprocess(tmp_file.name)
                audio_samples = preprocess("tmpvsplpdsd_mono.wav")

                # segments, info = model.transcribe(audio_samples, beam_size=5, language="en")
                captured_text = transcribe_audio(audio_samples, max_processes,  silence_duration=2, model=model)
                

                # Measure the end time
                end_time = time.time()

                # Calculate the transcription time
                transcription_time = end_time - start_time

                print(f"Transcription completed in {transcription_time:.2f} seconds.")
                print("Detected language '%s' with probability %f" % (info.language, info.language_probability))


                # captured_text = ""
                # print(f"Segments: {segments}")
                # for segment in segments:
                #     print(f"Processing segment: {segment}")
                #     print("[%.2fs -> %.2fs] %s" % (segment.start, segment.end, segment.text))
                #     captured_text += segment.text + " "

                    # print(f"Captured text after transcription: {captured_text}")
                print(f"Final captured text: {captured_text}")
            

# def transcriber(merged_chunks_queue, transcribed_text_queue, transcription_condition):
#     global whisper_model_loaded, samplerate, is_audio_system_running

#     print(f"Transcriber process: {multiprocessing.current_process().name}")
#     print(f"Transcription condition: {transcription_condition}")
#     if not whisper_model_loaded:
#         print("Loading Whisper model...")
#         whisper_model = WhisperModel("tiny.en", device="cpu", compute_type="int8")
#         print("Whisper model loaded.")
#         whisper_model_loaded = True

#     while True:
        # print("inside transcriber while true")
        # print("Waiting for audio data...")
        # merged_chunks, samplerate = merged_chunks_queue.get()
        # print(f"Transcriber process: {multiprocessing.current_process().name}")
        # print(f"Audio data received. Size: {len(merged_chunks)}")
        # print(f"Audio data received from the queue. Size: {len(merged_chunks)}")

        # with tempfile.NamedTemporaryFile(delete=False, suffix='_mono.wav', dir='/tmp') as tmp_file:
        #     print(f"Temporary file created: {tmp_file.name}")
        #     expanded_merged_chunks = np.expand_dims(merged_chunks, axis=-1).astype('float32')
        #     print(f"Expanded audio data shape: {expanded_merged_chunks.shape}, type: {type(expanded_merged_chunks)}")
        #     sf.write(tmp_file.name, expanded_merged_chunks, int(samplerate))
        #     print(f"Audio data saved to {tmp_file.name}")

        #     try:


        #         print("Transcribing audio data...")
        #         start_time = time.time()
                
        #         segments, info = whisper_model.transcribe(merged_chunks.flatten(), beam_size=5, language="en")
                 
        #         end_time = time.time()
        #         transcription_time = end_time - start_time
                
        #         print(f"Transcription completed in {transcription_time:.2f} seconds.")
        #         print("Detected language:", info.language)
        #         print("Language probability:", info.language_probability)
        #         print("Detected language '%s' with probability %f" % (info.language, info.language_probability))

        #         print("segments:", segments)
        #         print("Type of segments:", type(segments))
        #         captured_text = ""
        #         print("Iterating over segments...")
        #         decompress_times = []
        #         captured_texts = []
        #         start_time_iteration = time.time()
        #         for i, segment in enumerate(segments, start=1):
        #             print(f"Processing segment {i}...")
        #             start_time_decompress = time.perf_counter()
        #             segment_text = segment.text
        #             segment_tokens = segment.tokens 
        #             segment_words = segment.words
        #             decompress_time = time.perf_counter() - start_time_decompress
        #             decompress_times.append(decompress_time)
        #             print("  avg_logprob:", segment.avg_logprob)
        #             print(f"Processing segment {i}...")
        #             start_time_segment = time.perf_counter()
        #             print("Type of segment:", type(segment))
        #             print("Attributes of segment:", dir(segment))
        #             print("  id:", segment.id)
        #             print("  seek:", segment.seek)
        #             print("  start:", segment.start)
        #             print("  end:", segment.end)
        #             print("  text:", segment.text)
        #             print("  tokens:", segment.tokens)
        #             print(f"Compression ratio: {segment.compression_ratio}")
        #             print("  temperature:", segment.temperature)
        #             print("  avg_logprob:", segment.avg_logprob)
        #             print("  compression_ratio:", segment.compression_ratio)
        #             print("  no_speech_prob:", segment.no_speech_prob)
                
                  
        #             print("Getting segment text...")
        #             start_time_decompress = time.perf_counter()
        #             segment_text = segment.text
        #             decompress_time = time.perf_counter() - start_time_decompress
        #             print(f"Time to decompress and get segment text: {decompress_time:.6f} seconds.")
        #             text_time = time.perf_counter() - start_time_decompress

        #             print("Getting segment tokens...")
        #             start_time_decompress = time.perf_counter()
        #             segment_tokens = segment.tokens
        #             decompress_time = time.perf_counter() - start_time_decompress
        #             print(f"Time to decompress and get segment tokens: {decompress_time:.6f} seconds.")
        #             tokens_time = time.perf_counter() - start_time_decompress

        #             print("Getting segment words...")
        #             start_time_decompress = time.perf_counter()
        #             segment_words = segment.words
        #             decompress_time = time.perf_counter() - start_time_decompress
        #             print(f"Time to decompress and get segment words: {decompress_time:.6f} seconds.")
        #             words_time = time.perf_counter() - start_time_decompress

        #             captured_text += segment_text + " "
        #             # captured_texts.append(segment_text)
        #             # print(f"\[{segment.start:.2f}s -> {segment.end:.2f}s\] {segment_text}")
        #             total_segment_time = time.perf_counter() - start_time_segment

        #             print(f"Time to get segment text: {text_time:.6f} seconds.")
        #             print(f"Time to get segment tokens: {tokens_time:.6f} seconds.")
        #             print(f"Time to get segment words: {words_time:.6f} seconds.")
        #             print(f"Total time for segment {i}: {total_segment_time:.6f} seconds.")

        #         end_time_iteration = time.time()
        #         iteration_time = end_time_iteration - start_time_iteration
        #         print(f"Iteration time: {iteration_time:.2f} seconds")
        #         # total_decompress_time = sum(decompress_times)
        #         # print(f"Total decompression time: {total_decompress_time:.6f} seconds")
        #         # # print(f"Captured text: {captured_text}")
                

        #     except KeyboardInterrupt:
        #         print("Transcription interrupted by the user.")
        #     except Exception as e:
        #         print(f"Error during transcription: {str(e)}")

        #     print(f"Captured text after transcription: {captured_text}")

            if captured_text:
                transcribed_text_queue.put(captured_text)
                print("inside if captured")
                print(f"Transcription condition in transcriber: {id(transcription_condition)}")
                with transcription_condition:
                    print(f"Sound channel thread {threading.current_thread().name} acquired the lock")
                    print("inside with condition")
                    transcribed_text_queue.put(captured_text)
                    print(f"Transcribed text added to the queue. Queue size: {transcribed_text_queue.qsize()}")
                    # print(f"Transcriber process: {multiprocessing.current_process().name}")
                    print(f"Transcription condition in transcriber before notify: {id(transcription_condition)}")
                    print("Before notify")
                    transcription_condition.notify()
                    # print(f"Transcription process {multiprocessing.current_process().name} released the lock")
                    print("After notify")
                print(f"Transcription successful. Text: {captured_text}")



def buffer_manager(stream_id, fresh_new_chunk_queue, stream_condition):
    global keep_recording, transcription_lock, samplerate, transcribed_texts
    speech_detected_1 = False
    speech_detected_2 = False
    chunk_buffer_size = 1
    number_of_chunks_to_end_continuous = 4
    chunk_buffer_1 = collections.deque(maxlen=chunk_buffer_size)
    chunk_buffer_2 = collections.deque(maxlen=chunk_buffer_size)  
    first_speech_chunk = None
    chunk_counter_1 = 0
    chunk_counter_2 = 0
    continuous_buffer = Queue()
    speech_false_counter_1 = 0
    speech_false_counter_2 = 0
    continuous_recording_1 = False
    continuous_recording_2 = False
    print("Buffer manager started")
    lock = Lock()
    
    
    while True:
        with stream_condition:
            stream_condition.wait()
            try:
                audio_chunk = fresh_new_chunk_queue.get(block=False)
                
                if stream_id == 1:
                    speech_detected_1 = but_is_it_speech(audio_chunk, samplerate, chunk_buffer_1, chunk_buffer_2, stream_id)
                    # print(f"Speech detected in stream {stream_id}: {speech_detected_1}")
                    # print(f"the path after speech detected will be continuous_recording_1 {continuous_recording_1}")
                    
                    if not continuous_recording_1:
                        if not speech_detected_1:
                            # print(f"Appending audio chunk to chunk buffer")
                            chunk_buffer_1.append(audio_chunk)
                        else:
                            if not continuous_recording_2:
                                if continuous_buffer.empty():
                                    continuous_recording_1 = True
                                    print("Continuous recording is true for stream 1")
                                    chunk_id = f"stream{stream_id}_01"
                                    print(f"Assigning chunk ID: {chunk_id}")
                                    continuous_buffer.put((chunk_id, audio_chunk))
                                    print(f"Appending chunk {chunk_id} to continuous buffer")
                                    continuous_chunk_counter = 2
                                    if chunk_buffer_1:
                                        merged_chunk = np.concatenate([chunk for chunk in chunk_buffer_1])
                                        chunk_id = f"stream{stream_id}_00"
                                        print(f"Assigning chunk ID: {chunk_id}")
                                        continuous_buffer.put((chunk_id, merged_chunk))
                                        print(f"Appending chunk {chunk_id} to continuous buffer")
                                        chunk_buffer_1.clear()
                    else:
                        print(f"Inside continuous_recording_1 loop")
                        chunk_id = f"stream{stream_id}_{continuous_chunk_counter:02d}"
                        print(f"Assigning chunk ID: {chunk_id}")
                        continuous_buffer.put((chunk_id, audio_chunk))
                        print(f"Appending chunk {chunk_id} to continuous buffer")
                        continuous_chunk_counter += 1
                        print(f"Stream {stream_id}: Continuous buffer contains {continuous_buffer.qsize()} chunks")
                        
                        if not speech_detected_1:
                            speech_false_counter_1 += 1
                            print(f"Stream 1: Non-speech chunk count: {speech_false_counter_1}")
                        else:
                            speech_false_counter_1 = 0
                        
                        if not speech_detected_1 and speech_false_counter_1 >= number_of_chunks_to_end_continuous:
                            continuous_recording_1 = False
                            print(f"Stream {stream_id}: Continuous recording stopped")
                    
     
                            if not continuous_buffer.empty():
                                print("Sorting chunks in the continuous buffer...")
                                sorted_chunks = []
                                while not continuous_buffer.empty():
                                    chunk = continuous_buffer.get()
                                    sorted_chunks.append(chunk)
                                sorted_chunks.sort(key=lambda x: x[0])
                                print(f"Continuous buffer after sorting: {[chunk_id for chunk_id, _ in sorted_chunks]}")
                                
                                print("Concatenating audio data...")
                                merged_chunks = np.concatenate([chunk for _, chunk in sorted_chunks])
                                print(f"Number of chunks concatenated: {len(sorted_chunks)}")
                                
                                print("Putting audio data into queue for transcription...")
                                with merged_chunks_condition:
                                    merged_chunks_queue.put((merged_chunks, samplerate))
                                    print("Audio data put into queue.")
                                    merged_chunks_condition.notify()
                                    print("merged chunk notify sent.")

                                print("Clearing the continuous buffer...")
                                continuous_buffer = Queue()
                                print("Continuous buffer cleared.")
                                
                                chunk_counter_1 = 0
                            else:
                                print("Continuous buffer is empty.")
                                

            # else:
            #     chunk_buffer_2.append(audio_chunk)
            #     speech_detected_2 = but_is_it_speech(audio_chunk, samplerate)
            #     if speech_detected_2:
            #         print(f"Speech detected in stream 2")
            #         if not continuous_recording_1:
                        # print("Continuous recording is true for stream 2")
                        # continuous_buffer.extend(chunk_buffer_2)
                        # chunk_buffer_2.clear()
                        # continuous_recording_2 = True
            #             with condition_stream2:
            #                 condition_stream2.notify_all()
            #             while continuous_recording_2:
            #                 audio_chunk = sd.rec(int(duration * samplerate), channels=1, samplerate=samplerate, dtype='float32')
            #                 sd.wait()
            #                 audio_chunk = np.squeeze(audio_chunk)
            #                 continuous_buffer.put(audio_chunk)
            #                 speech_detected_2 = but_is_it_speech(audio_chunk, samplerate)
            #                 if not speech_detected_2:
            #                     continuous_recording_2 = False
            #                     print(f"Continuous recording stopped in stream 2")
            #                     with condition_stream2:
            #                         condition_stream2.notify_all()
            #                     break
            
            except queue.Empty:
                continue   

def create_new_chunks(fresh_new_chunk_queue, stream_condition, new_chunk_lock):
    while keep_recording:
        audio_chunk = sd.rec(int(duration * samplerate), channels=1, samplerate=samplerate, dtype='float32')
        sd.wait()
        audio_chunk = np.squeeze(audio_chunk)
        fresh_new_chunk_queue.put(audio_chunk)
        with new_chunk_lock:
            stream_condition.notify()


def startup_items(transcribed_text_queue, transcription_condition):
    print("Entering startup_items function.")
    global keep_recording, merged_chunks_queue, whisper_model, samplerate, duration, transcription_process
    frames_per_buffer = int(duration * samplerate)
    print(f"Frames per buffer: {frames_per_buffer}")
    keep_recording = True
    

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

    print("Starting record audio thread...")
    create_chunks_thread = threading.Thread(target=create_new_chunks, args=(fresh_new_chunk_queue, stream_condition, new_chunk_lock))
    create_chunks_thread.start()
    print("Record audio thread started.")

    print(f"Sound channel thread: {threading.current_thread().name}")
    print(f"Transcription condition: {transcription_condition}")
    print("Creating transcription thread...")
    
    # transcriber(merged_chunks_queue, transcribed_text_queue, transcription_condition, merged_chunks_condition)
    # print("Transcription thread started.")
    
    print("Creating transcription process...")
    transcription_process = multiprocessing.Process(target=transcriber,
                                                    args=(merged_chunks_queue, transcribed_text_queue, transcription_condition, merged_chunks_condition))
    transcription_process.start()
    print("Transcription process started.")



 

def capture_speech():
    global is_audio_system_running, transcription_condition, transcribed_text_queue, transcription_process
    if not is_audio_system_running:

        startup_items(transcribed_text_queue, transcription_condition)
        is_audio_system_running = True

    print(f"after with: {threading.current_thread().name}")
    print(f"after with Transcription condition: {transcription_condition}")
    print(f"Transcription condition in capture_speech: {id(transcription_condition)}")
    with transcription_condition:
        print(f"External module thread {threading.current_thread().name} acquired the lock")
        print(f"before with Main thread: {threading.current_thread().name}")
        print(f"before with Transcription condition: {transcription_condition}")
        print(f"Main thread: {threading.current_thread().name}")
        print("Before wait")
        print(f"Transcription condition: {transcription_condition}")
        print("Waiting...")
        transcription_condition.wait()
        print("After wait")
        queue_size = transcribed_text_queue.qsize()
        transcribed_texts = []
        # for _ in range(queue_size):multiprocessing.Condition
        #     transcribed_text = transcribed_text_queue.get()
        #     transcribed_texts.append(transcribed_text)

        print(f"External module thread {threading.current_thread().name} released the lock")
        print(f"Capture text complete.")
        return transcribed_texts[-1]


def stop_recording():
    print("Entering stop_recording function.")
    global keep_recording
    keep_recording = False
    thread1.join()
    speech_detection_thread.join()
    print("Leaving stop_recording function.")

if __name__ == "__main__":
    print("Running speech to text module directly.")
    capture_speech()
    print("System initialized. Enter 'q' to quit...")
    while input() != 'q':
        pass
    stop_recording()
    print("Recording stopped. Exiting system...")