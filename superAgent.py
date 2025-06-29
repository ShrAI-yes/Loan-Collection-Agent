import time
import os
from dotenv import load_dotenv
load_dotenv()

from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import SystemMessage

from context_manager import UserData, Database

class SuperAgent:
    """
        A class that manages the SuperAgent's functionalities, including summarization of conversations.
    """

    def __init__(self):
        """
            Initializes the SuperAgent with a summarizer LLM and database clients.
        """

        self.summarizer = ChatGroq(
            model='llama3-70b-8192',
            temperature=0.2,
            max_retries=5,
            api_key=os.getenv('GROQ_API_KEY')
        )

        self.client = Database()
        self.file = UserData()

        summary_template = """You are a simple chat conversation summarizer. 
        Summarize the given chat conversation which is provided in JSON format.
        If the chat conversation is blank return "No prior conversation occurred." as response 
        Mention important details in the summary which can be used by a LLM as context.
        """

        template_messages = [
            SystemMessage(content=summary_template),
            ("human", "{conversation}")
        ]
        self.summary_prompt_template = ChatPromptTemplate.from_messages(template_messages)

    def read_document(self, file_name):
        """
            Reads user data from a specified file in the './user_files/' directory.

            Args:
                file_name (str): The name of the file to be read.
        """
        self.file.read_file(file_name)
        self.all_user_data = self.file.Data

    def generate_summary(self,phone):
        """
            Generates a summary of recent voice conversations for a given phone number.

            Args:
                phone (str): The phone number of the customer.

            Returns:
                tuple: A tuple containing the summary of the voice conversation.
                       If an error occurs, it returns "No prior conversation occurred.".
        """
        uri = self.client.init_user(phone=str(phone))
        whatsapp_convo = self.client.get_convo(ref=uri, agent='whatsapp')
        voice_convo = self.client.get_convo(ref=uri, agent='voice')
        print(f'Fetched Conversation')

        try:
            message = self.summary_prompt_template.format_messages(conversation=whatsapp_convo)
            whatsapp_context = self.summarizer.invoke(message)
            time.sleep(1)
            message = self.summary_prompt_template.format_messages(conversation=voice_convo)
            voice_context = self.summarizer.invoke(message)
            return whatsapp_context.content, voice_context.content
        except Exception as e:
            print(e)
            return "No prior conversation occurred.","No prior conversation occurred."

    def agent_context(self,phone):
        """
            Fetches user data and conversation summaries for a specific phone number.

            Args:
                phone (str): The phone number of the customer.

            Returns:
                dict: A dictionary containing the customer's data and conversation summaries.
        """
        customer_data = self.file.fetch_user(phone_no=phone)
        customer_data['whatsapp_summary'], customer_data['call_summary'] = self.generate_summary(phone=phone)
        return customer_data
