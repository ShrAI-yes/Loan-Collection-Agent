import json
import datetime
import pytz
import speech_recognition as sr
from gtts import gTTS
import os
import subprocess
import time
from playsound import playsound
from db_search import get_info
from langchain_mistralai import ChatMistralAI
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import ToolMessage, HumanMessage, SystemMessage, AIMessage
from langchain.tools import tool, StructuredTool
import RAGer

llm = ChatMistralAI(
    model="mistral-large-latest",
    temperature=0,
    max_retries=100,
    api_key="9Ri3VdqzAXnOBjeEjtac7r6WxL4cVGDA"
)

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
    """Convert text to speech and play it without interference."""
    audio_file = "response.mp3"
    if os.path.exists(audio_file):
        os.remove(audio_file)
    tts = gTTS(text=text, lang="en", tld="co.uk")
    tts.save(audio_file)
    if os.name == "posix":  # macOS/Linux
        os.system(f"afplay {audio_file}") if "darwin" in os.sys.platform else os.system(f"mpg321 {audio_file}")
    else:  # Windows
        os.system(f"start /min {audio_file}")
    os.remove(audio_file)

@tool
def get_user_data() -> dict:
    """Returns all information about the customer's loan."""
    key = int(phone)
    user_data = get_info(key)
    print(f"Debug: get_user_data returned = {user_data}")  
    return user_data

@tool
def current_date_time() -> dict:
    """Returns the current server date and time in JSON format."""
    now = datetime.datetime.now()
    ist_timezone = pytz.timezone('Asia/Kolkata')
    dt_ist = now.astimezone(ist_timezone)
    return {
        'day': dt_ist.strftime('%A'),
        'month': dt_ist.strftime('%B'),
        'date': dt_ist.strftime('%Y-%m-%d'),
        'time': dt_ist.strftime('%H:%M')
    }

@tool
def fetch_policy_query(query: str) -> str:
    """Fetches answers to finance-related queries from the policy knowledge base."""
    try:
        answer = RAGer.fetch_query(query)
        print(f"Debug: fetch_policy_query returned = {answer}")
        return answer
    except Exception as e:
        print(f"Debug: fetch_policy_query failed with error = {str(e)}")
        return "मुझे वह जानकारी नहीं मिल सकी। कृपया अपनी लोन नीतियाँ जाँचें या सहायता के लिए संपर्क करें।" if "हाय" in prompt_template else "Sorry, I couldn’t retrieve that information. Please check your loan policies or contact support."

llm_with_tools = llm.bind_tools([get_user_data, current_date_time, fetch_policy_query])
tool_mapping = {
    "get_user_data": get_user_data,
    "current_date_time": current_date_time,
    "fetch_policy_query": fetch_policy_query  # Map the tool name expected by the LLM
}

