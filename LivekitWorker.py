
#In-built Python Libraries____________________________________
import logging
logger = logging.getLogger("voice-agent")
logger.setLevel(logging.INFO)

import json
import datetime, pytz
import asyncio
import os
from dotenv import load_dotenv
load_dotenv(override=True)

# Custom made Libraries________________________________________
from context_manager import UserData, Database
from LogMetrics import serialize_metrics, save_to_file

# Livekit Agent Libraries______________________________________
from livekit import agents, api
from livekit.agents import llm, metrics, function_tool, get_job_context

from livekit.agents import (
    AgentSession,
    Agent,
    ChatMessage,
    ChatContext,
    JobContext,
    MetricsCollectedEvent,
    RunContext,
    WorkerOptions
)

#Livekit Metrics Libraries_______________________________________
from livekit.agents.metrics import (
    LLMMetrics,
    STTMetrics,
    TTSMetrics,
    EOUMetrics
)

#Livekit Third_Party Plugins Libraries_______________________________
from livekit.plugins import (
    groq,
    openai,
    elevenlabs,
    deepgram,
    silero
)
from livekit.plugins.elevenlabs import VoiceSettings


#_________________________________________Defining the Environment Variables______________________________________

LIVEKIT_URL = os.getenv('LIVEKIT_URL')
LIVEKIT_API_KEY = os.getenv("LIVEKIT_API_KEY")
LIVEKIT_API_SECRET = os.getenv("LIVEKIT_API_SECRET")

DEEPGRAM_API_KEY = os.getenv("DEEPGRAM_API_KEY")
ELEVENLABS_API_KEY = os.getenv("ELEVEN_API_KEY")

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
AZURE_OPENAI_API_KEY = os.getenv("AZURE_OPENAI_API_KEY")
AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
OPENAI_API_VERSION = os.getenv("OPENAI_API_VERSION")

SIP_TRUNK_ID = os.getenv("SIP_TRUNK_ID")


#_________________________________________This class defines the Voice Agent_______________________________________

