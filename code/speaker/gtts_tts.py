from gtts import gTTS
import tempfile
import os

def gtts_tts(text, pitch=-5.0, credentials=None):
    tts = gTTS(text=text, lang='en')
    
    # Create a temporary file to store audio
    with tempfile.NamedTemporaryFile(delete=True) as fp:
        temp_path = f"{fp.name}.mp3"
        
    # Save the audio file
    tts.save(temp_path)
    
    # Read the audio file
    with open(temp_path, "rb") as f:
        audio_content = f.read()
        
    # Remove the temporary file
    os.remove(temp_path)

    return audio_content
