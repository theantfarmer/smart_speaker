import boto3

def amazon_polly_tts(text, voice_id='Joanna', aws_access_key_id=None, aws_secret_access_key=None):
    if aws_access_key_id and aws_secret_access_key:
        polly_client = boto3.client('polly',
                                    aws_access_key_id=aws_access_key_id,
                                    aws_secret_access_key=aws_secret_access_key,
                                    region_name='us-east-1')  # or any other AWS region
    else:
        polly_client = boto3.client('polly')
    
    response = polly_client.synthesize_speech(VoiceId=voice_id,
                                              OutputFormat='mp3', 
                                              Text=text)
    
    audio_content = response['AudioStream'].read()
    return audio_content
