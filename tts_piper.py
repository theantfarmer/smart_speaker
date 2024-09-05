import subprocess
import io
from pydub import AudioSegment
import threading

def tts_model(text, model='en_GB-jenny_dioco-medium'):
    # Create a thread-safe buffer to store the audio data
    audio_buffer = io.BytesIO()

    def process_tts():
        # Prepare the command to run Piper and output raw audio
        command = f"echo '{text}' | piper --model {model} --output-raw"

        try:
            # Capture the raw audio output of Piper
            raw_audio = subprocess.check_output(command, shell=True)

            # Convert raw audio to WAV using PyDub
            audio = AudioSegment.from_raw(io.BytesIO(raw_audio), sample_width=2, frame_rate=22050, channels=1)

            # Export to WAV
            audio.export(audio_buffer, format='wav')

        except subprocess.CalledProcessError as e:
            print(f"Error occurred: {e}")

    # Create a new thread for TTS processing
    thread = threading.Thread(target=process_tts)
    thread.start()

    # Wait for the thread to complete
    thread.join()

    # Get the audio data from the buffer
    audio_data = audio_buffer.getvalue()

    # Return the audio data
    return audio_data