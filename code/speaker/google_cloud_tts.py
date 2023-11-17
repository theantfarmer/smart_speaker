from google.cloud import texttospeech
from google.oauth2 import service_account
from dont_tell import GOOGLE_CLOUD_CREDENTIALS  # Make sure this import works as expected

# Initialize credentials globally so that you can use it in google_cloud_tts function
global_credentials = service_account.Credentials.from_service_account_info(GOOGLE_CLOUD_CREDENTIALS)

# Google-specific function
def google_cloud_tts(text, pitch=0.0, credentials=global_credentials):
    # Use the passed credentials or the global one if None is passed
    if credentials is None:
        credentials = global_credentials
    
    # Initialize TextToSpeechClient
    client = texttospeech.TextToSpeechClient(credentials=credentials)
    
    # Set input text
    input_text = texttospeech.SynthesisInput(text=text)
    
    # Choose a voice
    voice = texttospeech.VoiceSelectionParams(
        language_code='en-GB',
        name='en-GB-Standard-f',
    )
    
    # Configure audio settings
    audio_config = texttospeech.AudioConfig(
        audio_encoding=texttospeech.AudioEncoding.MP3,
        pitch=pitch
    )
    
    # Call Google Text-to-Speech API
    response = client.synthesize_speech(input=input_text, voice=voice, audio_config=audio_config)
    
    return response.audio_content
