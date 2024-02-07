import sounddevice as sd
import numpy as np
from scipy.io import wavfile
from faster_whisper import WhisperModel
import logging

# Logging configuration
logging.basicConfig()
logging.getLogger("faster_whisper").setLevel(logging.INFO)

# Configuration for Whisper Model
model_size = "small.en"  # Adjust according to your needs
model = WhisperModel(model_size, device="cpu", compute_type="int8")

# Define volume_levels as a global variable
volume_levels = []

def sound_level_callback(indata, frames, time, status):
    global volume_levels  # Declare global inside the function
    volume_norm = np.linalg.norm(indata) * 10
    volume_levels.append(volume_norm)

def capture_speech(filename="audio.wav", threshold=0.5, timeout=5):
    global volume_levels

    with sd.InputStream(callback=sound_level_callback):
        print("Listening for speech...")
        while True:
            if len(volume_levels) > 0 and max(volume_levels) >= threshold:
                volume_levels.clear()
                break

    # Capture the audio
    audio = sd.rec(int(timeout * 16000), samplerate=16000, channels=1)
    sd.wait()

    # Normalize and save the audio to a file
    audio_normalized = np.int16(audio / np.max(np.abs(audio)) * 32767)
    wavfile.write(filename, 16000, audio_normalized)

    try:
        # Transcribe the audio file
        segments, info = model.transcribe(filename)
        transcription = ' '.join([segment.text for segment in segments])
        print("Detected language '%s' with probability %f" % (info.language, info.language_probability))
        return transcription, None
    except Exception as e:
        return None, str(e)

def main():
    print("Please say something...")
    capture_speech()

if __name__ == "__main__":
    main()
