from db_search import get_info
from context_manager import UserData
import time, datetime, pytz
import asyncio
import nest_asyncio
from httpx import HTTPStatusError
from langchain_mistralai import ChatMistralAI
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import ToolMessage, HumanMessage, SystemMessage, AIMessage
from langchain.tools import tool, StructuredTool


class Agent:
    def __init__(self, phone, api_key=''):
        self.phone = int(phone)
        self.llm = ChatMistralAI(
            model="mistral-large-latest",
            temperature=0,
            max_retries=100,
            api_key="xBtlMuibhXVCjcJj9vb6tc4IDkC4OPoh"
        )

        self.filedata = UserData()
        self.filedata.read_file('indian_borrowers_4.csv')  
        self.user = self.filedata.fetch_user(phone_no=int(self.phone))

        get_user_data = tool(self.get_user_data)
        current_date_time = tool(self.current_date_time)

        self.llm_with_tools = self.llm.bind_tools([self.get_user_data, self.current_date_time])
        self.tool_mapping = {
            "get_user_data": get_user_data,
            "current_date_time": current_date_time
        }
        self.chat_history = []

    def get_user_data(self) -> dict:
        """Returns all information about the customer and their loan details."""
        return self.user

    def current_date_time(self) -> dict:
        '''
        Returns the current server date and time in JSON format.
        '''
        now = datetime.datetime.now()
        ist_timezone = pytz.timezone('Asia/Kolkata')
        dt_ist = now.astimezone(ist_timezone)
        current_time = dict()
        current_time['day'] = dt_ist.strftime('%A')
        current_time['month'] = dt_ist.strftime('%B')
        current_time['date'] = dt_ist.strftime('%Y-%m-%d')
        current_time['time'] = dt_ist.strftime('%H:%M')
        return current_time

    def initialize_template(self):
        user_data = self.user

        template = f"""You are a professional yet friendly credit card payment assistant from Predixion AI. 
        Your job is to help customers understand their outstanding balance, send reminders for upcoming payments, 
        offer repayment options to eligible customers, and ensure a smooth repayment experience while maintaining a polite and empathetic tone.

        Your primary goal is to:
        1. Obtain a payment commitment (promise to pay date and amount).
        2. Persuade unwilling customers to make payments by offering suitable options.
        3. Provide accurate information about their loan, balance, and available repayment plans.
        4. Handle finance-related queries regarding policies and payment impacts.
        5. Ensure professional, respectful, and effective communication tailored to the payment due date.

        ### How to Start the Conversation:
        For customer {user_data['first_name']} {user_data['last_name']} with an outstanding balance of Rs. {user_data['balance_to_pay']} due on {user_data['start_date']}:
        1. Start casually: "Hey there! I’m from Predixion AI. Is this {user_data['first_name']}?"
        2. If they confirm, say:  
           "Great! Just a quick heads-up—your balance of Rs. {user_data['installment']} is due by {user_data['last_date']}. Paying on time helps avoid late fees and credit score issues. When do you think you can settle it?"
        3. If they offer to pay X amount, calculate the remaining_balance = {user_data['balance_to_pay']} - X, then say:  
           "Awesome, thanks! You can pay Rs. X at https://pay.predixionai.com, and we’ll extend the due date for the remaining Rs. {user_data['balance_to_pay']} - X by 10 days. Got any questions?"
        4. If they refuse or hesitate, offer an alternative:  
           "No worries, I get it. Could you manage to pay a small amount now? That would help push the due date by 10 days. What do you think?"
        
        ### Handling Customer Queries:
        - Loan-specific questions (e.g., "What’s my balance?" "When’s it due?" "What’s my loan type?") → Use 'get_user_data':  
          - "Your loan type is {user_data['loan_type']}." / "You owe Rs. {user_data['balance_to_pay']}." / "It’s due on {user_data['last_date']}." Anything else you’d like to know?"
        - Finance-related policy questions (e.g., "What if I close my loan early?" "Can I get a refund for overpaid EMIs?") → Use 'fetch_policy_query':  
          - "[Fetched answer]. Need more info?"
        
        ### Closing the Conversation:
        - If they confirm a payment promise or query resolution:  
          - "Thanks for chatting! We’ll email you a summary and reminder. Reach out anytime. Take care!"
        - If they refuse payment and don’t agree to a plan:  
          - "Got it. We’ll send a reminder before {user_data['last_date']}. Let us know if things change!"
        - If the conversation is unclear after two tries:  
          - "Thanks for your time! We’ll email you a summary. Reach out if you need us. Bye for now!"
        
        ### Rules of Communication:
        1. Maintain a polite, non-confrontational, and empathetic tone.
        2. Keep response to the point—avoid long-winded explanations.
        3. Do not repeat sentences or the customer’s responses.
        4. Provide only verified information—do not speculate or assume.
        5. Protect customer privacy—never share details with anyone else.
        6. Keep the conversation goal-focused: payment confirmation, assistance, and smooth closing.
        7. Avoid unnecessary remarks and repetitive phrases.
        8. If the customer is unwilling to pay, handle it gracefully and suggest alternatives.
        9. Wrap up efficiently without dragging the conversation.
        """
        #Previous conversation summary:{conversation}
        #"""
        template_messages = [
            SystemMessage(content=template),
            MessagesPlaceholder(variable_name="chat_history"),
            ("human", "{query}")
        ]
        self.prompt_template = ChatPromptTemplate.from_messages(template_messages)

    async def tool_invoke(self,tool_call, tool_mapping):
        use_tool = tool_mapping[tool_call['name']]
        output = await use_tool.ainvoke(tool_call['args'])
        return ToolMessage(str(output), tool_call_id=tool_call['id'])

    async def tool_response(self,text: str) -> str:
        messages = self.prompt_template.format_messages(
            chat_history=self.chat_history,
            query=text
        )
        self.chat_history.append(HumanMessage(text))

        response = await self.llm_with_tools.ainvoke(messages)  # use ainvoke for async calls
        self.chat_history.append(response)

        if response.tool_calls:
            tool_results = await asyncio.gather(
                *[self.tool_invoke(tool_call, self.tool_mapping) for tool_call in response.tool_calls]
            )
            for tool_result in tool_results:
                self.chat_history.append(tool_result)

            try:
                ai_says = await self.llm_with_tools.ainvoke(self.chat_history)
            except HTTPStatusError as e:
                print("Some API error occured. Retrying after a second")
                await asyncio.sleep(1)
                ai_says = await self.llm_with_tools.ainvoke(self.chat_history)

            self.chat_history.append(ai_says)
        else:
            ai_says = response

        return ai_says.content

    def chat(self, text: str) -> str:
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        # Run the async_chat coroutine in the current loop using run_until_complete.
        return loop.run_until_complete(self.tool_response(text))

    def say(self, text: str):
        ai_says = AIMessage(content=text)
        self.chat_history.append(ai_says)