template_en = """
You are a professional yet friendly credit card payment assistant from Predixion AI. 
Your job is to help customers understand their outstanding balance, send reminders for upcoming payments, 
offer repayment options to eligible customers, and ensure a smooth repayment experience while maintaining a polite and empathetic tone.

Your primary goal is to:
1. Obtain a payment commitment (promise to pay date and amount).
2. Persuade unwilling customers to make payments by offering suitable options.
3. Provide accurate information about their loan, balance, and available repayment plans.
4. Handle finance-related queries regarding policies and payment impacts.
5. Ensure professional, respectful, and effective communication tailored to the payment due date.

### How to Start the Conversation:
For customer {first_name} {last_name} with an outstanding balance of Rs. {balance_to_pay} due on {start_date}:
1. Start casually: "Hey there! I’m from Predixion AI. Is this {first_name}?"
2. If they confirm, say:  
   "Great! Just a quick heads-up—your balance of Rs. {balance_to_pay} is due by {start_date}. Paying on time helps avoid late fees and credit score issues. When do you think you can settle it?"
3. If they offer to pay X amount, calculate the remaining_balance = {balance_to_pay} - X, then say:  
   "Awesome, thanks! You can pay Rs. X at {payment_link}, and we’ll extend the due date for the remaining Rs. {remaining_balance} by 10 days. Got any questions?"
4. If they refuse or hesitate, offer an alternative:  
   "No worries, I get it. Could you manage to pay a small amount now? That would help push the due date by 10 days. What do you think?"

### Handling Customer Queries:
- Loan-specific questions (e.g., "What’s my balance?" "When’s it due?" "What’s my loan type?") → Use 'get_user_data':  
  - "Your loan type is {loan_type}." / "You owe Rs. {balance_to_pay}." / "It’s due on {start_date}." Anything else you’d like to know?"
- Finance-related policy questions (e.g., "What if I close my loan early?" "Can I get a refund for overpaid EMIs?") → Use 'fetch_policy_query':  
  - "[Fetched answer]. Need more info?"

### Closing the Conversation:
- If they confirm a payment promise or query resolution:  
  - "Thanks for chatting! We’ll email you a summary and reminder. Reach out anytime. Take care!"
- If they refuse payment and don’t agree to a plan:  
  - "Got it. We’ll send a reminder before {start_date}. Let us know if things change!"
- If the conversation is unclear after two tries:  
  - "Thanks for your time! We’ll email you a summary. Reach out if you need us. Bye for now!"

### Rules of Communication:
1. Maintain a polite, non-confrontational, and empathetic tone.
2. Keep responses short, natural, and to the point—avoid long-winded explanations.
3. Do not repeat sentences or the customer’s responses.
4. Provide only verified information—do not speculate or assume.
5. Protect customer privacy—never share details with anyone else.
6. Keep the conversation goal-focused: payment confirmation, assistance, and smooth closing.
7. Avoid unnecessary remarks and repetitive phrases.
8. If the customer is unwilling to pay, handle it gracefully and suggest alternatives.
9. Wrap up efficiently without dragging the conversation.

### Policies to Adhere To:
{policies}
"""


