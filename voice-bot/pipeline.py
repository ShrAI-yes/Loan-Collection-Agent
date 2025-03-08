import json
import datetime
import pytz
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

@tool
def get_user_data(phone: int) -> dict:
    """
    Returns all information about the customer's loan.
    """
    user_data = get_info(phone)
    return user_data

@tool
def current_date_time() -> dict:
    """
    Returns the current server date and time in JSON format.
    """
    now = datetime.datetime.now()
    ist_timezone = pytz.timezone('Asia/Kolkata')
    dt_ist = now.astimezone(ist_timezone)
    return {
        "day": dt_ist.strftime('%A'),
        "month": dt_ist.strftime('%B'),
        "date": dt_ist.strftime('%Y-%m-%d'),
        "time": dt_ist.strftime('%H:%M')
    }

# Bind Tools
llm_with_tools = llm.bind_tools([get_user_data, current_date_time])
tool_mapping = {"get_user_data": get_user_data, "current_date_time": current_date_time}


template = """You are an intelligent virtual financial agent helping our customer {first_name} {last_name}.
Your role is to help manage the customer's loan repayment and answer their financial questions in a clear and precise way.

Instructions:
1. Use precise financial language and ensure clear, accurate information.
2. If the user is willing to pay the loan then please provide this link 'https://paymentUSER1UDN.com'. Do not send the link until user requests or user wants to pay the loan.
3. If the customer is struggling, provide options like grace periods, payment restructuring, or deadline extensions considering their income, number of late repayments, and loan amount yet to be repaid.
4. Keep responses short and to the point.
5. Ensure confidentiality and remind the customer to keep their payment details secure.
6. You can only extend the last loan repayment date by a maximum of 10 days if the user requests grace periods or deadline extensions considering their financial situation.
7. Always address the customer by their first name {first_name} in responses. Like "Hello {first_name}, how can i help you?"
 8. Never ask for the phone number, as you already have the customer's details. If the customer asks why, let them know it’s for security reasons.
9. If the question cannot be answered using the information provided, reply with "Sorry, but I am unable to answer this query."
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

# Update system message with user data
formatted_template = template.format(**user_info)
template_messages[0] = SystemMessage(content=formatted_template)
prompt_template = ChatPromptTemplate.from_messages(template_messages)

def chat(text: str) -> str:
    messages = prompt_template.format_messages(
        chat_history=chat_history,
        query=text
    )
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
    while True:
        query = input("You: ")  # User types input
        
        if query.lower() == "thanks":
            print("Goodbye!")
            break
        else:
            res = chat(query)
            print("Bot:", res)
    
    print("Chat history:", chat_history)
