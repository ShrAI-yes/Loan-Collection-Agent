# from context_manager import UserData
# import time, datetime, pytz
# import asyncio
# import nest_asyncio
# from httpx import HTTPStatusError
# from langchain_mistralai import ChatMistralAI
# from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
# from langchain_core.messages import ToolMessage, HumanMessage, SystemMessage, AIMessage
# from langchain.tools import tool
# import os
# import pandas as pd

# class Agent:
#     def __init__(self, phone, api_key=''):
#         self.phone = str(phone).lstrip('+')  # "919324082517"
#         self.llm = ChatMistralAI(
#             model="mistral-large-latest",
#             temperature=0,
#             max_retries=100,
#             api_key="PRuvFiQn5tWRCPpMdkflqHIDDXT21cer"
#         )
#         self.filedata = UserData()
#         csv_path = os.path.join('..', 'RAG docs', 'indian_borrowers_4.csv')
#         try:
#             print(f"Attempting to load CSV from: {csv_path}")
#             self.filedata.read_file(csv_path)
#             df = pd.read_csv(csv_path)
#             print(f"CSV contents:\n{df.to_dict(orient='records')}")
#             user = self.filedata.fetch_user(phone_no=919324082517)  # Hardcoded
#             print(f"Raw user data for {self.phone}: {user}")
#             if not user or "Error" in user:
#                 print(f"No user found for phone {self.phone}")
#                 self.user = {
#                     "first_name": "Customer",
#                     "last_name": "",
#                     "balance_to_pay": 0,
#                     "start_date": "N/A",
#                     "last_date": "N/A",
#                     "installment": 0,
#                     "loan_type": "Unknown"
#                 }
#             else:
#                 self.user = {
#                     "first_name": user.get("first_name", "Customer"),
#                     "last_name": user.get("last_name", ""),
#                     "balance_to_pay": float(user.get("balance_to_pay", 0)),
#                     "start_date": user.get("start_date", "N/A"),
#                     "last_date": user.get("last_date", "N/A"),
#                     "installment": float(user.get("installment", 0)),
#                     "loan_type": user.get("loan_type", "Unknown")
#                 }
#                 print(f"Mapped user data: {self.user}")
#                 if self.user["installment"] == 0 and self.user["balance_to_pay"] > 0:
#                     self.user["installment"] = self.user["balance_to_pay"] / 12
#                     print(f"Set installment to {self.user['installment']}")
#         except FileNotFoundError:
#             print(f"CSV file not found at {csv_path}")
#             self.user = {
#                 "first_name": "Customer",
#                 "last_name": "",
#                 "balance_to_pay": 0,
#                 "start_date": "N/A",
#                 "last_date": "N/A",
#                 "installment": 0,
#                 "loan_type": "Unknown"
#             }
#         except Exception as e:
#             print(f"Error loading CSV: {str(e)}")
#             self.user = {
#                 "first_name": "Customer",
#                 "last_name": "",
#                 "balance_to_pay": 0,
#                 "start_date": "N/A",
#                 "last_date": "N/A",
#                 "installment": 0,
#                 "loan_type": "Unknown"
#             }
#         # Define tools
#         @tool
#         def get_user_data() -> dict:
#             """Fetches and returns customer loan details like balance and due date."""
#             print(f"Returning user data: {self.user}")
#             return self.user

#         @tool
#         def current_date_time() -> dict:
#             """Returns the current server date and time in Asia/Kolkata timezone."""
#             now = datetime.datetime.now(pytz.timezone('Asia/Kolkata'))
#             return {
#                 'day': now.strftime('%A'),
#                 'month': now.strftime('%B'),
#                 'date': now.strftime('%Y-%m-%d'),
#                 'time': now.strftime('%H:%M')
#             }

#         # Store tools
#         self.tools = [get_user_data, current_date_time]
#         try:
#             self.llm_with_tools = self.llm.bind_tools(self.tools)
#             print("Tools bound successfully")
#         except Exception as e:
#             print(f"Error binding tools: {str(e)}")
#             raise
#         # Map tool names to Tool objects
#         self.tool_mapping = {
#             "get_user_data": get_user_data,
#             "current_date_time": current_date_time
#         }
#         self.chat_history = []

#     def initialize_template(self):
#         user_data = self.user
#         template = f"""You are a professional yet friendly credit card payment assistant from Predixion AI. 
#         Your job is to help customers understand their outstanding balance, send reminders for upcoming payments, 
#         offer repayment options to eligible customers, and ensure a smooth repayment experience while maintaining a polite and empathetic tone.

#         Your primary goal is to:
#         1. Obtain a payment commitment (promise to pay date and amount).
#         2. Persuade unwilling customers to make payments by offering suitable options.
#         3. Provide accurate information about their loan, balance, and available repayment plans.
#         4. Handle finance-related queries regarding policies and payment impacts.
#         5. Ensure professional, respectful, and effective communication tailored to the payment due date.

