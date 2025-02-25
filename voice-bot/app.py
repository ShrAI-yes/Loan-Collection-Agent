import time
import os
import speech_recognition as sr
from flask import Flask, request, jsonify, send_file
from voicebot import chat, text_to_speech
from flask_cors import CORS
from twilio.rest import Client
from twilio.twiml.voice_response import VoiceResponse, Gather
from twilio.request_validator import RequestValidator
from dotenv import load_dotenv, dotenv_values 

app = Flask(__name__)
CORS(app)

app.config['SERVER_NAME'] = None
app.config['PREFERRED_URL_SCHEME'] = 'https'

WEBHOOK_BASE_URL="https://0b7a-103-48-100-115.ngrok-free.app"

load_dotenv() 
TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_PHONE = os.getenv("TWILIO_PHONE")
# USER_PHONE = os.getenv("USER_PHONE") #this will be dynamic

if not all([TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_PHONE]):
    raise ValueError("Missing required Twilio environment variables")

try:
    client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
    client.api.accounts(TWILIO_ACCOUNT_SID).fetch()
    print("Twilio credentials verified successfully")
except Exception as e:
    print(f"Failed to initialize Twilio client: {str(e)}")
    raise

# client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
validator = RequestValidator(TWILIO_AUTH_TOKEN)
log_file = "conversation_log.txt"

if not os.path.exists(log_file):
    with open(log_file, "w") as f:
        f.write("Chat Log:\n")

def log_conversation(user_input, response, latency):
    with open(log_file, "a") as f:
        f.write(f"User: {user_input}\n")
        f.write(f"Bot: {response}\n")
        f.write(f"Response Time: {latency:.3f} seconds\n\n")

#validate that the request actually came from twilio
def validate_twilio_request():
    signature = request.headers.get('X-Twilio-Signature', '')
    url = request.url
    params = request.form

    return validator.validate(url, params, signature)

# def speech_to_text():
#     recognizer = sr.Recognizer()
#     with sr.Microphone() as source:
#         try:
#             audio = recognizer.listen(source, timeout=10)
#             return recognizer.recognize_google(audio).lower()
#         except sr.UnknownValueError:
#             return "Sorry, I couldn't understand. Please try again."
#         except sr.WaitTimeoutError:
#             return "Listening timed out. Please try again."

@app.route("/chat", methods=["POST", "OPTIONS"])
def chatbot():
    if request.method == "OPTIONS":
        return jsonify({"message": "Preflight request"}), 200

    data = request.get_json()
    if not data or "message" not in data:
        return jsonify({"error": "No message provided"}), 400

    user_input = data["message"]
    start_time = time.time()
    response = chat(user_input)
    latency = time.time() - start_time
    text_to_speech(response)
    log_conversation(user_input, response, latency)
    return jsonify({"response": response, "latency": latency})

@app.route("/download-log", methods=["GET"])
def download_log():
    return send_file(log_file, as_attachment=True)

@app.route("/start-call", methods=["POST", "GET"])  
def start_call():
    # if request.method == "GET":
    #     return jsonify({"message": "Call endpoint is accessible"}), 200
        
    # try:
    #     print("\nStarting new call:")
    #     call = client.calls.create(
    #         url=f"{WEBHOOK_BASE_URL}/handle-call",
    #         to=USER_PHONE,
    #         from_=TWILIO_PHONE,
    #         status_callback=f"{WEBHOOK_BASE_URL}/call-status",
    #         status_callback_event=['initiated', 'ringing', 'answered', 'completed']
    #     )
    #     print(f"Call initiated - SID: {call.sid}")
    #     return jsonify({
    #         "message": "Call initiated",
    #         "call_sid": call.sid,
    #         "status": call.status
    #     }), 200

    # except Exception as e:
    #     print(f"Error initiating call: {str(e)}")
        # return jsonify({"error": str(e)}), 500
    try:
        data = request.json
        print(f"Received payload: {data}")  # ✅ Debugging print
        if not data or "phone" not in data:
            return jsonify({"error": "Missing 'phone' field"}), 400  # ✅ Improved error message
        borrower_phone = data["phone"]
        print(f"Initiating call to: {borrower_phone}")

        call = client.calls.create(
            url=f"{WEBHOOK_BASE_URL}/handle-call",
            to=borrower_phone,
            from_=TWILIO_PHONE,
            status_callback=f"{WEBHOOK_BASE_URL}/call-status",
            status_callback_event=['initiated', 'ringing', 'answered', 'completed']
        )
        print(f"Call initiated - SID: {call.sid}")
        return jsonify({
            "message": "Call initiated",
            "status": "initiated"
        }), 200

    except Exception as e:
        print(f"Error initiating call: {str(e)}") 
        return jsonify({"error": str(e)}), 500

@app.route("/call-status", methods=['POST'])
def call_status():
    print(f"\nCall Status Update:")
    print(f"Call SID: {request.form.get('CallSid')}")
    print(f"Call Status: {request.form.get('CallStatus')}")
    return "", 200

@app.route("/handle-call", methods=["POST"])
def handle_call():
    # print("\nHandling incoming call:")
    # print(f"Request form data: {dict(request.form)}") 
    # if not validate_twilio_request():
    #     print("Failed to validate Twilio request")
    #     return "Invalid request", 403
    response = VoiceResponse()
    response.say("Hello! How can I help you today?")
    gather = Gather(input='speech', action=f'{WEBHOOK_BASE_URL}/process-speech', timeout=5)
    response.append(gather)
    return str(response)


@app.route("/process-speech", methods=["POST"])
def process_speech():
    # if not validate_twilio_request():
    #     return "Invalid request", 403

    response = VoiceResponse()
    user_input = request.values.get("SpeechResult")
    if user_input:
        print(f"Recognized speech: {user_input}")
        start_time = time.time()
        bot_response = chat(user_input)
        latency = time.time() - start_time
        response.say(bot_response)
    else:
        print("No speech recognized")
        response.say("I didn't catch that. Could you please repeat?")
    gather = Gather(input='speech', action=f'{WEBHOOK_BASE_URL}/process-speech', timeout=5)
    response.append(gather)
    return str(response)


if __name__ == "__main__":
    app.run( debug=True)

