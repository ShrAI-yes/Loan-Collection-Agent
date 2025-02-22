import os
import time
import torch
import numpy as np
import pyaudio
import speech_recognition as sr
import multiprocessing
from io import BytesIO
from gtts import gTTS
from pydub import AudioSegment
from pydub.playback import _play_with_simpleaudio
from langchain_mistralai import ChatMistralAI

llm = ChatMistralAI(
    model="mistral-large-latest",
    temperature=0,
    max_retries=100,
    api_key="6rnYo35pFqCbyLPo6hf4pndUOnGg62oP"
)

vad_model, utils = torch.hub.load('snakers4/silero-vad', 'silero_vad', trust_repo=True)
(get_speech_timestamps, _, _, _, _) = utils

# Audio setup
RATE = 16000
CHUNK = 1024
FORMAT = pyaudio.paInt16
CHANNELS = 1

p = pyaudio.PyAudio()
stream = p.open(format=FORMAT, channels=CHANNELS, rate=RATE, input=True, frames_per_buffer=CHUNK)

# Global flag for speech interruption
interrupt_flag = multiprocessing.Value("b", False)

def vad_check():
    """Detects if the user is speaking using Silero VAD."""
    audio_chunk = stream.read(CHUNK, exception_on_overflow=False)
    audio_tensor = torch.tensor(np.frombuffer(audio_chunk, dtype=np.int16), dtype=torch.float32) / 32768.0
    speech_timestamps = get_speech_timestamps(audio_tensor, vad_model, sampling_rate=RATE)
    return len(speech_timestamps) > 0  

def recognize_trigger_words():
    """Checks if user says stop words like 'stop', 'cancel', etc."""
    recognizer = sr.Recognizer()
    with sr.Microphone() as source:
        recognizer.adjust_for_ambient_noise(source)
        try:
            audio = recognizer.listen(source, timeout=1)
            user_input = recognizer.recognize_google(audio)
            stop_words = ["stop", "cancel", "exit", "shut up"]
            return any(word in user_input.lower() for word in stop_words)
        except (sr.UnknownValueError, sr.WaitTimeoutError):
            return False

def play_audio(text, interrupt_flag):
    """Plays speech and stops if interrupted."""
    tts = gTTS(text=text, lang="en")
    audio_path = "temp_audio.mp3"
    tts.save(audio_path)

    audio = AudioSegment.from_file(audio_path)
    player = _play_with_simpleaudio(audio)

    start_time = time.time()
    while time.time() - start_time < len(text) // 5:
        if vad_check() or recognize_trigger_words():
            print("User interrupted! Stopping speech...")
            interrupt_flag.value = True  
            player.stop()  
            break

    os.remove(audio_path)  

def speak_text(text):
    """Plays text using multiprocessing for real-time interruption."""
    global interrupt_flag
    interrupt_flag.value = False  
    audio_process = multiprocessing.Process(target=play_audio, args=(text, interrupt_flag))
    audio_process.start()
    audio_process.join()  

def recognize_speech(timeout=10):
    """Recognizes user speech and detects stop words."""
    recognizer = sr.Recognizer()
    with sr.Microphone() as source:
        recognizer.adjust_for_ambient_noise(source)
        print("Listening... Speak now.")
        try:
            audio = recognizer.listen(source, timeout=timeout)
            user_input = recognizer.recognize_google(audio)
            stop_words = ["stop", "cancel", "exit", "shut up"]
            return "stop" if any(word in user_input.lower() for word in stop_words) else user_input
        except (sr.UnknownValueError, sr.WaitTimeoutError):
            return "timeout"

def chatbot():
    """Main chatbot function with real-time interruption."""
    print("Assistant: Hello! How can I assist you today?")
    speak_text("Hello! How can I assist you today?")

    while True:
        user_query = recognize_speech(timeout=10)
        if user_query in ["timeout", "stop"]:
            print("User stopped or no response. Exiting chatbot.")
            break

        response = llm.predict(f"Answer this query: {user_query}")
        print(f'Bot: {response}')
        speak_text(response)  

    print("Session ended.")

if __name__ == "__main__":
    chatbot()
