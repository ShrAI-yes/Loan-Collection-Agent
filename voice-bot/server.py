import time
import os
from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
from flask_socketio import SocketIO, emit
from twilio.rest import Client
from twilio.twiml.voice_response import VoiceResponse, Gather
from dotenv import load_dotenv
# from voicebot import chat
from context_manager import Database
from gtts import gTTS
import pandas as pd
import requests
from agent import Agent

app = Flask(__name__)
CORS(app, supports_credentials=True)
socketio = SocketIO(app, cors_allowed_origins="*")

load_dotenv()
TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_PHONE_NUMBER = os.getenv("TWILIO_PHONE")
WHATSAPP_API_URL = "http://localhost:8000/send-summary"
WEBHOOK_BASE_URL = "https://fdf5-103-185-11-75.ngrok-free.app"
MAX_UNRESPONDED_ATTEMPTS = 2
RETRY_DELAY_SECONDS = 120 # 2 minute

if not all([TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_PHONE_NUMBER]):
    raise ValueError("Missing required Twilio environment variables")

try:
    client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
    client.api.accounts(TWILIO_ACCOUNT_SID).fetch()
    print("Twilio credentials verified successfully")
except Exception as e:
    print(f"Failed to initialize Twilio client: {str(e)}")
    raise

db = Database()
call_state = {}
call_status_tracker = {}
conversation_history = {}  # {phone: [{sender: "Bot"/"User", text: "...", time: timestamp}]}
last_read_time = {}  # {phone: timestamp}
whatsapp_engaged = {}  # {phone: bool}
borrowers_data = []

def text_to_speech(text, language="en"):
    audio_file = "response.mp3"
    if os.path.exists(audio_file):
        os.remove(audio_file)
    tts = gTTS(text=text, lang=language, tld="co.uk" if language == "en" else "co.in")
    tts.save(audio_file)
    return audio_file

@socketio.on('connect')
def handle_connect():
    print("Client connected")
    emit('connected', {'status': 'connected'})

@app.route("/upload-csv", methods=["POST"])
def upload_csv():
    global borrowers_data
    if "file" not in request.files:
        return jsonify({"error": "No file part"}), 400
    file = request.files["file"]
    if file.filename == "":
        return jsonify({"error": "No selected file"}), 400
    if file and file.filename.endswith(".csv"):
        df = pd.read_csv(file)
        borrowers_data = df.to_dict(orient="records")
        socketio.emit("borrowers_update", {"borrowers": borrowers_data})
        return jsonify({"borrowers": borrowers_data}), 200
    return jsonify({"error": "Invalid file format"}), 400

def initiate_call(phone, borrower):
    ref = db.init_user(phone)
    try:
        call = client.calls.create(
            to=f"+{phone}",
            from_=TWILIO_PHONE_NUMBER,
            url=f"{WEBHOOK_BASE_URL}/handle-call",
            status_callback=f"{WEBHOOK_BASE_URL}/call-status",
            status_callback_event=["initiated", "ringing", "answered", "completed", "no-answer", "failed"]
        )
        call_state[call.sid] = {"phone": f"+{phone}", "language": "en", "borrower": borrower, "ref": ref, "init_time": time.time()}
        print(f"Initiating call to +{phone} (SID: {call.sid})")
        socketio.emit("call_status", {"phone": phone, "status": "initiated"})
    except Exception as e:
        print(f"Call initiation failed for {phone}: {str(e)}")
        socketio.emit("call_status", {"phone": phone, "status": "failed"})
        db.increment_attempts(ref, "voice")
        handle_retry(phone, "voice", borrower, ref)