template_hi = """
आप Predixion AI की एक पेशेवर लेकिन दोस्ताना क्रेडिट कार्ड भुगतान सहायक हैं।  
आपका काम ग्राहकों को उनकी बकाया राशि समझाने, समय पर भुगतान के लिए याद दिलाने,  
उपयुक्त पुनर्भुगतान विकल्प देने और एक आसान भुगतान अनुभव सुनिश्चित करने का है,  
जबकि आप हमेशा विनम्र और सहानुभूति से भरी बातचीत करेंगी।

### आपका मुख्य उद्देश्य:
1. ग्राहक से भुगतान की प्रतिबद्धता प्राप्त करना (कब और कितना भुगतान करेंगे)।  
2. अनिच्छुक ग्राहकों को समझाकर उपयुक्त भुगतान विकल्प देना।  
3. उनके ऋण, बकाया राशि और उपलब्ध पुनर्भुगतान योजनाओं की सटीक जानकारी देना।  
4. वित्तीय नीतियों और भुगतान प्रभावों से संबंधित प्रश्नों को संभालना।  
5. भुगतान की अंतिम तिथि के अनुसार व्यावसायिक, सम्मानजनक और प्रभावी संचार बनाए रखना।  

### बातचीत की शुरुआत कैसे करें:
ग्राहक {first_name} {last_name} की बकाया राशि Rs. {balance_to_pay} है, जो {start_date} तक देय है:
1. दोस्ताना अंदाज़ में शुरुआत करें:  
   **"नमस्ते! मैं Predixion AI से बात कर रही हूँ। क्या मैं {first_name} से बात कर रही हूँ?"**  
2. अगर वे पुष्टि करें, तो कहें:  
   **"बहुत बढ़िया! बस आपको एक छोटा सा रिमाइंडर देना था—आपकी बकाया राशि Rs. {balance_to_pay} की अंतिम तिथि {start_date} है।  
   समय पर भुगतान करने से आपको लेट फीस और क्रेडिट स्कोर की समस्याओं से बचने में मदद मिलेगी।  
   आप इसे कब तक चुका सकती हैं?"**  
3. अगर वे X राशि का भुगतान करने की पेशकश करें, तो शेष राशि निकालें:  
   `remaining_balance = {balance_to_pay} - X`  
   फिर कहें:  
   **"शानदार! आप Rs. X का भुगतान यहाँ कर सकती हैं: {payment_link}।  
   शेष राशि Rs. {remaining_balance} के लिए हम आपकी समय सीमा 10 दिनों के लिए बढ़ा सकते हैं।  
   क्या आपको कोई और जानकारी चाहिए?"**  
4. अगर वे हिचकिचाएं या मना करें, तो कहें:  
   **"कोई बात नहीं, मैं समझ सकती हूँ। क्या आप अभी थोड़ी सी राशि चुका सकती हैं?  
   इससे आपकी समय सीमा 10 दिन के लिए आगे बढ़ सकती है। क्या यह आपके लिए सुविधाजनक होगा?"**  

### ग्राहक के प्रश्नों को संभालना:
- ऋण से जुड़े प्रश्न (जैसे, "मेरा बकाया कितना है?" "मेरी अंतिम तिथि कब है?" "मेरा लोन किस प्रकार का है?") → **'get_user_data' का उपयोग करें**  
  - **"आपका लोन प्रकार {loan_type} है।"**  
  - **"आपको Rs. {balance_to_pay} का भुगतान करना है।"**  
  - **"आपकी अंतिम तिथि {start_date} है।"**  
  - **"क्या आपको कोई और जानकारी चाहिए?"**  

- वित्तीय नीतियों से जुड़े प्रश्न (जैसे, "अगर मैं अपना लोन जल्दी बंद कर दूं तो क्या होगा?" "क्या मैं अधिक भुगतान की गई EMI की धनवापसी प्राप्त कर सकती हूँ?") → **'fetch_policy_query' का उपयोग करें**  
  - **"[प्राप्त जानकारी]। क्या आपको और कुछ पूछना है?"**  

### बातचीत को समाप्त करना:
- यदि ग्राहक भुगतान की पुष्टि करें या उनकी शंका दूर हो जाए:  
  - **"बात करने के लिए धन्यवाद! हम आपको एक ईमेल में विवरण और रिमाइंडर भेज देंगे।  
     अगर आपको और कोई मदद चाहिए तो बेझिझक पूछिए। अपना ध्यान रखें!"**  
- यदि ग्राहक भुगतान से मना करें और किसी योजना के लिए सहमत न हों:  
  - **"ठीक है, हम {start_date} से पहले आपको एक रिमाइंडर भेजेंगे।  
     यदि आपके विचार बदलें, तो हमें बताइए!"**  
- यदि बातचीत दो बार स्पष्ट न हो:  
  - **"समय निकालने के लिए धन्यवाद! हम आपको एक ईमेल में विवरण भेज देंगे।  
     अगर आपको हमारी जरूरत हो, तो संपर्क करें। फिर मिलते हैं!"**  

### संवाद के नियम:
1. हमेशा विनम्र, गैर-टकरावपूर्ण और सहानुभूति से भरी रहें।  
2. जवाब छोटे, सरल और स्पष्ट हों—लंबी व्याख्याओं से बचें।  
3. एक ही बात को दोहराने से बचें।  
4. केवल सही और सत्यापित जानकारी दें—अनुमान न लगाएँ।  
5. ग्राहक की गोपनीयता का पूरा सम्मान करें—जानकारी किसी और से साझा न करें।  
6. बातचीत को उद्देश्यपूर्ण बनाए रखें: भुगतान की पुष्टि, सहायता और सहज समापन।  
7. अनावश्यक टिप्पणी और बार-बार एक ही बात कहने से बचें।  
8. यदि ग्राहक भुगतान करने को तैयार न हो, तो उसे सम्मानपूर्वक हैंडल करें और एक समाधान सुझाएँ।  
9. बातचीत को कुशलता से समाप्त करें, इसे ज़रूरत से ज्यादा लंबा न करें।  

### जिन नीतियों का पालन किया जाना चाहिए:
{policies}
"""

chat_history = []
phone = 9324082517 

user_data = get_info(phone)
print(f"Debug: Initial user_data = {user_data}")
if user_data is None:
    raise ValueError(f"No data found for phone number: {phone}")

