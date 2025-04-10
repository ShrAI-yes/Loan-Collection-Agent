# THIS SCRIPT IS THE MAIN SCRIPT 

import json
import datetime
import pytz
import speech_recognition as sr
from gtts import gTTS
import os
import subprocess
import time
from playsound import playsound
from agent import Agent 
import asyncio

def speech_to_text():
    recognizer = sr.Recognizer()
    with sr.Microphone() as source:
        print("\nListening... (Say 'exit' or 'thanks' to quit)")
        try:
            audio = recognizer.listen(source, timeout=10)
            user_input = recognizer.recognize_google(audio)
            print(f"You said: {user_input}")
            return user_input.lower()
        except sr.UnknownValueError:
            print("Sorry, I couldn't understand. Try again.")
            return None
        except sr.WaitTimeoutError:
            print("Listening timed out. Please try again.")
            return None

def text_to_speech(text):
    audio_file = "response.mp3"
    if os.path.exists(audio_file):
        os.remove(audio_file)
    tts = gTTS(text=text, lang=language, tld="co.uk" if language == "en" else "co.in")
    tts.save(audio_file)
    if os.name == "posix":  # macOS/Linux
        os.system(f"afplay {audio_file}") if "darwin" in os.sys.platform else os.system(f"mpg321 {audio_file}")
    else:  # Windows
        os.system(f"start /min {audio_file}")
    os.remove(audio_file)


# template_hi = """
# आप Predixion AI की एक पेशेवर लेकिन दोस्ताना क्रेडिट कार्ड भुगतान सहायक हैं।  
# आपका काम ग्राहकों को उनकी बकाया राशि समझाने, समय पर भुगतान के लिए याद दिलाने,  
# उपयुक्त पुनर्भुगतान विकल्प देने और एक आसान भुगतान अनुभव सुनिश्चित करने का है,  
# जबकि आप हमेशा विनम्र और सहानुभूति से भरी बातचीत करेंगी।

# ### आपका मुख्य उद्देश्य:
# 1. ग्राहक से भुगतान की प्रतिबद्धता प्राप्त करना (कब और कितना भुगतान करेंगे)।  
# 2. अनिच्छुक ग्राहकों को समझाकर उपयुक्त भुगतान विकल्प देना।  
# 3. उनके ऋण, बकाया राशि और उपलब्ध पुनर्भुगतान योजनाओं की सटीक जानकारी देना।  
# 4. वित्तीय नीतियों और भुगतान प्रभावों से संबंधित प्रश्नों को संभालना।  
# 5. भुगतान की अंतिम तिथि के अनुसार व्यावसायिक, सम्मानजनक और प्रभावी संचार बनाए रखना।  

# ### बातचीत की शुरुआत कैसे करें:
# ग्राहक {first_name} {last_name} की बकाया राशि Rs. {balance_to_pay} है, जो {start_date} तक देय है:
# 1. दोस्ताना अंदाज़ में शुरुआत करें:  
#    **"नमस्ते! मैं Predixion AI से बात कर रही हूँ। क्या मैं {first_name} से बात कर रही हूँ?"**  
# 2. अगर वे पुष्टि करें, तो कहें:  
#    **"बहुत बढ़िया! बस आपको एक छोटा सा रिमाइंडर देना था—आपकी बकाया राशि Rs. {balance_to_pay} की अंतिम तिथि {start_date} है।  
#    समय पर भुगतान करने से आपको लेट फीस और क्रेडिट स्कोर की समस्याओं से बचने में मदद मिलेगी।  
#    आप इसे कब तक चुका सकती हैं?"**  
# 3. अगर वे X राशि का भुगतान करने की पेशकश करें, तो शेष राशि निकालें:  
#    `remaining_balance = {balance_to_pay} - X`  
#    फिर कहें:  
#    **"शानदार! आप Rs. X का भुगतान यहाँ कर सकती हैं: https://pay.predixionai.com ।  
#    शेष राशि Rs. remaining_balance के लिए हम आपकी समय सीमा 10 दिनों के लिए बढ़ा सकते हैं।  
#    क्या आपको कोई और जानकारी चाहिए?"**  
# 4. अगर वे हिचकिचाएं या मना करें, तो कहें:  
#    **"कोई बात नहीं, मैं समझ सकती हूँ। क्या आप अभी थोड़ी सी राशि चुका सकती हैं?  
#    इससे आपकी समय सीमा 10 दिन के लिए आगे बढ़ सकती है। क्या यह आपके लिए सुविधाजनक होगा?"**  

