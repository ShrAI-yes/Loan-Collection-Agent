import time
import os
from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
from flask_socketio import SocketIO
from twilio.rest import Client
from twilio.twiml.voice_response import VoiceResponse, Gather
from dotenv import load_dotenv
from voicebot import chat, text_to_speech
from collections import defaultdict

app = Flask(__name__)
CORS(app, supports_credentials=True)  
# app.config['SECRET_KEY'] = 'your_secret_key'
socketio = SocketIO(app, cors_allowed_origins="*")

WEBHOOK_BASE_URL = "YOUR_NGROK_URL"

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

# log_file = "conversation_log.txt"
# if not os.path.exists(log_file):
#     with open(log_file, "w") as f:
#         f.write("Chat Log:\n")

# def log_conversation(user_input, response, latency):
#     with open(log_file, "a") as f:
#         f.write(f"User: {user_input}\n")
#         f.write(f"Bot: {response}\n")
#         f.write(f"Response Time: {latency:.3f} seconds\n\n")

# @app.route("/download-log", methods=["GET"])
# def download_log():
#     return send_file(log_file, as_attachment=True)

@socketio.on('connect')
def handle_connect():
    print("Client connected")
    socketio.emit('connected', {'status': 'connected'})

@socketio.on('start_call')
def start_call(data):
    try:
        borrower_phone = data.get("phone")
        language = data.get("language", "English")
        
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
        return "", 200  #ignoring duplicate status updates
    call_status_tracker[call_sid] = call_status 
    print(f"Call {call_sid} status: {call_status}")
    socketio.emit('call_status', {"call_sid": call_sid, "status": call_status})
    return "", 200

@app.route("/handle-call", methods=["POST"])
def handle_call():
    response = VoiceResponse()
    response.say("Hello! How can I help you today?")
    gather = Gather(input='speech', action=f'{WEBHOOK_BASE_URL}/process-speech', timeout=5)
    response.append(gather)
    return str(response)

@app.route("/process-speech", methods=["POST"])
def process_speech():
    response = VoiceResponse()
    user_input = request.values.get("SpeechResult")
    if user_input:
        start_time = time.time()
        bot_response = chat(user_input)
        latency = time.time() - start_time
        response.say(bot_response)
        socketio.emit('conversation_update', {"user": user_input, "bot": bot_response, "latency": latency})
    else:
        response.say("I didn't catch that. Could you please repeat?")
    
    gather = Gather(input='speech', action=f'{WEBHOOK_BASE_URL}/process-speech', timeout=5)
    response.append(gather)
    return str(response)

if __name__ == "__main__":
    socketio.run(app, debug=True, allow_unsafe_werkzeug=True)  
