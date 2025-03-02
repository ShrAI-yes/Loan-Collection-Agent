import torch
import sounddevice as sd
from langdetect import detect
from TTS.api import TTS


class Text2Speech:
    def __init__(self):
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.tts = TTS("tts_models/multilingual/multi-dataset/xtts_v2").to(self.device)
        self.voice = './voices/Indian_Accent.wav'

    def speak(self, text):
        lang = detect(text)
        if lang not in ['en','hi']:
            lang = 'en'
        wav = self.tts.tts(text=text, speaker_wav=self.voice, language=lang)
        sample_rate = self.tts.synthesizer.output_sample_rate
        sd.play(wav, sample_rate)
        sd.wait()