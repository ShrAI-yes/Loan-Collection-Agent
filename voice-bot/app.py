from flask import Flask, request, jsonify, send_file
import speech_recognition as sr
from voicebot import chat, text_to_speech
from flask_cors import CORS
import time
import os

app = Flask(__name__)
CORS(app)
log_file = "conversation_log.txt"

#does the log file exist?
if not os.path.exists(log_file):
    with open(log_file, "w") as f:
        f.write("Chat Log:\n")


def log_conversation(user_input, response, latency):
    with open(log_file, "a") as f:
        f.write(f"User: {user_input}\n")
        f.write(f"Bot: {response}\n")
        f.write(f"Response Time: {latency:.3f} seconds\n\n")


def speech_to_text():
    recognizer = sr.Recognizer()
    with sr.Microphone() as source:
        try:
            audio = recognizer.listen(source, timeout=10)
            return recognizer.recognize_google(audio).lower()
        except sr.UnknownValueError:
            return "Sorry, I couldn't understand. Please try again."
        except sr.WaitTimeoutError:
            return "Listening timed out. Please try again."


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


# @app.route("/voice", methods=["POST"])
# def voice_input():
#     user_input = speech_to_text()
#     start_time = time.time()
#     response = chat(user_input)
#     latency = time.time() - start_time
#     text_to_speech(response)

#     log_conversation(user_input, response, latency)

#     return jsonify({"response": response, "latency": latency})


@app.route("/download-log", methods=["GET"])
def download_log():
    return send_file(log_file, as_attachment=True)

if __name__ == "__main__":
    app.run(debug=False, threaded=False) 












