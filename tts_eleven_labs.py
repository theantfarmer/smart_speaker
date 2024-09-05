import requests
import logging
import os
from dont_tell import ELEVEN_LABS_KEY


def tts_model(text, model_id='o9k0HV3UbuCBBTyV7oEG'):
    CHUNK_SIZE = 1024
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{model_id}"

    headers = {
        "Accept": "audio/mpeg",
        "Content-Type": "application/json",
        "xi-api-key": ELEVEN_LABS_KEY
    }

    data = {
        "text": text,
        "model_id": "eleven_monolingual_v1",  
        "voice_settings": {
            "stability": 0.9,
            "similarity_boost": 0.5
        }
    }

    try:
        response = requests.post(url, json=data, headers=headers)
        if response.status_code == 200:
            audio_content = response.content
            


            
            logging.info("TTS conversion successful.")
            return audio_content
        else:
            logging.error(f"Error in TTS conversion: {response.status_code}")
            logging.error(response.text)
            return None
    except Exception as e:
        logging.error(f"Exception in TTS service: {e}")
        return None