# ### ग्राहक के प्रश्नों को संभालना:
# - ऋण से जुड़े प्रश्न (जैसे, "मेरा बकाया कितना है?" "मेरी अंतिम तिथि कब है?" "मेरा लोन किस प्रकार का है?") → **'get_user_data' का उपयोग करें**  
#   - **"आपका लोन प्रकार {loan_type} है।"**  
#   - **"आपको Rs. {balance_to_pay} का भुगतान करना है।"**  
#   - **"आपकी अंतिम तिथि {start_date} है।"**  
#   - **"क्या आपको कोई और जानकारी चाहिए?"**  

# - वित्तीय नीतियों से जुड़े प्रश्न (जैसे, "अगर मैं अपना लोन जल्दी बंद कर दूं तो क्या होगा?" "क्या मैं अधिक भुगतान की गई EMI की धनवापसी प्राप्त कर सकती हूँ?") → **'fetch_policy_query' का उपयोग करें**  
#   - **"[प्राप्त जानकारी]। क्या आपको और कुछ पूछना है?"**  t

# ### बातचीत को समाप्त करना:
# - यदि ग्राहक भुगतान की पुष्टि करें या उनकी शंका दूर हो जाए:  
#   - **"बात करने के लिए धन्यवाद! हम आपको एक ईमेल में विवरण और रिमाइंडर भेज देंगे।  
#      अगर आपको और कोई मदद चाहिए तो बेझिझक पूछिए। अपना ध्यान रखें!"**  
# - यदि ग्राहक भुगतान से मना करें और किसी योजना के लिए सहमत न हों:  
#   - **"ठीक है, हम {start_date} से पहले आपको एक रिमाइंडर भेजेंगे।  
#      यदि आपके विचार बदलें, तो हमें बताइए!"**  
# - यदि बातचीत दो बार स्पष्ट न हो:  
#   - **"समय निकालने के लिए धन्यवाद! हम आपको एक ईमेल में विवरण भेज देंगे।  
#      अगर आपको हमारी जरूरत हो, तो संपर्क करें। फिर मिलते हैं!"**  

# ### संवाद के नियम:
# 1. हमेशा विनम्र, गैर-टकरावपूर्ण और सहानुभूति से भरी रहें।  
# 2. जवाब छोटे, सरल और स्पष्ट हों—लंबी व्याख्याओं से बचें।  
# 3. एक ही बात को दोहराने से बचें।  
# 4. केवल सही और सत्यापित जानकारी दें—अनुमान न लगाएँ।  
# 5. ग्राहक की गोपनीयता का पूरा सम्मान करें—जानकारी किसी और से साझा न करें।  
# 6. बातचीत को उद्देश्यपूर्ण बनाए रखें: भुगतान की पुष्टि, सहायता और सहज समापन।  
# 7. अनावश्यक टिप्पणी और बार-बार एक ही बात कहने से बचें।  
# 8. यदि ग्राहक भुगतान करने को तैयार न हो, तो उसे सम्मानपूर्वक हैंडल करें और एक समाधान सुझाएँ।  
# 9. बातचीत को कुशलता से समाप्त करें, इसे ज़रूरत से ज्यादा लंबा न करें।  
# """

# Agent manager to handle multiple instances
agents = {}

def get_or_create_agent(phone, lang="en"):
    if phone not in agents:
        agents[phone] = Agent(phone=phone)
        agents[phone].initialize_template()
        initial_message = (
            f"हाय! मैं Predixion AI से हूँ। क्या आप {agents[phone].user['first_name']} जी हैं?" if lang == "hi"
            else f"Hey there! I’m from Predixion AI. Is this {agents[phone].user['first_name']}?"
        )
        agents[phone].say(initial_message)
    return agents[phone]

def chat(text=None, lang="en", phone=None):
    if not phone:
        raise ValueError("Phone number not set")
    agent = get_or_create_agent(phone, lang)
    if text:
        return agent.chat(text)
    return agent.chat_history[-1].content if agent.chat_history else "No conversation started yet."

voicebot_phone = None  # Keep for compatibility, but not used in chat

if __name__ == "__main__":
    phone = 9324082517
    print("Welcome! You can speak or type your queries. Say 'exit' or 'thanks' to quit.")
    initial_response = chat(phone=phone)
    print(f"\033[92mBot: {initial_response}\033[0m")
    text_to_speech(initial_response)
    while True:
        query = speech_to_text()
        if not query:
            query = input("\033[94mYou: \033[0m").strip().lower()
        if query in ['exit', 'thanks']:
            print(f"\033[92mBot: Goodbye! Have a great day.\033[0m")
            text_to_speech("Goodbye! Have a great day.")
            break
        response = chat(query, phone=phone)
        print(f"\033[92mBot: {response}\033[0m")
        text_to_speech(response)