# def initiate_whatsapp(phone, borrower):
#     ref = db.init_user(phone)
#     summary = f"Hello {borrower.get('F_Name', 'Customer')}! Your balance of Rs. {borrower.get('Current_balance', 0)} is due by {borrower.get('Date_of_last_payment', 'N/A')}. Please confirm when you can pay."
#     try:
#         response = requests.post(WHATSAPP_API_URL, json={
#             "phone_number": f"+{phone}",
#             "message": summary
#         })
#         if response.status_code == 200:
#             db.add_convo(ref, "message", db.payload("Bot", summary, time.ctime()))
#             print(f"Sent WhatsApp message to +{phone}: {summary}")
#             socketio.emit("whatsapp_status", {"phone": phone, "status": "sent", "sender": "Bot", "message": summary})
#             conversation_history.setdefault(phone, []).append({
#                 "sender": "Bot",
#                 "text": summary,
#                 "time": time.ctime()
#             })
#         else:
#             print(f"Failed to send WhatsApp message to +{phone}")
#             socketio.emit("whatsapp_status", {"phone": phone, "status": "Failed to send"})
#             db.increment_attempts(ref, "message")
#             handle_retry(phone, "message", borrower, ref)
#     except Exception as e:
#         print(f"WhatsApp message failed for {phone}: {str(e)}")
#         socketio.emit("whatsapp_status", {"phone": phone, "status": "Failed"})
#         db.increment_attempts(ref, "message")
#         handle_retry(phone, "message", borrower, ref)
def initiate_whatsapp(phone, borrower):
    ref = db.init_user(phone)
    try:
        agent = Agent(phone=phone)
        print(f"Agent initialized for {phone}: {agent.user}")
        initial_message = agent.chat("")
        print(f"Generated initial WhatsApp message for +{phone}: {initial_message}")
        response = requests.post(WHATSAPP_API_URL, json={
            "phone_number": f"+{phone}",
            "message": initial_message
        })
        if response.status_code == 200:
            db.add_convo(ref, "message", db.payload("Bot", initial_message, time.ctime()))
            print(f"Sent WhatsApp message to +{phone}: {initial_message}")
            socketio.emit("whatsapp_status", {
                "phone": phone,
                "status": "sent",
                "sender": "Bot",
                "message": initial_message
            })
            conversation_history.setdefault(phone, []).append({
                "sender": "Bot",
                "text": initial_message,
                "time": time.ctime()
            })
            return True
        else:
            print(f"Failed to send WhatsApp message to +{phone}: {response.text}")
            socketio.emit("whatsapp_status", {"phone": phone, "status": "failed", "error": response.text})
            raise Exception(f"WhatsApp API failed: {response.text}")
    except Exception as e:
        print(f"WhatsApp message failed for {phone}: {str(e)}")
        socketio.emit("whatsapp_status", {"phone": phone, "status": "failed", "error": str(e)})
        db.increment_attempts(ref, "message")
        handle_retry(phone, "message", borrower, ref)
        return False

def handle_retry(phone, channel, borrower, ref):
    if whatsapp_engaged.get(phone, False):
        print(f"Skipping retry for {phone}: User engaged on WhatsApp")
        return
    attempts = db.get_attempts(ref, channel)
    print(f"Handling retry for {phone} on {channel}: {attempts}/{MAX_UNRESPONDED_ATTEMPTS}")
    if attempts < MAX_UNRESPONDED_ATTEMPTS:
        if channel == "message":
            last_time = last_read_time.get(phone, 0)
            if time.time() - last_time < RETRY_DELAY_SECONDS:
                print(f"Skipping retry for {phone}: replied within {RETRY_DELAY_SECONDS}s")
                return
        time.sleep(5)
        if channel == "voice":
            initiate_call(phone, borrower)
        elif channel == "message":
            initiate_whatsapp(phone, borrower)
    elif attempts >= MAX_UNRESPONDED_ATTEMPTS:
        alternate_channel = "message" if channel == "voice" else "voice"
        print(f"Attempting switch to {alternate_channel} for {phone} after {attempts} unresponded {channel} attempts")
        if alternate_channel == "voice" and whatsapp_engaged.get(phone, False):
            print(f"Blocked switch to voice for {phone}: User engaged on WhatsApp")
            return
        db.reset_attempts(ref, alternate_channel)
        if alternate_channel == "voice":
            initiate_call(phone, borrower)
        elif alternate_channel == "message":
            initiate_whatsapp(phone, borrower)