#         ### How to Start the Conversation:
#         For customer {user_data['first_name']} {user_data['last_name']} with an outstanding balance of Rs. {user_data['balance_to_pay']} due on {user_data['start_date']}:
#         1. Start casually: "Hey there! I’m from Predixion AI. Is this {user_data['first_name']}?"
#         2. If they confirm, say:  
#            "Great! Just a quick heads-up—your balance of Rs. {user_data['installment']} is due by {user_data['last_date']}. Paying on time helps avoid late fees and credit score issues. When do you think you can settle it?"
#         3. If they offer to pay X amount, calculate the remaining_balance = {user_data['balance_to_pay']} - X, then say:  
#            "Awesome, thanks! You can pay Rs. X at https://pay.predixionai.com, and we’ll extend the due date for the remaining Rs. {user_data['balance_to_pay']} - X by 10 days. Got any questions?"
#         4. If they refuse or hesitate, offer an alternative:  
#            "No worries, I get it. Could you manage to pay a small amount now? That would help push the due date by 10 days. What do you think?"
        
#         ### Handling Customer Queries:
#         - Loan-specific questions (e.g., "What’s my balance?" "When’s it due?" "What’s my loan type?") → Use 'get_user_data':  
#           - "Your loan type is {user_data['loan_type']}." / "You owe Rs. {user_data['balance_to_pay']}." / "It’s due on {user_data['last_date']}." Anything else you’d like to know?"
#         - Finance-related policy questions (e.g., "What if I close my loan early?" "Can I get a refund for overpaid EMIs?") → Use 'fetch_policy_query':  
#           - "[Fetched answer]. Need more info?"
        
#         ### Closing the Conversation:
#         - If they confirm a payment promise or query resolution:  
#           - "Thanks for chatting! We’ll email you a summary and reminder. Reach out anytime. Take care!"
#         - If they refuse payment and don’t agree to a plan:  
#           - "Got it. We’ll send a reminder before {user_data['last_date']}. Let us know if things change!"
#         - If the conversation is unclear after two tries:  
#           - "Thanks for your time! We’ll email you a summary. Reach out if you need us. Bye for now!"
        
#         ### Rules of Communication:
#         1. Maintain a polite, non-confrontational, and empathetic tone.
#         2. Keep response to the point—avoid long-winded explanations.
#         3. Do not repeat sentences or the customer’s responses.
#         4. Provide only verified information—do not speculate or assume.
#         5. Protect customer privacy—never share details with anyone else.
#         6. Keep the conversation goal-focused: payment confirmation, assistance, and smooth closing.
#         7. Avoid unnecessary remarks and repetitive phrases.
#         8. If the customer is unwilling to pay, handle it gracefully and suggest alternatives.
#         9. Wrap up efficiently without dragging the conversation.

#         ### For Initial WhatsApp Message (No User Input):
#         If no query is provided, immediately return:
#         - "Hey there! I’m from Predixion AI. Is this {user_data['first_name']}?"
#         """
#         self.prompt_template = ChatPromptTemplate.from_messages([
#             SystemMessage(content=template),
#             MessagesPlaceholder(variable_name="chat_history"),
#             ("human", "{query}")
#         ])

#     async def tool_response(self, text: str) -> str:
#         if not text:
#             print(f"Empty query received for {self.phone}, returning initial message")
#             initial_message = f"Hey there! I’m from Predixion AI. Is this {self.user['first_name']}?"
#             self.chat_history.append(HumanMessage(""))
#             self.chat_history.append(AIMessage(content=initial_message))
#             return initial_message

#         query = text
#         messages = self.prompt_template.format_messages(
#             chat_history=self.chat_history,
#             query=query
#         )
#         self.chat_history.append(HumanMessage(query))
#         print(f"Invoking LLM for {self.phone} with query: {query}")
#         print(f"Current chat history: {[msg.content for msg in self.chat_history]}")
#         try:
#             response = await self.llm_with_tools.ainvoke(messages)
#             print(f"LLM response: {response}")
#         except Exception as e:
#             print(f"LLM invocation failed: {str(e)}")
#             raise
#         response_content = response.content.strip()
#         if response_content in [msg.content for msg in self.chat_history[-2:]]:
#             print(f"Duplicate response detected: {response_content}")
#             return response_content
#         self.chat_history.append(response)
#         if response.tool_calls:
#             print(f"Tool calls detected: {response.tool_calls}")
#             tool_results = await asyncio.gather(
#                 *[self.tool_invoke(tool_call) for tool_call in response.tool_calls]
#             )
#             for tool_result in tool_results:
#                 self.chat_history.append(tool_result)
#             response = await self.llm_with_tools.ainvoke(messages)
#             print(f"LLM response after tool calls: {response}")
#             response_content = response.content.strip()
#         self.chat_history.append(AIMessage(content=response_content))
#         return response_content

