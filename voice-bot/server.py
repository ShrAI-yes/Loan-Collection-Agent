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
from voicebot import chat
from collections import defaultdict
from flask_socketio import emit
import requests
from context_manager import Database
from gtts import gTTS

conversation_history = defaultdict(list)  
WHATSAPP_API_URL="http://localhost:8000/send-summary"

app = Flask(__name__)
CORS(app, supports_credentials=True)  
socketio = SocketIO(app, cors_allowed_origins="*")

WEBHOOK_BASE_URL = "https://5394-103-185-11-231.ngrok-free.app" 

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

# elevenlabs_client = ElevenLabs(api_key="sk_55f902c5ef7dddd7a65066aba188870ebb3da4610f7d373a")
call_state = {}
db = Database()  

def text_to_speech(text, language="en"):
    audio_file = "response.mp3"
    if os.path.exists(audio_file):
        os.remove(audio_file)
    tts = gTTS(text=text, lang=language, tld="co.uk" if language == "en" else "co.in")  # 'co.in' for Hindi, 'co.uk' for English
    tts.save(audio_file)
    return audio_file

# def text_to_speech(text, language="en"):
#     audio_file = "response.mp3"
#     if os.path.exists(audio_file):
#         os.remove(audio_file)
    
#     # voice: Hindi
#     if language == "hi":
#         audio = elevenlabs_client.text_to_speech.convert(
#             text=text,
#             voice_id="50YSQEDPA2vlOxhCseP4",  # Hindi voice
#             model_id="eleven_flash_v2_5",
#             output_format="mp3_44100_128"
#         )
#     else:  # voice: English
#         audio = elevenlabs_client.text_to_speech.convert(
#             text=text,
#             voice_id="90ipbRoKi4CpHXvKVtl0",  # English voice
#             model_id="eleven_flash_v2_5",
#             output_format="mp3_44100_128"
#         )
    
#     save(audio, audio_file)
#     return audio_file

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
    
    if call_status == "completed" and call_sid in call_state:
        state = call_state[call_sid]
        phone = state["phone"]
        language = state["language"]
        history = conversation_history.get(call_sid, [])
        
        if history:
            #Initialize Firestore document
            ref = db.init_user(phone)
            
            #Prepare summary for WhatsApp
            summary = "Hello! We just had a call with you! The following is the transcript or conversation summary:\n" if language == "en" else "बातचीत का सारांश:\n"
            for entry in history:
                summary += f"User: {entry['user']}\nBot: {entry['bot']}\n\n"
                #Save to Firestore
                db.add_convo(ref, "voice", db.payload("User", entry['user'], time.ctime()))
                db.add_convo(ref, "voice", db.payload("Bot", entry['bot'], time.ctime()))
        
            #Send WhatsApp summary
            try:
                response = requests.post(WHATSAPP_API_URL, json={
                    "phone_number": phone,
                    "message": summary
                })
                if response.status_code == 200:
                    print(f"Sent WhatsApp summary to {phone}")
                    #Store the summary in whatsapp_messages
                    db.add_convo(ref, "whatsapp", db.payload("Bot", summary, time.ctime()))
                else:
                    print(f"Failed to send WhatsApp summary: HTTP {response.status_code}")
            except Exception as e:
                print(f"Failed to send WhatsApp summary: {str(e)}")
        
        del call_state[call_sid]
        if call_sid in conversation_history:
            del conversation_history[call_sid]
    
    return "", 200

@app.route("/handle-call", methods=["POST"])
def handle_call():
    response = VoiceResponse()
    call_sid = request.form.get("CallSid")
    state = call_state.get(call_sid, {"phone": "9324082517", "language": "en"})
    phone = state["phone"]
    language = state["language"]
    
    print(f"Handling call for phone: {phone}")  
    initial_message = chat(lang=language, phone=phone)  
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
    return send_file(filename, mimetype="audio/mpeg")

@app.before_request
def start_timer():
    request.start_time = time.time()

@app.route("/process-speech", methods=["POST"])
def process_speech():
    response = VoiceResponse()
    call_sid = request.form.get("CallSid")
    user_input = request.values.get("SpeechResult")
    state = call_state.get(call_sid, {"phone": "9324082517", "language": "en"})
    phone = state["phone"]
    language = state["language"]
    
    if user_input:
        total_start = time.time()
        llm_start = time.time()
        bot_response = chat(user_input, lang=language, phone=phone)  # Pass phone explicitly
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
        conversation_history[call_sid].append({
            "user": user_input,
            "bot": bot_response
        })
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