class VoiceAgent(Agent):
    """
        A Livekit Agent implementation for a credit card payment management executive.

        This agent interacts with customers to provide loan details, remind about
        payments, and facilitate a smooth repayment experience. It uses various
        Livekit plugins for Speech-to-Text (STT), Large Language Model (LLM),
        and Text-to-Speech (TTS) functionalities.

        Attributes:
            context (dict): Metadata containing customer and loan details.
            customer_phone (str): The customer's phone number extracted from metadata.
    """

    def __init__(self, metadata, chat_ctx: ChatContext) -> None:
        """
        Initializes the VoiceAgent with specific instructions and Livekit components.

        Args:
            metadata (dict): A dictionary containing customer-specific information
                             such as phone, due_date, outstanding_amount, etc.
            chat_ctx (ChatContext): The Livekit ChatContext for managing chat history.
        """
        self.context = metadata
        self.customer_phone = self.context['phone'][3:]

        due_date = self.context['due_date']
        pending_days = self.context['pending_days']
        outstanding_amount = self.context['outstanding_amount']
        minimum_due_amount = self.context['minimum_due_amount']
        late_fees = self.context['late_fees']
        interest_rate = self.context['interest_rate']
        emi_eligible = self.context['emi_eligible']

        super().__init__(
            chat_ctx=chat_ctx,
            instructions=f"""
            **Identity**
            You are a female professional credit card payment management executive.
            Your primary responsibility is to assist customers with understanding their loan details,
            provide helpful reminders about upcoming payments, and ensure a smooth repayment experience.
            
            **Context**
            You are calling customers of a credit card company to remind them of their outstanding balance and minimum due amount.
            The goal is to obtain a promise-to-pay date and amount from willing customers, and to persuade unwilling customers to make payment.
            You may provide EMI offers to eligible customers. Communication should be adjusted based on number of days left for due date.
            Do not invent information. Only answer questions related to this context.
    
            ***Main Conversation Tasks***
            1. Greet customer and confirm identity.
            2. Remind of outstanding balance, minimum due, due date.
            3. If willing to pay → capture promise-to-pay.
            4. If unwilling → persuade to pay minimum → capture promise-to-pay.
            5. If still unwilling → capture reason → offer EMI if eligible.
            6. End call with proper summary of commitment or reason.
            
            **Payment Recovery Focus**
            - Primary goal: Secure payment commitment (date + amount).
            - If customer unwilling → capture reason, offer EMI if eligible.
            - Confirm that dates are legitimate (no invalid dates like 30 February).
            - Verify commitment before closing.
    
            ***Conversation Flow to Follow***
            1. Customer Identity Confirmation:
            - If yes → Proceed.
            - If wrong number → "माफ़ कीजिए!" → End call.
            - If busy/unavailable → "धन्यवाद। मैं वापस कॉल करूँगी।" → End call.
            2. Payment Reminder:
            "आपके क्रेडिट कार्ड के payment की ड्यू डेट {due_date} है। अभी {pending_days} दिन बाकी हैं। कृपया {outstanding_amount} समय पर clear करें।"
            3. Willing to Pay Full Amount:
            "मैं आपके account को अपडेट करूँगी कि आप {outstanding_amount} का payment {due_date} से पहले ऐप के जरिए करेंगे, क्या यह सही है?"
            - If yes → End call.
            - If no → Proceed to 4.
            4. Unwilling to Pay Full:
            "समझ सकती हूँ कि आप पूरा payment नहीं कर पा रहे हैं, लेकिन कृपया कम से कम minimum amount {minimum_due_amount} का payment करें ताकि लेट फीस से बच सकें और आपकी क्रेडिट हिस्ट्री भी affect न हो।"
            - If agrees → "मैं आपके account को अपडेट करूँगी कि आप minimum amount {minimum_due_amount}, {due_date} से पहले ऐप के जरिए करेंगे।" → End call.
            - If no → Proceed to 5.
            5. Unwilling to Pay Any Amount:
            "आपको पेमेंट करने में क्या problem है?"
            - If EMI eligible: "आपके account में EMI का option है। क्या आप इसे लेना चाहेंगे?"
            -- If yes → "मैं आपके account को अपडेट करूँगी कि आप EMI का option choose करने में interested हैं। लेकिन फिर भी आप minimum due amount {minimum_due_amount} जल्द से जल्द clear करें ताकि आपकी क्रेडिट हिस्ट्री affect न हो।" → End call.
            - If EMI not eligible and asked:
            -- "Unfortunately, इस समय EMI option आपके लिए उपलब्ध नहीं है। लेकिन आप payment करने के लिए दूसरे options को देखें ताकि लेट फीस और interest चार्जेस से बच सकें।" → End call.
            6. Call Closing:
            - Summarize the customer's commitment.
            - Trigger 'end_call' function.
            
            ***Response Generation and Language Guidelines***
            - Use conversational Hindi with urban tone (Delhi, Mumbai, Jaipur, Pune).
            - Rephrase statements naturally to avoid repetition.
            - Speak dates and numbers accurately in Hindi.
            - Do not perform or speak date calculations to customer.
            - Naturally mix common English words (loan, payment, business, interest, income).
            - Use colloquial Hindi, not formal Hindi.
            - Use 'दशमलव' for Interest.
            - Speak Rupees and Paise properly.
            - Use natural fillers ('Ok', 'हाँ', 'अच्छा', 'ठीक है') after customer responses.
            - Keep responses short and goal-focused.
            - Do not speculate or disclose unverified information.
            - Protect customer privacy.
            - Generate responses in simple Hindi
            - Generate responses in a single line without line breaks.
            - Do NOT use abbreviations. Write full words.
            
            **Style and Tone**
            - Polite, non-confrontational, empathetic tone
            - Clear and respectful language
            - Listen more, speak less
            - Professional and ethical
            
            **Communication Rules**
            - Short, natural, human-like responses.
            - No repeating customer's answers.
            - No repetitive phrases.
            - No speculative or unscripted statements.
            - When EMI is offered, do not calculate or disclose EMI amount.
    
            **Call Management and Language Detection Rules**
            - If customer greets with "Hello", "Hi", "Yes", proceed in Hindi.
            - If customer speaks multiple full sentences in another language, politely end call and inform a team member will call back in their preferred language.
            - Do not address customer by name after identity confirmation.
            - Do not end call until a commitment or valid reason for delay is captured.
            - Keep call under 5 minutes.
            - Do not hang up while the customer is speaking.
            
            ***Function Calls Available***
            - When customer asks any questions about their loan -> Fetch only relevant information from 'get_user_data' function.
            - When customer is confused about their loan details -> Fetch information from 'get_user_data' function.
            - If current date or time is required -> Fetch current datetime information from 'current_date_time' function.
            
            **Guardrails**
            - Maintain professionalism and user privacy.
            - Never disclose customer details to anyone else.
            - Ethically handle requests and disputes.
            
            **Avoid Early Termination**
            - Empathize and persuade customer to continue.
            - Highlight benefit of continuing.
            - Promise efficiency and short call.
            - Work toward solution.
            
            **Response Handling**
            #Gentle Clarification
            - "Sorry, थोड़ा क्लियर नहीं हुआ। आप फिर से बताएंगे?"
            - "मैं समझ सकती हूँ। आप tension ना लें..."
            
            **Redirection**
            - "Sorry, मुझे अपनी बात पूरी करने दें।"
            - Active listening.
            - Gentle guidance.
            
            **Dispute Handling**
            - Acknowledge: "क्या आप अपनी problem के बारे में थोड़ा detail में बता सकते हैं?"
            - Empathy: "मैं आपकी problem समझ रही हूँ और इसे resolve करने की पूरी कोशिश करूंगी।"
            - Resolution: "मैं इसे अभी note कर रही हूँ और related department को escalate करूंगी।"
            - Assurance: "हम आपकी problem का solution priority पर लेंगे और आपको अगले 48 hours में update देंगे।"
            - Closing: "धन्यवाद। आपकी problem का solution हमारी priority है।"
            
            ***Common Customer Question Answers***
            - Are you a robot? → "नहीं"
            - Is MAD required under EMI? → "Yes"
            - Is GST applicable on credit card default? → "Yes"
            - Is GST applicable on EMI interest? → "Yes"
            - Can you tell EMI interest or monthly payment? → "We will get back to you with details."
            - What is my due date? → {due_date}
            - What is current date? → Use 'current_date_time' function to get 'date' 
            - What are pending days? → {pending_days}
            - What is my late fees? → {late_fees}
            - What is interest rate? → {interest_rate}
            - Am I eligible for EMI? → {emi_eligible}
            - What is my outstanding amount? → {outstanding_amount}
            - What is my minimum due amount? → {minimum_due_amount}
            - Where are you calling from? → "One Card"
            - Can I pay using net banking? → "No, payment can be done through app only. If you need any assistance, we can arrange a call back and end the call."
            - How can I make payment? → "You can make the payment through app."
            """,

            stt=deepgram.STT(
                model="nova-3",
                smart_format=True,
                filler_words=True,
                language="multi",
                api_key=DEEPGRAM_API_KEY
            ),
            llm=llm.FallbackAdapter([
                openai.LLM.with_azure(
                    azure_endpoint=AZURE_OPENAI_ENDPOINT,
                    api_key=AZURE_OPENAI_API_KEY,
                    api_version=OPENAI_API_VERSION
                ),
                groq.LLM(
                    model='llama3-70b-8192',
                    api_key=GROQ_API_KEY
                ),
            ]),
            tts=elevenlabs.TTS(
                voice_id="JNaMjd7t4u3EhgkVknn3",
                model="eleven_turbo_v2_5",
                voice_settings=VoiceSettings(
                    speed=1.1,
                    style=0,
                    stability=0.5,
                    use_speaker_boost=False,
                    similarity_boost=0.8
                ),
                api_key=ELEVENLABS_API_KEY
            ),
            vad=silero.VAD.load(),
            turn_detection='stt',
        )


    #This is a Livekit In-built function that has been Overridden
    async def on_user_turn_completed(self, turn_ctx: ChatContext, new_message: ChatMessage):
        """
        Called when the user has finished speaking and the LLM is about to respond.

        This method can be overridden to add custom logic after a user's turn,
        such as logging the user's message or performing specific actions before
        the agent generates a reply.

        Args:
            turn_ctx (ChatContext): The current chat context of the session.
            new_message (ChatMessage): The new message from the user.
        """

        room_chat = turn_ctx.items
        for chat in room_chat[::-1]:
            if chat.role == 'assistant':
                #logger.info(f'Agent said: {chat.content[0]}')          #This statement prints the Agent response in console
                break

        #logger.info(f"User said: {new_message.text_content}")          #This statement prints the User response in console


    async def hangup(self):
        """
        Helper function to hang up the call by deleting the room.

        This function retrieves the job context and uses the Livekit API
        to delete the associated room, effectively ending the call.
        """

        logger.info(f"\n\n------------------Ending the call/ Terminating Room---------------------\n\n")

        job_ctx = get_job_context()
        await job_ctx.api.room.delete_room(
            api.DeleteRoomRequest(
                room=job_ctx.room.name,
            )
        )


    @function_tool()
    async def current_date_time(self, ctx: RunContext) -> dict:
        """
                Returns the current day, date and time in JSON format.

                Returns:
                    dict: A dictionary containing the current day, date, and time.
                          Example: {'day': 'Monday', 'date': '01 January, 2024', 'time': '03:45 PM'}
        """
        now = datetime.datetime.now()
        ist_timezone = pytz.timezone('Asia/Kolkata')
        dt_ist = now.astimezone(ist_timezone)

        current_time = dict()
        current_time['day'] = dt_ist.strftime('%A')
        current_time['date'] = f"{dt_ist.day} {dt_ist.strftime('%B')}, {dt_ist.year}"
        current_time['time'] = dt_ist.strftime('%I:%M %p')
        return current_time

    @function_tool()
    async def get_user_data(self, ctx: RunContext) -> dict:
        """
            Returns all information about the customer and their loan details in JSON format.

            Returns:
                dict: A dictionary containing all available user and loan details.
        """
        phone_number=self.customer_phone

        #Write code to fetch all user details from any database server based on phone number.

        data = UserData()
        data.read_file('borrower.csv')
        user_data = data.fetch_user(phone_number)
        return user_data


    @function_tool()
    async def end_call(self, ctx: RunContext):
        """
        Called when the user wants to end the call or mentions that you have called the wrong person.
        """

        await ctx.session.generate_reply(
            instructions="""Gracefully end the call.
                         If call ending due to wrong number, apologize.""",
            allow_interruptions=False
        )
        current_speech = ctx.session.current_speech
        if current_speech:
            await current_speech.wait_for_playout()

        await self.hangup()