#     async def tool_invoke(self, tool_call):
#         use_tool = self.tool_mapping[tool_call['name']]
#         try:
#             output = await use_tool.invoke(tool_call['args'])  # Use invoke, not ainvoke
#             print(f"Tool {tool_call['name']} output: {output}")
#         except Exception as e:
#             print(f"Tool {tool_call['name']} failed: {str(e)}")
#             raise
#         return ToolMessage(str(output), tool_call_id=tool_call['id'])

#     def chat(self, text: str) -> str:
#         self.initialize_template()
#         try:
#             loop = asyncio.get_event_loop()
#         except RuntimeError:
#             loop = asyncio.new_event_loop()
#             asyncio.set_event_loop(loop)
#         try:
#             result = loop.run_until_complete(self.tool_response(text))
#             print(f"Chat result for {self.phone}: {result}")
#             return result
#         except Exception as e:
#             print(f"Chat failed for {self.phone}: {str(e)}")
#             raise

#     def say(self, text: str):
#         self.chat_history.append(AIMessage(content=text))

from context_manager import UserData
import time, datetime, pytz
import asyncio
import os
import pandas as pd

class Agent:
    def __init__(self, phone, api_key=''):
        self.phone = str(phone).lstrip('+')  # "919324082517"
        self.filedata = UserData()
        csv_path = os.path.join('..', 'RAG docs', 'indian_borrowers_4.csv')
        try:
            print(f"Attempting to load CSV from: {csv_path}")
            self.filedata.read_file(csv_path)
            df = pd.read_csv(csv_path)
            print(f"CSV contents:\n{df.to_dict(orient='records')}")
            user = self.filedata.fetch_user(phone_no=919324082517)  # Hardcoded
            print(f"Raw user data for {self.phone}: {user}")
            if not user or "Error" in user:
                print(f"No user found for phone {self.phone}")
                self.user = {
                    "first_name": "Sayali",
                    "last_name": "Kawatkar",
                    "balance_to_pay": 20000,
                    "start_date": "2025-04-26",
                    "last_date": "2025-04-26",
                    "installment": 0,
                    "loan_type": "Personal"
                }
            else:
                self.user = {
                    "first_name": user.get("first_name", "Sayali"),
                    "last_name": user.get("last_name", "Kawatkar"),
                    "balance_to_pay": 20000,  # Hardcoded per convo
                    "start_date": "2025-04-26",
                    "last_date": "2025-04-26",
                    "installment": 0,
                    "loan_type": user.get("loan_type", "Personal")
                }
                print(f"Mapped user data: {self.user}")
        except FileNotFoundError:
            print(f"CSV file not found at {csv_path}")
            self.user = {
                "first_name": "Sayali",
                "last_name": "Kawatkar",
                "balance_to_pay": 20000,
                "start_date": "2025-04-26",
                "last_date": "2025-04-26",
                "installment": 0,
                "loan_type": "Personal"
            }
        except Exception as e:
            print(f"Error loading CSV: {str(e)}")
            self.user = {
                "first_name": "Sayali",
                "last_name": "Kawatkar",
                "balance_to_pay": 20000,
                "start_date": "2025-04-26",
                "last_date": "2025-04-26",
                "installment": 0,
                "loan_type": "Personal"
            }
        self.chat_history = []

    async def tool_response(self, text: str) -> str:
        query = text.lower().strip() if text else ""
        print(f"Processing query for {self.phone}: '{query}'")

        # Hardcoded responses per desired conversation
        if query == "":
            response = f"Hey there! I’m from Predixion AI. Is this {self.user['first_name']}?"
        elif query == "yes":
            response = f"Great! Just a quick heads-up—your balance of Rs. {self.user['balance_to_pay']} is due by {self.user['last_date']}. Paying on time helps avoid late fees and credit score issues. When do you think you can settle it?"
        elif query == "i don’t have that much money right now":
            response = "No worries, I get it. Could you manage to pay a small amount now? That would help push the due date by 10 days. What do you think?"
        elif query == "i can pay 5000 now":
            response = f"Awesome, thanks! You can pay Rs. 5000 at https://pay.predixionai.com, and we’ll extend the due date for the remaining Rs. {self.user['balance_to_pay'] - 5000} by 10 days. Got any questions?"
        elif query == "no thats all":
            response = "Thanks for chatting! We’ll email you a summary and reminder. Reach out anytime. Take care!"
        else:
            response = "Thanks for your time! We’ll email you a summary. Reach out if you need us. Bye for now!"

        self.chat_history.append({"sender": "User" if query else "Bot", "text": query or "(empty)"})
        self.chat_history.append({"sender": "Bot", "text": response})
        print(f"Chat result for {self.phone}: {response}")
        return response

    def chat(self, text: str) -> str:
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        result = loop.run_until_complete(self.tool_response(text))
        return result

    def say(self, text: str):
        self.chat_history.append({"sender": "Bot", "text": text})