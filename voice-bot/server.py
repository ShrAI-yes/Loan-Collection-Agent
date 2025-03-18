# THIS SCRIPT IS THE MAIN SERVER SCRIPT WHICH CONNECTS WITH TWILIO AS WELL AS VOICEBOT.PY

import time
import os
from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
from flask_socketio import SocketIO
from twilio.rest import Client
from twilio.twiml.voice_response import VoiceResponse, Gather
from elevenlabs.client import ElevenLabs
from elevenlabs import save
from dotenv import load_dotenv
from voicebot import chat, phone as voicebot_phone
from collections import defaultdict
from flask_socketio import emit

app = Flask(__name__)
CORS(app, supports_credentials=True)  
# app.config['SECRET_KEY'] = 'your_secret_key'
socketio = SocketIO(app, cors_allowed_origins="*")

WEBHOOK_BASE_URL = "your_ngrok_url"  # e.g., "https://abcd1234.ngrok.io"

load_dotenv()
TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_PHONE = os.getenv("TWILIO_PHONE")

if not all([TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_PHONE]):
    raise ValueError("Missing required Twilio environment variables")

try:
    client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
    client.api.accounts(TWILIO_ACCOUNT_SID).fetch()
    print("Twilio credentials verified successfully")
except Exception as e:
    print(f"Failed to initialize Twilio client: {str(e)}")
    raise

elevenlabs_client = ElevenLabs(api_key="your_elevenlabs_api_key")
call_state = {}

def text_to_speech(text, language="en"):
    """Convert text to speech using ElevenLabs and return the audio file path."""
    audio_file = "response.mp3"
    if os.path.exists(audio_file):
        os.remove(audio_file)
    
    # voice: Hindi
    if language == "hi":
        audio = elevenlabs_client.text_to_speech.convert(
            text=text,
            voice_id="50YSQEDPA2vlOxhCseP4",  # Hindi voice
            model_id="eleven_flash_v2_5",
            output_format="mp3_44100_128"
        )
    else:  # voice: English
        audio = elevenlabs_client.text_to_speech.convert(
            text=text,
            voice_id="90ipbRoKi4CpHXvKVtl0",  # English voice
            model_id="eleven_flash_v2_5",
            output_format="mp3_44100_128"
        )
    
    save(audio, audio_file)
    return audio_file

@socketio.on('connect')
def handle_connect():
    print("Client connected")
    socketio.emit('connected', {'status': 'connected'})

@socketio.on('start_call')
def start_call(data):
    try:
        borrower_phone = data.get("phone")
        language = data.get("language", "en")
        
        if not borrower_phone:
            socketio.emit('error', {"message": "Missing 'phone' field"})
            return
        
        print(f"Initiating call to {borrower_phone} in {language}")
        
        call = client.calls.create(
            url=f"{WEBHOOK_BASE_URL}/handle-call",
            to=borrower_phone,
            from_=TWILIO_PHONE,
            status_callback=f"{WEBHOOK_BASE_URL}/call-status",
            status_callback_event=['initiated', 'ringing', 'answered', 'completed']
        )

        #storing the phone and language in call_state using the call SID
        call_state[call.sid] = {"phone": borrower_phone, "language": language}

        socketio.emit('call_status', {"status": "initiated", "call_sid": call.sid})
    except Exception as e:
        print(f"Error starting call: {str(e)}")
        socketio.emit('error', {"message": str(e)})


call_status_tracker = defaultdict(str) 

@app.route("/call-status", methods=['POST'])
def call_status():
    call_sid = request.form.get("CallSid")
    call_status = request.form.get("CallStatus")
    if call_status_tracker[call_sid] == call_status:
        return "", 200
    call_status_tracker[call_sid] = call_status
    print(f"Call {call_sid} status: {call_status}")
    socketio.emit('call_status', {"call_sid": call_sid, "status": call_status})
    #cleaning up call_state when call is completed
    if call_status == "completed" and call_sid in call_state:
        del call_state[call_sid]
    return "", 200

