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
from flask_socketio import emit

app = Flask(__name__)
CORS(app, supports_credentials=True)  
# app.config['SECRET_KEY'] = 'your_secret_key'
socketio = SocketIO(app, cors_allowed_origins="*")

WEBHOOK_BASE_URL = "url"

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

# @app.route("/handle-call", methods=["POST"])
# def handle_call():
#     response = VoiceResponse()
#     response.say("Hello! How can I help you today?")
#     gather = Gather(input='speech', action=f'{WEBHOOK_BASE_URL}/process-speech', timeout=5)
#     response.append(gather)
#     return str(response)

@app.route("/handle-call", methods=["POST"])
def handle_call():
    response = VoiceResponse()
    # Get phone number from query param (passed in start_call)
    phone = request.args.get("phone", "YOUR_PHONE_NUMBER_HERE")  # Fallback to your number
    
    # Set the phone number in voicebot (assuming it uses a global 'phone' variable)
    from voicebot import phone as voicebot_phone
    global voicebot_phone
    voicebot_phone = phone
    
    # Get initial message from chat (identity verification)
    initial_message = chat()  # Calls your updated chat function with no input
    response.say(initial_message)  # Send to Twilio for voice
    
    # Emit the initial message to the frontend immediately
    socketio.emit('conversation_update', {
        "user": None,  # No user input yet
        "bot": initial_message,
        "latency_breakdown": {"total": 0}  # Minimal latency for initial message
    })
    
    gather = Gather(input='speech', action=f'{WEBHOOK_BASE_URL}/process-speech', timeout=5)
    response.append(gather)
    print("TwiML Response:", str(response))
    return str(response)

# @app.route("/process-speech", methods=["POST"])
# def process_speech():
#     response = VoiceResponse()
#     user_input = request.values.get("SpeechResult")
    
#     if user_input:
#         # Start total latency timer
#         total_start = time.time()

#         # 1. Transcription latency (Twilio speech-to-text already done by this point)
#         transcription_latency = 0.1  # Placeholder; Twilio doesn't expose this directly

#         # 2. LLM latency
#         llm_start = time.time()
#         bot_response = chat(user_input)  # Your LLM function
#         llm_latency = time.time() - llm_start

#         # 3. Voice latency (Preparing the Twilio say command)
#         voice_start = time.time()
#         response.say(bot_response)  # This is what Twilio uses to speak
#         voice_latency = time.time() - voice_start  # Time to prepare the TwiML say instruction

#         # 4. Telephony latency (Twilio overhead, estimate)
#         telephony_latency = 0.05  # Placeholder; estimate based on Twilio API

#         # 5. Platform latency (remaining overhead)
#         total_latency = time.time() - total_start
#         platform_latency = total_latency - (transcription_latency + llm_latency + voice_latency + telephony_latency)

#         # Prepare latency breakdown
#         latency_breakdown = {
#             "platform": platform_latency,
#             "voice": voice_latency,
#             "llm": llm_latency,
#             "transcription": transcription_latency,
#             "telephony": telephony_latency,
#             "total": total_latency
#         }

#         # Emit to frontend
#         socketio.emit('conversation_update', {
#             "user": user_input,
#             "bot": bot_response,
#             "latency_breakdown": latency_breakdown
#         })
#     else:
#         response.say("I didn't catch that. Could you please repeat?")
    
#     gather = Gather(input='speech', action=f'{WEBHOOK_BASE_URL}/process-speech', timeout=5)
#     response.append(gather)
    
#     return str(response)
# Middleware to measure total request time (for telephony approximation)
@app.before_request
def start_timer():
    request.start_time = time.time()

@app.route("/process-speech", methods=["POST"])
def process_speech():
    response = VoiceResponse()
    user_input = request.values.get("SpeechResult")
    if user_input:
        total_start = time.time()
        llm_start = time.time()
        bot_response = chat(user_input)
        llm_latency = time.time() - llm_start
        voice_start = time.time()
        response.say(bot_response)
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
        # Placeholder for email sending logic
        if "We’ll send you" in bot_response:
            print("Debug: Email sending triggered (implement actual logic here)")
    else:
        response.say("I didn't catch that. Could you please repeat?")
    gather = Gather(input='speech', action=f'{WEBHOOK_BASE_URL}/process-speech', timeout=7,
                    hints="yes, no, pay, rupees, 1000, 2000, 5000, 10000, balance, due, that's me, thanks, thats'all",
                    language="en-IN")
    response.append(gather)
    print("TwiML Response:", str(response))
    if user_input:
        print("Latency Breakdown:", latency_breakdown)
    return str(response)

if __name__ == "__main__":
    socketio.run(app, debug=True, allow_unsafe_werkzeug=True)  