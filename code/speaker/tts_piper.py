import subprocess
import io
from pydub import AudioSegment




def tts_piper(text, model='en_GB-jenny_dioco-medium'):
    # Prepare the command to run Piper and output raw audio
    command = f"echo '{text}' | piper --model {model} --output-raw"
    try:
        # Capture the raw audio output of Piper
        raw_audio = subprocess.check_output(command, shell=True)

        # Convert raw audio to WAV using PyDub
        audio = AudioSegment.from_raw(io.BytesIO(raw_audio), sample_width=2, frame_rate=22050, channels=1)

        # Export to WAV
        wav_buffer = io.BytesIO()
        audio.export(wav_buffer, format='wav')
        return wav_buffer.getvalue()
    except subprocess.CalledProcessError as e:
        print(f"Error occurred: {e}")
        return None
