#this script is a speech enabled chatbot that interacts with the user to provide information about their loan and answer financial queries
#the user can speak or write their queries and the bot will respond accordingly
#the bot will only respond in text format 

import json
import datetime
import pytz
import speech_recognition as sr
from db_search import get_info
from langchain_mistralai import ChatMistralAI
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import ToolMessage, HumanMessage, SystemMessage, AIMessage
from langchain.tools import tool, StructuredTool

llm = ChatMistralAI(
    model="codestral-2501",
    temperature=0,
    max_retries=100,
    api_key="r2laTLGuoa4V7Lm5onLICJf942bSlEJs"
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

template = """You are an intelligent virtual financial agent helping our customer {first_name} {last_name}.
Your role is to help manage the customer's loan repayment and answer their financial questions in a clear and precise way. 

Instructions:
1. Use precise financial language and ensure clear, accurate information.
2. If the user is willing to pay the loan, provide this link '''https://paymentUSER1UDN.com'''. Do not send the link until the user requests it.
3. If the customer is struggling, provide options like grace periods, payment restructuring, or deadline extensions.
4. Keep responses short and to the point.
5. Ensure confidentiality and remind the customer to keep their payment details secure.
6. You can extend the last loan repayment date by a maximum of 10 days if the user requests it.
7. If the question cannot be answered using the provided information, reply with "Sorry, but I am unable to answer this query".
"""

chat_history = []

template_messages = [
    SystemMessage(content=template),
    MessagesPlaceholder(variable_name="chat_history"),
    ("human", "{query}")
]

prompt_template = ChatPromptTemplate.from_messages(template_messages)

phone = 9324082517
user_data = get_info(phone)

user_info = {
    "first_name": user_data['first_name'],
    "last_name": user_data['last_name']
}

formatted_template = template.format(**user_info)
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

if __name__ == "__main__":
    print("Welcome! You can speak or type your queries. Say 'exit' or type 'thanks' to quit.")

    while True:
        query = speech_to_text()  #trying the voice input first

        if not query:  #if voice fails, go for a simple text based approach
            query = input("You: ").strip().lower()

        if query in ['exit', 'thanks']:
            print("Bot: Goodbye! Have a great day.")
            break

        response = chat(query)
        print("Bot:", response)
