import time

from langchain_mistralai import ChatMistralAI
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import ToolMessage, HumanMessage, SystemMessage, AIMessage
from langchain.tools import tool

from context_manager import UserData, Database

class SuperAgent:
    def __init__(self):
        self.llm = ChatMistralAI(
            model="mistral-large-latest",
            temperature=0,
            max_retries=2,
            api_key="lSkg39BPClUnCXsloWHdoMUGp75f4el5"
        )

        self.summarizer = ChatMistralAI(
            model="mistral-large-latest",
            max_tokens=4096,
            temperature=0,
            max_retries=10,
            api_key="VS4P743v31nDWbgUcwy3MJJ9zWk5mt1V"
        )

        self.twillio_api='' #for connecting to voice agent
        self.meta_api='' #for connecting to whatsapp agent

        self.client = Database()
        self.file = UserData()

        whatsapp_agent = tool(self.whatsapp_agent)
        voice_agent = tool(self.voice_agent)
        self.arbiter = self.llm.bind_tools([self.whatsapp_agent, self.voice_agent])
        self.tool_mapping = {
            "whatsapp_agent": whatsapp_agent,
            "voice_agent": voice_agent
        }

        self.preference = 'call' #temporaryily added to prevent unpredictable behavior of LLM

        summary_template = """You are a simple chat conversation summarizer. 
        Summarize the given chat conversation which is provided in JSON format.
        If the chat conversation is blank return "" as response 
        Mention important details in the summary which can be used by a LLM as context.
        """

        decision_template = f"""You are an intelligent decision making model. 
        You have to use my response to decide between using either the 'whatsapp_agent' or the 'voice_agent'.
        If my response does not mention any preference for the agent use this preference: {self.preference}
        
        Use Voice Agent -> 'voice_agent':
        -If my preference is "call".
        -If my response explicitly mentions to speak to someone.
        -If my respomse explicitly mentions to have a phone call.
        -If my response explicitly mentions that I prefer to be called.
        
        Use WhatsApp Agent -> 'whatsapp_agent'
        -If my preference is "message"
        -If my response explictly mentions to send me a message.
        -If my response explictly mentions that I dont want to talk now.
        -If my response explicitly mentions that I prefer to be messaged.
        """
        template_messages = [
            SystemMessage(content=decision_template),
            ("human", "{response}")
        ]
        self.decision_prompt_template = ChatPromptTemplate.from_messages(template_messages)

        template_messages = [
            SystemMessage(content=summary_template),
            ("human", "{conversation}")
        ]
        self.summary_prompt_template = ChatPromptTemplate.from_messages(template_messages)

    def read_document(self, file_name):
        self.file.read_file(file_name)
        self.all_user_data = self.file.Data

    def generate_summary(self,phone):
        uri = self.client.init_user(phone=str(phone))
        whatsapp_convo = self.client.get_convo(ref=uri, agent='whatsapp')
        voice_convo = self.client.get_convo(ref=uri, agent='voice')

        try:
            message = self.summary_prompt_template.format_messages(conversation=whatsapp_convo)
            whatsapp_context = self.summarizer.invoke(message)
            time.sleep(1)
            message = self.summary_prompt_template.format_messages(conversation=voice_convo)
            voice_context = self.summarizer.invoke(message)
        except Exception as e:
            print(e)

        return whatsapp_context.content, voice_context.content

    def agent_context(self,phone):
        customer_data = self.file.fetch_user(phone_no=phone)
        customer_data['whatsapp_summary'], customer_data['call_summary'] = self.generate_summary(phone=phone)
        return customer_data

    def decide_agent(self, response):
        messages = self.decision_prompt_template.format_messages(response=response)
        decision = self.arbiter.invoke(messages)
        agent = decision.additional_kwargs['tool_calls'][0]['function']['name']
        if agent == 'whatsapp_agent':
            return agent
        else:
            return 'voice_agent'

    def whatsapp_agent(self) -> dict:
        """
        Connects to the WhatsApp Agent to send messages to the customer through WhatsApp.
        """
        print('____________________________Function Called the WhatsApp Agent_________________________')
        return {'Super Agent Response':'Connected to the WhatsApp Agent'}

    def voice_agent(self) -> dict:
        """
        Connects to the Voice Agent to initiate a Voice Call to talk with the customer.
        """
        print('____________________________Function Called the Voice Agent_________________________')
        return {'Super Agent Response':'Connected to the Voice Agent'}