@socketio.on("start_campaign")
def start_campaign(data):
    global borrowers_data
    borrowers = data["borrowers"]
    borrower = borrowers[0]
    phone = str(borrower["Mobile_No"])
    borrowers_data = borrowers
    channel = borrower.get("Channel_Preference", "voice").lower()
    
    ref = db.init_user(phone)
    db.reset_attempts(ref, channel)
    
    emit("campaign_status", {"phone": phone, "status": "Running"})
    if channel == "voice":
        initiate_call(phone, borrower)
    elif channel == "message":
        initiate_whatsapp(phone, borrower)

@app.route("/handle-call", methods=["POST"])
def handle_call():
    response = VoiceResponse()
    call_sid = request.form.get("CallSid")
    state = call_state.get(call_sid, {"phone": "9324082517", "language": "en"})
    phone = state["phone"]
    language = state["language"]
    
    initial_message = chat(lang=language, phone=phone[1:])
    audio_file = text_to_speech(initial_message, language)
    response.play(f"{WEBHOOK_BASE_URL}/serve-audio/{os.path.basename(audio_file)}")
    socketio.emit('conversation_update', {
        "phone": phone[1:],
        "sender": "Bot",
        "text": initial_message,
        "time": time.ctime()
    })
    conversation_history.setdefault(phone[1:], []).append({
        "sender": "Bot",
        "text": initial_message,
        "time": time.ctime()
    })
    gather = Gather(input='speech', action=f'{WEBHOOK_BASE_URL}/process-speech', timeout=5, language="hi-IN" if language == "hi" else "en-IN")
    response.append(gather)
    return str(response)

@app.route("/call-status", methods=['POST'])
def call_status():
    call_sid = request.form.get("CallSid")
    call_status = request.form.get("CallStatus")
    print(f"Received call status for {call_sid}: {call_status}")
    if call_status_tracker.get(call_sid) == call_status:
        return "", 200
    call_status_tracker[call_sid] = call_status
    if call_sid not in call_state:
        print(f"Unknown call SID: {call_sid}")
        return "", 200
    phone = call_state[call_sid]["phone"][1:]
    borrower = call_state[call_sid]["borrower"]
    ref = call_state[call_sid]["ref"]
    print(f"Call {call_sid} status: {call_status} for {phone}")
    socketio.emit('call_status', {"phone": phone, "status": call_status})
    
    if call_status in ["no-answer", "failed"]:
        db.increment_attempts(ref, "voice")
        handle_retry(phone, "voice", borrower, ref)
    elif call_status in ["completed"]:
        del call_state[call_sid]
    
    return "", 200

@app.route("/process-whatsapp-message", methods=["POST"])
def process_whatsapp_message():
    data = request.json
    phone = data.get("phone_number")
    user_query = data.get("user_query")
    try:
        socketio.emit("whatsapp_status", {
            "phone": phone,
            "status": "received",
            "sender": "User",
            "message": user_query
        })
        print(f"Emitted whatsapp_status for User: {phone}, message: {user_query}")
        
        agent = Agent(phone=phone)
        response = agent.chat(user_query)
        ref = db.init_user(phone)
        db.add_convo(ref, "message", db.payload("User", user_query, time.ctime()))
        db.add_convo(ref, "message", db.payload("Bot", response, time.ctime()))
        whatsapp_engaged[phone] = True
        socketio.emit("whatsapp_status", {
            "phone": phone,
            "status": "sent",
            "sender": "Bot",
            "message": response
        })
        print(f"Emitted whatsapp_status for Bot: {phone}, message: {response}")
        conversation_history.setdefault(phone, []).append({
            "sender": "User",
            "text": user_query,
            "time": time.ctime()
        })
        conversation_history[phone].append({
            "sender": "Bot",
            "text": response,
            "time": time.ctime()
        })
        return jsonify({"response": response}), 200
    except Exception as e:
        print(f"Error processing WhatsApp message for {phone}: {str(e)}")
        socketio.emit("whatsapp_status", {
            "phone": phone,
            "status": "failed",
            "sender": "Bot",
            "error": str(e)
        })
        return jsonify({"error": str(e)}), 500

