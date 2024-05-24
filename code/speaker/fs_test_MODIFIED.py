from faster_whisper import WhisperModel
import time
import numpy as np
from pydub import AudioSegment
import multiprocessing
from multiprocessing import Queue, Condition

def preprocess(file, sample_rate=16000):
    sound = AudioSegment.from_file(file, format='wav', frame_rate=sample_rate)
    sound = sound.set_frame_rate(sample_rate)
    samples = sound.get_array_of_samples()
    samples = np.array(samples).flatten().astype(np.float32) / 32768.0
    return samples

def transcriber(audio_queue, result_queue, transcription_condition):
    model = WhisperModel("tiny", device="cpu", compute_type="int8")

    while True:
        with transcription_condition:
            transcription_condition.wait()
            if audio_queue.empty():
                break
            audio_samples = audio_queue.get()

        start_time = time.time()
        segments, info = model.transcribe(audio_samples, beam_size=5, language="en")
        end_time = time.time()
        transcription_time = end_time - start_time

        result_queue.put((segments, info, transcription_time))
        with transcription_condition:
            transcription_condition.notify()

if __name__ == '__main__':
    audio_queue = Queue()
    result_queue = Queue()
    transcription_condition = Condition()

    transcription_process = multiprocessing.Process(target=transcriber, args=(audio_queue, result_queue, transcription_condition))
    transcription_process.start()

    audio_samples = preprocess("tmpvsplpdsd_mono.wav")
    audio_queue.put(audio_samples)

    with transcription_condition:
        transcription_condition.notify()

    with transcription_condition:
        transcription_condition.wait()
        segments, info, transcription_time = result_queue.get()

    print(f"Transcription completed in {transcription_time:.2f} seconds.")
    print("Detected language '%s' with probability %f" % (info.language, info.language_probability))
    for segment in segments:
        print("[%.2fs -> %.2fs] %s" % (segment.start, segment.end, segment.text))

    audio_queue.put(None)
    with transcription_condition:
        transcription_condition.notify()

    transcription_process.join()