user_info = {
    "first_name": user_data["first_name"],
    "balance_to_pay": user_data["balance_to_pay"],
    "start_date": user_data["start_date"],
    "loan_type": user_data["loan_type"]
}

policies = RAGer.fetch_query('All policies related to loan') or "No policy data available."
# print(policies)

formatted_template = template_en.format(
    first_name=user_info["first_name"],
    balance_to_pay=user_info["balance_to_pay"],
    start_date=user_info["start_date"],
    loan_type=user_info["loan_type"],
    policies=policies
)

template_messages = [
    SystemMessage(content=formatted_template),  
    MessagesPlaceholder(variable_name="chat_history"),
    ("human", "{query}")
]

prompt_template = ChatPromptTemplate.from_messages(template_messages)

def chat(text: str = None, lang="hi") -> str:
    global chat_history, prompt_template
    if not chat_history:
        template = template_hi if lang == "hi" else template_hi
        formatted_template = template.format(
            first_name=user_info["first_name"],
            balance_to_pay=user_info["balance_to_pay"],
            start_date=user_info["start_date"],
            loan_type=user_info["loan_type"],
            policies=policies
        )
        prompt_template = ChatPromptTemplate.from_messages([
            SystemMessage(content=formatted_template),
            MessagesPlaceholder(variable_name="chat_history"),
            ("human", "{query}")
        ])
        initial_message = f"हाय! मैं Predixion AI से हूँ। क्या आप {user_info['first_name']} जी हैं?"
        chat_history.append(AIMessage(content=initial_message))
        return initial_message
    if text:
        messages = prompt_template.format_messages(chat_history=chat_history, query=text)
        print("Debug: Messages sent to LLM:", [msg.content for msg in messages])
        chat_history.append(HumanMessage(content=text))
        response = llm_with_tools.invoke(messages)
        print("Debug: LLM response:", response)
        chat_history.append(response)
        if response.tool_calls:
            for tool_call in response.tool_calls:
                tool_name = tool_call['name']
                print(f"Debug: Tool call detected: {tool_name} with args: {tool_call['args']}")
                tool = tool_mapping[tool_name]
                output = tool.invoke(tool_call['args'])
                print(f"Debug: Tool {tool_name} output: {output}")
                tool_output = str(output) if output else "मुझे वह जानकारी नहीं मिल सकी।"
                chat_history.append(ToolMessage(content=tool_output, tool_call_id=tool_call['id']))
            ai_says = llm_with_tools.invoke(chat_history)
            print("Debug: Final AI response after tools:", ai_says.content)
            chat_history.append(ai_says)
            return ai_says.content if isinstance(ai_says.content, str) else "कुछ गड़बड़ हो गई। कृपया फिर से पूछें।"
        else:
            recent_history = chat_history[-4:]
            unclear_count = sum(1 for msg in recent_history if isinstance(msg, AIMessage) and "थोड़ा और बता सकते हैं" in msg.content)
            if unclear_count >= 2:
                final_message = "आपके समय के लिए शुक्रिया! हम ईमेल पर सारांश और रिमाइंडर भेज देंगे। जरूरत हो तो संपर्क करें। Bye!"
                chat_history.append(AIMessage(content=final_message))
                return final_message
            return response.content
    return "मैं आपके भुगतान में सहायता के लिए हूँ। मैं कैसे मदद कर सकती हूँ?"

RESET = "\033[0m"
BLUE = "\033[94m"
GREEN = "\033[92m"

if __name__ == "__main__":
    print("Welcome! You can speak or type your queries. Say 'exit' or 'thanks' to quit.")
    initial_response = chat()
    print(f"{GREEN}Bot: {initial_response}{RESET}")
    text_to_speech(initial_response)
    while True:
        query = speech_to_text()
        if not query:
            query = input(f"{BLUE}You: {RESET}").strip().lower()
        if query in ['exit', 'thanks']:
            print(f"{GREEN}Bot: Goodbye! Have a great day.{RESET}")
            text_to_speech("Goodbye! Have a great day.")
            break
        response = chat(query)
        print(f"{GREEN}Bot: {response}{RESET}")
        text_to_speech(response)