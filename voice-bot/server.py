import time
import os
from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
from flask_socketio import SocketIO, emit
from twilio.rest import Client
from twilio.twiml.voice_response import VoiceResponse, Gather
from dotenv import load_dotenv
from voicebot import chat
from context_manager import Database
from gtts import gTTS
import pandas as pd
import requests

app = Flask(__name__)
CORS(app, supports_credentials=True)
socketio = SocketIO(app, cors_allowed_origins="*")

load_dotenv()
TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_PHONE_NUMBER = os.getenv("TWILIO_PHONE")
WHATSAPP_API_URL = "http://localhost:8000/send-summary"
WEBHOOK_BASE_URL = "https://0110-103-48-101-59.ngrok-free.app"  # Confirm this is current
MAX_UNRESPONDED_ATTEMPTS = 2

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
conversation_history = {}

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
    if "file" not in request.files:
        return jsonify({"error": "No file part"}), 400
    file = request.files["file"]
    if file.filename == "":
        return jsonify({"error": "No selected file"}), 400
    if file and file.filename.endswith(".csv"):
        df = pd.read_csv(file)
        borrowers = df.to_dict(orient="records")
        socketio.emit("borrowers_update", {"borrowers": borrowers})
        return jsonify({"borrowers": borrowers}), 200
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

def initiate_whatsapp(phone, borrower):
    ref = db.init_user(phone)
    summary = f"Hello {borrower['F_Name']}! Your balance of Rs. {borrower['Current_balance']} is due by {borrower['Date_of_last_payment']}. Please confirm when you can pay."
    try:
        response = requests.post(WHATSAPP_API_URL, json={
            "phone_number": f"+{phone}",
            "message": summary
        })
        if response.status_code == 200:
            db.add_convo(ref, "message", db.payload("Bot", summary, time.ctime()))
            print(f"Sent WhatsApp message to +{phone}: {summary}")
            socketio.emit("whatsapp_status", {"phone": phone, "status": "sent", "message": summary})
        else:
            print(f"Failed to send WhatsApp message to +{phone}")
            socketio.emit("whatsapp_status", {"phone": phone, "status": "Failed to send"})
            db.increment_attempts(ref, "message")
            handle_retry(phone, "message", borrower, ref)
    except Exception as e:
        print(f"WhatsApp message failed for {phone}: {str(e)}")
        socketio.emit("whatsapp_status", {"phone": phone, "status": "Failed"})
        db.increment_attempts(ref, "message")
        handle_retry(phone, "message", borrower, ref)

def handle_retry(phone, channel, borrower,
 ref):
    attempts = db.get_attempts(ref, channel)
    print(f"Handling retry for {phone} on {channel}: {attempts}/{MAX_UNRESPONDED_ATTEMPTS}")
    if attempts < MAX_UNRESPONDED_ATTEMPTS:
        time.sleep(5)
        if channel == "voice":
            initiate_call(phone, borrower)
        elif channel == "message":
            initiate_whatsapp(phone, borrower)
    elif attempts >= MAX_UNRESPONDED_ATTEMPTS:
        alternate_channel = "message" if channel == "voice" else "voice"
        print(f"Switching to {alternate_channel} for {phone} after {attempts} unresponded {channel} attempts")
        db.reset_attempts(ref, alternate_channel)
        if alternate_channel == "voice":
            initiate_call(phone, borrower)
        elif alternate_channel == "message":
            initiate_whatsapp(phone, borrower)

@socketio.on("start_campaign")
def start_campaign(data):
    borrowers = data["borrowers"]
    borrower = borrowers[0]
    phone = str(borrower["Mobile_No"])
    channel = borrower["Channel_Preference"].lower()
    
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
        "user": None,
        "bot": initial_message,
        "latency_breakdown": {"total": 0}
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
        if call_sid in conversation_history:
            del conversation_history[call_sid]
    
    return "", 200

@app.route("/update-whatsapp-status", methods=['POST'])
def update_whatsapp_status():
    data = request.json
    phone = data["phone"]
    status = data["status"]
    ref = db.init_user(phone)
    print(f"WhatsApp status update for {phone}: {status}")
    socketio.emit("whatsapp_status", {"phone": phone, "status": status})
    if status == "read":
        db.increment_attempts(ref, "message")
        for b in pd.read_csv("indian_borrowers_4.csv").to_dict(orient="records"):
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