@app.route("/handle-call", methods=["POST"])
def handle_call():
    response = VoiceResponse()
    call_sid = request.form.get("CallSid")
    
    #retrieve phone and language from call_state
    state = call_state.get(call_sid, {"phone": "9324082517", "language": "en"})
    phone = state["phone"]
    language = state["language"]
    
    global voicebot_phone
    voicebot_phone = phone
    initial_message = chat(lang=language)
    audio_file = text_to_speech(initial_message, language)
    response.play(f"{WEBHOOK_BASE_URL}/serve-audio/{os.path.basename(audio_file)}")
    socketio.emit('conversation_update', {
        "user": None,
        "bot": initial_message,
        "latency_breakdown": {"total": 0}
    })
    
    gather = Gather(input='speech', action=f'{WEBHOOK_BASE_URL}/process-speech', timeout=5, language="hi-IN" if language == "hi" else "en-IN")
    response.append(gather)
    print("TwiML Response:", str(response))
    return str(response)

@app.route("/serve-audio/<filename>", methods=["GET"])
def serve_audio(filename):
    #serving the generated audio file
    return send_file(filename, mimetype="audio/mpeg")

@app.before_request
def start_timer():
    request.start_time = time.time()

@app.route("/process-speech", methods=["POST"])
def process_speech():
    response = VoiceResponse()
    call_sid = request.form.get("CallSid")
    user_input = request.values.get("SpeechResult")
    
    #retrieve phone and language from call_state
    state = call_state.get(call_sid, {"phone": "9324082517", "language": "en"})
    phone = state["phone"]
    language = state["language"]
    
    if user_input:
        total_start = time.time()
        llm_start = time.time()
        bot_response = chat(user_input, lang=language)  
        llm_latency = time.time() - llm_start
        voice_start = time.time()
        audio_file = text_to_speech(bot_response, language)
        response.play(f"{WEBHOOK_BASE_URL}/serve-audio/{os.path.basename(audio_file)}")
        voice_latency = time.time() - voice_start
        transcription_latency = 0.0
        telephony_start = request.start_time
        telephony_latency = total_start - telephony_start
        total_latency = time.time() - total_start
        platform_latency = total_latency - (llm_latency + voice_latency)
        latency_breakdown = {
            "platform": platform_latency,
            "voice": voice_latency,
            "llm": llm_latency,
            "transcription": transcription_latency,
            "telephony": telephony_latency,
            "total": total_latency + telephony_latency
        }
        socketio.emit('conversation_update', {
            "user": user_input,
            "bot": bot_response,
            "latency_breakdown": latency_breakdown
        })
        if "We’ll send you" in bot_response or "हम आपको" in bot_response:
            print("Debug: Email sending triggered (implement actual logic here)")
    else:
        no_input_msg = "I didn't catch that. Could you please repeat?" if language == "en" else "मुझे समझ नहीं आया। कृपया दोहराएं।"
        audio_file = text_to_speech(no_input_msg, language)
        response.play(f"{WEBHOOK_BASE_URL}/serve-audio/{os.path.basename(audio_file)}")
    
    gather = Gather(input='speech', action=f'{WEBHOOK_BASE_URL}/process-speech?phone={phone}&language={language}', timeout=10,
                    hints="yes, no, pay, rupees, हाँ, नहीं, भुगतान, रुपये" if language == "hi" else "yes, no, pay, rupees, 1000, 2000, 5000, 10000, balance, due, funds, money",
                    language="hi-IN" if language == "hi" else "en-IN")
    response.append(gather)
    print("TwiML Response:", str(response))
    if user_input:
        print("Latency Breakdown:", latency_breakdown)
    return str(response)

if __name__ == "__main__":
    socketio.run(app, debug=True, allow_unsafe_werkzeug=True)  