@app.route("/update-whatsapp-status", methods=['POST'])
def update_whatsapp_status():
    global borrowers_data
    data = request.json
    phone = data["phone"]
    status = data["status"]
    ref = db.init_user(phone)
    print(f"WhatsApp status update for {phone}: {status}")
    socketio.emit("whatsapp_status", {"phone": phone, "status": status})
    if status == "read" and borrowers_data:
        last_read_time[phone] = time.time()
        db.increment_attempts(ref, "message")
        for b in borrowers_data:
            if str(b["Mobile_No"]) == phone:
                handle_retry(phone, "message", b, ref)
                break
    return jsonify({"success": True}), 200

@app.route("/get-attempts/<phone>", methods=["GET"])
def get_attempts(phone):
    ref = db.init_user(phone)
    attempts = {
        "voice_attempts": db.get_attempts(ref, "voice"),
        "message_attempts": db.get_attempts(ref, "message")
    }
    print(f"Serving attempts for {phone}: {attempts}")
    return jsonify(attempts), 200

@app.route("/serve-audio/<filename>", methods=["GET"])
def serve_audio(filename):
    return send_file(filename, mimetype="audio/mpeg")

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
        bot_response = chat(user_input, lang=language, phone=phone[1:])
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
        socketio.emit('conversation_update', {
            "phone": phone[1:],
            "sender": "User",
            "text": user_input,
            "time": time.ctime()
        })
        print(f"Emitted conversation_update for User: {phone[1:]}, message: {user_input}")
        socketio.emit('conversation_update', {
            "phone": phone[1:],
            "sender": "Bot",
            "text": bot_response,
            "time": time.ctime()
        })
        print(f"Emitted conversation_update for Bot: {phone[1:]}, message: {bot_response}")
        conversation_history.setdefault(phone[1:], []).append({
            "sender": "User",
            "text": user_input,
            "time": time.ctime()
        })
        conversation_history[phone[1:]].append({
            "sender": "Bot",
            "text": bot_response,
            "time": time.ctime()
        })
        print("Latency Breakdown:", {
            "platform": platform_latency,
            "voice": voice_latency,
            "llm": llm_latency,
            "transcription": transcription_latency,
            "telephony": telephony_latency,
            "total": total_latency + telephony_latency
        })
    else:
        no_input_msg = "I didn't catch that. Could you please repeat?" if language == "en" else "मुझे समझ नहीं आया। कृपया दोहराएं।"
        audio_file = text_to_speech(no_input_msg, language)
        response.play(f"{WEBHOOK_BASE_URL}/serve-audio/{os.path.basename(audio_file)}")
        socketio.emit('conversation_update', {
            "phone": phone[1:],
            "sender": "Bot",
            "text": no_input_msg,
            "time": time.ctime()
        })
        print(f"Emitted conversation_update for Bot: {phone[1:]}, message: {no_input_msg}")
        conversation_history.setdefault(phone[1:], []).append({
            "sender": "Bot",
            "text": no_input_msg,
            "time": time.ctime()
        })
    
    gather = Gather(input='speech', action=f'{WEBHOOK_BASE_URL}/process-speech?phone={phone}&language={language}', timeout=10,
                    hints="yes, no, pay, rupees, हाँ, नहीं, भुगतान, रुपये" if language == "hi" else "yes, no, pay, rupees, 1000, 2000, 5000, 10000, balance, due, funds, money",
                    language="hi-IN" if language == "hi" else "en-IN")
    response.append(gather)
    print("TwiML Response:", str(response))
    return str(response)

@app.before_request
def start_timer():
    request.start_time = time.time()

if __name__ == "__main__":
    socketio.run(app, debug=True, allow_unsafe_werkzeug=True)