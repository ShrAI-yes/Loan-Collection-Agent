import elevenlabs
from elevenlabs.client import ElevenLabs
from elevenlabs import save

client = ElevenLabs(
  api_key='sk_40c80ce0ef655ee28ac1bc190b7999023623fe3898525957'
)

#Only pass hindi text in this function
def hi_tts(text):
    audio = client.text_to_speech.convert(
        text=text,
        voice_id="mfMM3ijQgz8QtMeKifko",
        model_id="eleven_multilingual_v2",
        output_format="mp3_44100_128",
    )
    elevenlabs.save(audio, 'response.mp3')

#Only pass english text in this function
def en_text(text):
    audio = client.text_to_speech.convert(
        text=text,
        voice_id="GHKbgpqchXOxta6X2lSd",
        model_id="eleven_multilingual_v2",
        output_format="mp3_44100_128",
    )
    elevenlabs.save(audio, 'response.mp3')