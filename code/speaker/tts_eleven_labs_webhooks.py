import requests
import json
from dont_tell import ELEVEN_LABS_KEY

def tts_eleven_labs(text, model_id='WsHLrEi4hVFr5gMgQuii'):
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{model_id}"


    headers = {
        "Accept": "audio/mpeg",
        "Content-Type": "application/json",
        "xi-api-key": xi_api_key,
        "Authorization": f"Bearer {authorization_token}"
    }

    data = {
        "text": text,
        "voice_settings": {
            "stability": 0.5,
            "similarity_boost": 0.5
        },
        "generation_config": {
            "chunk_length_schedule": []
        },
        
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