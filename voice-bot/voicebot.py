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
    api_key="key"
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
    print(f"Debug: get_user_data returned = {user_data}")  # Debug tool output
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

template = """You are a professional credit card payment management executive from Predixion AI. Your sole task is to assist customers with payment reminders and repayment plans for their outstanding balance of Rs. {balance_to_pay} due on {start_date}.

For customer {first_name}:
1. Start with: "Hi, I’m from Predixion AI. Am I talking to {first_name}?"
2. If the input is "yes", respond: "I’m calling to remind you that your outstanding balance of Rs. {balance_to_pay} is due on {start_date}. Please make sure to pay before {start_date} to avoid a late fee and a potential decrease in your credit score. Can you confirm when you’ll be able to pay?"
3. If the input matches "I can pay X now" (where X is a number), calculate remaining_balance as {balance_to_pay} minus X and respond: "Thank you, you can pay Rs. X at https://pay.predixionai.com. We’ll extend the due date by 10 days for the remaining Rs. [remaining_balance]. Is there anything else you’d like to know?"
4. If the input indicates refusal (e.g., "I can’t pay," "not now," "no" without prior payment offer), respond: "I understand your situation. To help, we can offer an EMI option or extend the due date by 10 days if you can pay a small amount soon. What works best for you?"
5. If the input asks about loan details (e.g., "what’s my balance," "when is it due"), use the 'get_user_data' tool and respond: "Your outstanding balance is Rs. {balance_to_pay}, due on {start_date}."
6. If the input is "no" after a payment offer was accepted, respond: "Thank you for arranging the payment. We’ll send you a confirmation and payment reminder via email. Please ensure it’s completed soon."
7. If the input is "no" after a refusal and no payment plan is agreed, respond: "I understand. We’ll send you a reminder via email. Please reach out if your situation changes before {start_date}."
8. For any other input, respond: "I’m here to assist with your payment. Could you please clarify or let me know how I can help with your balance of Rs. {balance_to_pay} due on {start_date}?"
9. If the input remains unclear after two attempts (track via chat history), respond: "Thank you for your time. We’ll send you a summary and reminder via email. Please contact us if you need further assistance."

Rules:
1. Maintain a polite, non-confrontational tone.
2. Keep responses short, direct, and limited to one or two sentences.
3. Do not repeat prior messages unless explicitly asked.
4. Do not invent user responses or unnecessary dialogue.
5. Use 'get_user_data' tool for accurate loan details when needed.
6. Focus on obtaining a promise-to-pay or offering repayment options.
7. End the call gracefully with an email follow-up mention when appropriate.

Policies: {policies}
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
    "start_date": user_data["start_date"]
}

policies = RAGer.fetch_query('All policies related to loan')

formatted_template = template.format(
    first_name=user_info["first_name"],
    balance_to_pay=user_info["balance_to_pay"],
    start_date=user_info["start_date"],
    policies=policies
)

template_messages = [
    SystemMessage(content=formatted_template),
    MessagesPlaceholder(variable_name="chat_history"),
    ("human", "{query}")
]
prompt_template = ChatPromptTemplate.from_messages(template_messages)

def chat(text: str = None) -> str:
    global chat_history
    if not chat_history:
        initial_message = f"Hi, I’m from Predixion AI. Am I talking to {user_info['first_name']}?"
        chat_history.append(AIMessage(content=initial_message))
        return initial_message
    if text:
        messages = prompt_template.format_messages(chat_history=chat_history, query=text)
        print("Debug: Messages sent to LLM:", [msg.content for msg in messages])
        chat_history.append(HumanMessage(text))
        response = llm_with_tools.invoke(messages)
        print("Debug: LLM response:", response.content)
        chat_history.append(response)
        if response.tool_calls:
            for tool_call in response.tool_calls:
                tool = tool_mapping[tool_call['name']]
                output = tool.invoke(tool_call['args'])
                print(f"Debug: Tool {tool_call['name']} output:", output)
                chat_history.append(ToolMessage(str(output), tool_call_id=tool_call['id']))
            ai_says = llm_with_tools.invoke(chat_history)
            print("Debug: Final AI response after tools:", ai_says.content)
            chat_history.append(ai_says)
            return ai_says.content
        else:
            # Check for repeated unclear input
            recent_history = chat_history[-4:]  # Look at last 4 messages (2 turns)
            unclear_count = sum(1 for msg in recent_history if isinstance(msg, AIMessage) and "Could you please clarify" in msg.content)
            if unclear_count >= 2:
                final_message = f"Thank you for your time. We’ll send you a summary and reminder via email. Please contact us if you need further assistance."
                chat_history.append(AIMessage(content=final_message))
                return final_message
            return response.content
    return "I’m here to assist with your payment. How can I help?"

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