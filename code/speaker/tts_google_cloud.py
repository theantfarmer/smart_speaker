from google.cloud import texttospeech
from google.oauth2 import service_account
from dont_tell import GOOGLE_CLOUD_CREDENTIALS
 # Make sure this import works as expected

# Initialize credentials globally so that you can use it in google_cloud_tts function
global_credentials = service_account.Credentials.from_service_account_info(GOOGLE_CLOUD_CREDENTIALS)

# Google-specific function
def tts_google_cloud(text, credentials=global_credentials):
    if credentials is None:
        credentials = global_credentials

    client = texttospeech.TextToSpeechClient(credentials=credentials)
    input_text = texttospeech.SynthesisInput(text=text)
    voice = texttospeech.VoiceSelectionParams(
        language_code='en-GB',
        name='en-GB-Standard-f',
    )
    audio_config = texttospeech.AudioConfig(
        audio_encoding=texttospeech.AudioEncoding.MP3
    )
    response = client.synthesize_speech(input=input_text, voice=voice, audio_config=audio_config)
    return response.audio_content
    
    