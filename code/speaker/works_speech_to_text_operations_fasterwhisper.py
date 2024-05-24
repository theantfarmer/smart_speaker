import sounddevice as sd
import numpy as np
from scipy.io.wavfile import write
import queue
import threading
from faster_whisper import WhisperModel

CHUNK_SIZE = 480
BUFFER_SIZE = 4800
duration = 5
sample_rate = 16000
output_file = "test_audio.wav"

model = WhisperModel("small.en", device="cpu", compute_type="int8")

audio_queue = queue.Queue()
lock = threading.Lock()

class RingBuffer:
    def __init__(self, size):
        self.data = [None for _ in range(size)]
        self.size = size
        self.index = 0

    def append(self, element):
        self.data[self.index] = element
        self.index = (self.index + 1) % self.size

    def get_all(self):
        return self.data

def get_speech(duration, sample_rate, output_file):
    audio_data = sd.rec(int(duration * sample_rate), samplerate=sample_rate, channels=1)
    sd.wait()
    write(output_file, sample_rate, audio_data)

    try:
        segments, _ = model.transcribe(output_file, beam_size=5)
        captured_text = ' '.join(segment.text for segment in segments)
        return captured_text
    except Exception as e:
        return None

def capture_speech():
    buffer = RingBuffer(BUFFER_SIZE)
    audio_data = np.empty((0,))
    while True:
        audio_data = sd.rec(int(duration * sample_rate), samplerate=sample_rate, channels=1)
        sd.wait()

        # Store audio data in the ring buffer
        for data in audio_data:
            buffer.append(data)

        # Accumulate audio data for transcription
        audio_data = np.append(audio_data, buffer.get_all())

        # Write to file and transcribe
        write("temp_audio.wav", sample_rate, audio_data)
        text = get_speech(len(audio_data) / sample_rate, sample_rate, "temp_audio.wav")
        if text is not None:
            print("Captured Text: ", text)
            return text
