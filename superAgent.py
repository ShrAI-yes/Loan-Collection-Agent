from langchain_mistralai import ChatMistralAI
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import ToolMessage, HumanMessage, SystemMessage, AIMessage
from langchain.tools import tool

from context_manager import UserData

class SuperAgent:
    def __init__(self,preference):
        self.llm = ChatMistralAI(
            model="mistral-large-latest",
            temperature=0,
            max_retries=2,
            api_key="87du8i9QPYZVhsToktC9HxXP0yrjhdjQ"
        )

        self.twillio_api='' #for connecting to voice agent
        self.meta_api='' #for connecting to whatsapp agent

        whatsapp_agent = tool(self.whatsapp_agent)
        voice_agent = tool(self.voice_agent)
        self.arbiter = self.llm.bind_tools([self.whatsapp_agent, self.voice_agent])
        self.tool_mapping = {
            "whatsapp_agent": whatsapp_agent,
            "voice_agent": voice_agent
        }

        self.preference = preference

        template = f"""You are an intelligent decision making model. 
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
            SystemMessage(content=template),
            ("human", "{response}")
            # HumanMessage(content="{query}")
        ]
        self.prompt_template = ChatPromptTemplate.from_messages(template_messages)

    def read_document(self, file_name):
        file = UserData()
        file.read_file(file_name)
        self.all_user_data = file.Data

    def decide_agent(self, response):
        messages = self.prompt_template.format_messages(response=response)
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
