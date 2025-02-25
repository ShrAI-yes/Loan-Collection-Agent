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
    model="codestral-2501",
    temperature=0,
    max_retries=100,
    api_key="HjbwhDXRzRjxaKcj6GLdS5jWP2SUNpH7"
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

# def text_to_speech(text):
#     """Convert text to speech and play it."""
#     tts = gTTS(text=text, lang="en", tld="co.uk")  
#     audio_file = "response.mp3"
#     tts.save(audio_file)
#     playsound(audio_file)
#     os.remove(audio_file)

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

llm_with_tools = llm.bind_tools([get_user_data, current_date_time])
tool_mapping = {"get_user_data": get_user_data, "current_date_time": current_date_time}

template = """You are a professional credit card payment management executive.
Your primary responsibility is to assist customers with understanding their loan details, 
provide helpful reminders about upcoming payments, and ensure a smooth repayment experience. 

You are helping our customer {first_name} {last_name} to remind them of their outstanding balance along with minimum due amount. 
The goal is to obtain promise to pay date, and amount from willing customers, persuade unwilling customers to make payment. 
You may provide EMI offer to eligible customers. Communication needs to be adjusted based on number of days for due date. 
Stay focused on this context and provide relevant information. 
Do not invent information not drawn from the context. Answer only questions related to the context.

Rules of communication:
1. Maintain polite, non-confrontational tone
2. Handle concerns empathetically
3. Use clear and respectful language
4. Keep responses short and natural
5. Keep responses very short and to the point, mimicking human-like conversation.  
6. Prioritize user well-being and information accuracy.  
7. Show understanding with acknowledgments.  
8. Avoid long statements, especially while ending the call.  
9. Keep the conversation short and avoid unnecessary remarks.  
10. Avoid repeating borrower’s answers.  
11. Avoid repetitive phrases and statements.
12. Do not repeat a sentence twice.  
13. Avoid speculative/unverified information
14. Only mention numbers/amounts specified in relevant data.
15. Do not confront customers about anything and keep your tone polite.  
16. Maintain unwavering professionalism.  
17. Do not disclose any details to anyone except the customer.  
18. Protect user privacy and safety.  
19. Provide helpful, ethical, and constructive assistance.  
20. Recognize and gracefully handle inappropriate requests.  

Policies to adhere to: {policies}
"""

chat_history = []

template_messages = [
    SystemMessage(content=template),
    MessagesPlaceholder(variable_name="chat_history"),
    ("human", "{query}")
]

prompt_template = ChatPromptTemplate.from_messages(template_messages)

phone = 9804604602
user_data = get_info(phone)

user_info = {
    "first_name": user_data['first_name'],
    "last_name": user_data['last_name']
}

# Update system message with user data
policies = RAGer.fetch_query('All policies related to loan')
formatted_template = template.format(**user_info, policies=policies)
template_messages[0] = SystemMessage(content=formatted_template)
prompt_template = ChatPromptTemplate.from_messages(template_messages)

def chat(text: str) -> str:
    messages = prompt_template.format_messages(chat_history=chat_history, query=text)
    chat_history.append(HumanMessage(text))

    response = llm_with_tools.invoke(messages)
    chat_history.append(response)

    if response.tool_calls:
        for tool_call in response.tool_calls:
            tool = tool_mapping[tool_call['name']]
            output = tool.invoke(tool_call['args'])
            chat_history.append(ToolMessage(str(output), tool_call_id=tool_call['id']))
            ai_says = llm_with_tools.invoke(chat_history)
        chat_history.append(ai_says)
    else:
        ai_says = response

    return ai_says.content


RESET = "\033[0m"
BLUE = "\033[94m"  
GREEN = "\033[92m"  

if __name__ == "__main__":
    print("Welcome! You can speak or type your queries. Say 'exit' or type 'thanks' to quit.")

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