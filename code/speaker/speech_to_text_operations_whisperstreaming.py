import sounddevice as sd
import numpy as np
from scipy.io.wavfile import write
import tempfile
from faster_whisper import WhisperModel
from text_to_speech_operations import tts_is_speaking

# Initialize the Whisper model
model = WhisperModel("base", device="cpu")  # Adjust model size and device as needed

def capture_and_process_chunk(chunk_duration=5):
    samplerate = 16000  # Whisper expects 16kHz audio

    def callback(indata, frames, time, status):
        # This callback captures audio but does not process it here
        volume_norm = np.linalg.norm(indata) * 10
        print(f"Capturing audio... Volume: {volume_norm:.2f}")

    print("Listening for speech...")
    with tempfile.NamedTemporaryFile(delete=False, suffix='.wav') as tmpfile:
        with sd.InputStream(callback=callback, samplerate=samplerate, channels=1, dtype='float32'):
            sd.sleep(chunk_duration * 1000)  # Capture for a specified duration in milliseconds
            write(tmpfile.name, samplerate, (sd.rec(int(samplerate * chunk_duration), samplerate=samplerate, channels=1, dtype='float32') * 32767).astype(np.int16))

        # Process the captured audio chunk
        try:
            segments, _ = model.transcribe(tmpfile.name, language="en")  # Adjust language as needed
            text = " ".join([segment.text for segment in segments])
            print(f"Transcribed text: {text}")
        except Exception as e:
            print(f"Error during transcription: {str(e)}")

# Example of capturing and processing in a loop
while True:
    capture_and_process_chunk(chunk_duration=5)