#___________________________________Main Entrypoint Function executed when Job Dispatched__________________________

async def entrypoint(ctx: JobContext):
    """
        The main entry point for the Livekit Agent job.

        This asynchronous function initializes the VoiceAgent, connects it to the Livekit room,
        manages call metrics, handles conversation history storage, and initiates the SIP call
        to the customer.

        Args:
            ctx (JobContext): The Livekit JobContext, providing access to room, job metadata,
                              and API functionalities.
    """

    logger.info(f"\n\n------------------Connecting to room {ctx.room.name}---------------------\n")

    Metrics = {
        'LLM_METRICS' : [],
        'STT_METRICS' : [],
        'TTS_METRICS' : [],
        'EOU_METRICS' : []
    }

    #Extracting Metadata
    metadata = json.loads(ctx.job.metadata)

    first_name = metadata['first_name']
    last_name = metadata['last_name']
    outstanding_amount = metadata['outstanding_amount']
    installment = metadata['installment']
    call_summary = metadata['call_summary']

    phone = metadata['phone']  # Ex. +91987654321
    customer = f'{first_name} {last_name}'


    #--------------Context Management- Provide previous conversation context to Agent
    previous_context_flag = metadata['use_context']

    initial_context = f"""
            You are talking to our customer named {first_name} {last_name}.
            They have a total outstandiing loan repayment balance of {outstanding_amount}.
            According to their agreement they need to pay {installment} as monthly installment.
    """
    if previous_context_flag:
        initial_context = f"""
            {initial_context}

            Refer to the following previous conversation's context to start this conversation:
            {call_summary}
            
            Acknowledge the last interaction naturally. Do not repeat the entire conversation — 
            summarize briefly in a polite, human-like manner before continuing with the current objective.
    """

    initial_ctx = ChatContext()
    initial_ctx.add_message(
        role='system',
        content=initial_context
    )

    agent = VoiceAgent(metadata=metadata,chat_ctx=initial_ctx)      #Initializing Worker Agent

    await ctx.connect()         #Connects the Voice Agent to Livekit Room

    session = AgentSession(
        stt=agent.stt,
        llm=agent.llm,
        tts=agent.tts,
        vad=agent.vad,
        turn_detection='stt',
        allow_interruptions=True
    )

    #--------------Collect Call Metrics after each response-----------------
    @session.on("metrics_collected")
    def _on_metrics_collected(ev: MetricsCollectedEvent):
        if isinstance(ev.metrics, LLMMetrics):
            Metrics['LLM_METRICS'].append(ev.metrics)
            #print(f'LLM Metrics: {ev.metrics}')            #Prints LLM Metrics for each response in console
        elif isinstance(ev.metrics, STTMetrics):
            Metrics['STT_METRICS'].append(ev.metrics)
            #print(f'STT Metrics: {ev.metrics}')            #Prints STT Metrics for each response in console
        elif isinstance(ev.metrics, TTSMetrics):
            Metrics['TTS_METRICS'].append(ev.metrics)
            #print(f'TTS Metrics: {ev.metrics}')            #Prints TTS Metrics for each response in console
        elif isinstance(ev.metrics, EOUMetrics):
            Metrics['EOU_METRICS'].append(ev.metrics)
            #print(f'EOU Metrics: {ev.metrics}')            #Prints EOU Metrics for each response in console
        else:
            pass


    #----------------------These function will be executed after the call ends and session dissolves--------------
    async def store_history():
        """
            Asynchronously stores the conversation history to the database.

            This function extracts the chat history from the Livekit session,
            formats it, and then adds it to the database associated with the user.
        """
        print("\nStoring Conversation")
        chat_history = session.history.to_dict()

        phone_ref = phone[3:]
        name = customer
        history = []
        db = Database()
        ref = db.init_user(phone=phone_ref, name=name)

        for chat in chat_history['items']:
            payload = db.payload(
                name='agent' if chat['role'] == 'assistant' else name,
                text=chat['content'][0],  # or chat['content'] if it's a string
                time=datetime.datetime.now().isoformat(),
            )
            history.append(payload)

        db.add_convo(ref=ref, agent='voice',msg=history)


    async def store_metrics():
        """
        Asynchronously stores the collected call metrics to a file.

        This function serializes the collected LLM, STT, TTS, and EOU metrics
        into a JSON format and saves them to a timestamped file within the
        'log_metrics' directory.
        """

        print("\nStoring Metrics\n")
        call_metrics = json.dumps(Metrics, indent=4, default=serialize_metrics) #JSON format of all metrics for the current session

        dt_ist = datetime.datetime.now()
        filename = f"{phone}_CallMetrics_{dt_ist.day}-{dt_ist.strftime('%B')}-{dt_ist.year}T{dt_ist.strftime('%H_%M')}"
        save_to_file(file_content=call_metrics, filename=filename)

    ctx.add_shutdown_callback(store_history)
    ctx.add_shutdown_callback(store_metrics)


    #Create a Livekit Room for Agent and Customer to connect
    session_started = asyncio.create_task(
        session.start(
            agent=agent,
            room=ctx.room
        )
    )


    #Initiate Call to Customer using provided SIP Trunk
    try:
        await ctx.api.sip.create_sip_participant(
            api.CreateSIPParticipantRequest(
                room_name=ctx.room.name,
                sip_trunk_id=SIP_TRUNK_ID,
                sip_call_to=phone,
                participant_identity=customer,
                wait_until_answered=True
            )
        )

        await session_started
        participant = await ctx.wait_for_participant(identity=customer)
        logger.info(f"This participant joined: {participant.identity}")
        await session.generate_reply(instructions="Follow the **Converstation Flow**")

    except api.TwirpError as e:
        logger.error(
            f"The following error occured while creating SIP participant: {e.message}, "
            f"SIP status: {e.metadata.get('sip_status_code')} "
            f"{e.metadata.get('sip_status')}"
        )
        ctx.shutdown()

if __name__ == "__main__":
#______________________________Run an Instance of the Worker Agent using Livekit Cloud_______________________________________
    agents.cli.run_app(
        WorkerOptions(
            entrypoint_fnc=entrypoint,
            agent_name="Predixion-Voice-Agent",
            ws_url=LIVEKIT_URL,
            api_key=LIVEKIT_API_KEY,
            api_secret=LIVEKIT_API_SECRET,
            shutdown_process_timeout=15
        )
    )
