import logging
logger = logging.getLogger("voice-agent")
logger.setLevel(logging.INFO)

import json
import datetime, pytz
import asyncio
import os
from dotenv import load_dotenv
load_dotenv()

from context_manager import UserData, Database

from livekit import agents, api
from livekit.agents import (
    AgentSession,
    Agent,
    ChatMessage,
    ChatContext,
    function_tool,
    get_job_context,
    JobContext,
    metrics,
    MetricsCollectedEvent,
    RunContext,
    WorkerOptions
)

from livekit.agents.metrics import (
    LLMMetrics,
    STTMetrics,
    TTSMetrics,
    EOUMetrics
)

from livekit.plugins import (
    groq,
    elevenlabs,
    deepgram,
    silero
)


LIVEKIT_URL = os.getenv('LIVEKIT_URL')
LIVEKIT_API_KEY = os.getenv("LIVEKIT_API_KEY")
LIVEKIT_API_SECRET = os.getenv("LIVEKIT_API_SECRET")

DEEPGRAM_API_KEY = os.getenv("DEEPGRAM_API_KEY")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
ELEVENLABS_API_KEY = os.getenv("ELEVEN_API_KEY")


class VoiceAgent(Agent):
    def __init__(self, metadata, chat_ctx: ChatContext) -> None:
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
    
            ***Conversation Flow to Follow***
            1. Customer Identity Confirmation
            - If yes → Proceed.
            - If wrong number → "माफ़ कीजिए!" → End call.
            - If busy/unavailable → "धन्यवाद। मैं वापस कॉल करूँगी।" → End call.
    
            2. Payment Reminder
            "आपके क्रेडिट कार्ड के payment की ड्यू डेट {due_date} है। अभी {pending_days} दिन बाकी हैं। कृपया {outstanding_amount} रुपये समय पर clear करें।"
    
            3. Willing to Pay Full Amount
            "मैं आपके account को अपडेट करूँगी कि आप {outstanding_amount} रुपये का payment {due_date} से पहले ऐप के जरिए करेंगे, क्या यह सही है?"
            - If yes → End call.
            - If no → Proceed to 4.
    
            4. Unwilling to Pay Full
            "समझ सकती हूँ कि आप पूरा payment नहीं कर पा रहे हैं, लेकिन कृपया कम से कम minimum amount {minimum_due_amount} रुपये का payment करें ताकि लेट फीस से बच सकें और आपकी क्रेडिट हिस्ट्री भी affect न हो।"
            - If agrees → "मैं आपके account को अपडेट करूँगी कि आप minimum amount {minimum_due_amount} रुपये {due_date} से पहले ऐप के जरिए करेंगे।" → End call.
            - If no → Proceed to 5.
    
            5. Unwilling to Pay Any Amount
            "आपको पेमेंट करने में क्या problem है?"
            - If EMI eligible: "आपके account में EMI का option है। क्या आप इसे लेना चाहेंगे?"
            -- If yes → "मैं आपके account को अपडेट करूँगी कि आप EMI का option choose करने में interested हैं। लेकिन फिर भी आप minimum due amount {minimum_due_amount} रुपये जल्द से जल्द clear करें ताकि आपकी क्रेडिट हिस्ट्री affect न हो।" → End call.
            - If EMI not eligible and asked:
            -- "Unfortunately, इस समय EMI option आपके लिए उपलब्ध नहीं है। लेकिन आप payment करने के लिए दूसरे options को देखें ताकि लेट फीस और interest चार्जेस से बच सकें।" → End call.
    
            6. Call Closing
            - Summarize the customer's commitment.
            - Trigger 'end_call' function.
    
            **Response Generation and Language Guidelines**
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
    
            **Common Customer Question Answers**
            - Are you a robot? → "नहीं"
            - Is MAD required under EMI? → "Yes"
            - Is GST applicable on credit card default? → "Yes"
            - Is GST applicable on EMI interest? → "Yes"
            - Can you tell EMI interest or monthly payment? → "We will get back to you with details."
            - What is my due date? → {due_date}
            - What is current date? → Use 'current_date_time' function to get 'date' 
            - What are pending days? → {pending_days}
            - What is my late fees? → Rs.{late_fees}
            - What is interest rate? → {interest_rate}
            - Am I eligible for EMI? → {emi_eligible}
            - What is my outstanding amount? → Rs.{outstanding_amount}
            - What is my minimum due amount? → Rs.{minimum_due_amount}
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
            llm=groq.LLM(
                model='llama3-70b-8192',
                api_key=GROQ_API_KEY
            ),
            tts=elevenlabs.TTS(
                voice_id="mfMM3ijQgz8QtMeKifko",
                model="eleven_multilingual_v2",
                api_key=ELEVENLABS_API_KEY
            ),
            vad=silero.VAD.load(),
            turn_detection='stt',
        )

    async def on_user_turn_completed(self, turn_ctx: ChatContext, new_message: ChatMessage):

        """Called when the user has finished speaking and the LLM is about to respond. """

        room_chat = turn_ctx.items

        for chat in room_chat[::-1]:
            if chat.role == 'assistant':
                logger.info(f'Agent said: {chat.content[0]}')
                break

        logger.info(f"User said: {new_message.text_content}")

    async def hangup(self):

        """Helper function to hang up the call by deleting the room"""

        job_ctx = get_job_context()
        await job_ctx.api.room.delete_room(
            api.DeleteRoomRequest(
                room=job_ctx.room.name,
            )
        )

    @function_tool()
    async def current_date_time(self, ctx: RunContext) -> dict:

        """Returns the current day, date and time in JSON format."""

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

        """Returns all information about the customer and their loan details in JSON format."""

        phone_number=self.customer_phone

        #Code to fetch all user details from database server based on phone number.

        data = UserData()
        data.read_file('borrower.csv')
        user_data = data.fetch_user(phone_number)
        return user_data


    @function_tool()
    async def end_call(self, ctx: RunContext):

        """Called when the user wants to end the call or mentions that you have called the wrong person."""

        logger.info(f"\n------------------Ending the call/ Terminating Room---------------------\n")

        current_speech = ctx.session.current_speech
        if current_speech:
            await current_speech.wait_for_playout()

        await self.hangup()

async def entrypoint(ctx: JobContext):
    logger.info(f"\n------------------Connecting to room {ctx.room.name}---------------------\n")

    metadata = json.loads(ctx.job.metadata)

    first_name = metadata['first_name']
    last_name = metadata['last_name']
    outstanding_amount = metadata['outstanding_amount']
    installment = metadata['installment']
    wa_summary = metadata['whatsapp_summary']
    call_summary = metadata['call_summary']

    phone = metadata['phone']  # Ex. +91987654321
    print('\n',phone[3:],'\n')
    customer = f'{first_name} {last_name}'


    initial_ctx = ChatContext()
    initial_ctx.add_message(
        role='system',
        content=f"""
            You are talking to our customer named {first_name} {last_name}.
            They have a total outstandiing loan repayment balance of Rupees {outstanding_amount}.
            According to their agreement they need to pay Rupees {installment} as monthly installment.
            
            Here are the previous conversation summaries with the customer on WhatsApp and Phone Call.
            Use these conversation summaries for additional context if necessary:
            
            WhatsApp Conversation Summary: {wa_summary}
            
            Phone Call Conversation Summary: {call_summary}
    """
    )

    agent = VoiceAgent(metadata=metadata,chat_ctx=initial_ctx)

    await ctx.connect()

    session = AgentSession(
        stt=agent.stt,
        llm=agent.llm,
        tts=agent.tts,
        vad=agent.vad,
        turn_detection='stt',
        allow_interruptions=True
    )

    session_monitor = metrics.UsageCollector()

    @session.on("metrics_collected")
    def _on_metrics_collected(ev: MetricsCollectedEvent):
        if isinstance(ev.metrics, LLMMetrics):
            print(f'LLM Metrics: {ev.metrics}')
        elif isinstance(ev.metrics, STTMetrics):
            print(f'STT Metrics: {ev.metrics}')
        elif isinstance(ev.metrics, TTSMetrics):
            print(f'TTS Metrics: {ev.metrics}')
        elif isinstance(ev.metrics, EOUMetrics):
            print(f'EOU Metrics: {ev.metrics}')
        else:
            pass

    async def store_history():
        chat_history = session.history.to_dict()

        phone_ref = phone
        name = f'{first_name} {last_name}'
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

        await session.aclose()

    async def get_metrics():
        metrics_summary = session_monitor.get_summary()
        print(f"Metrics: \n{metrics_summary}")

    ctx.add_shutdown_callback(store_history)
    ctx.add_shutdown_callback(get_metrics)

    session_started = asyncio.create_task(
        session.start(
            agent=agent,
            room=ctx.room
        )
    )

    try:
        await ctx.api.sip.create_sip_participant(
            api.CreateSIPParticipantRequest(
                room_name=ctx.room.name,
                sip_trunk_id='ST_udiSagMKGZKr',
                sip_call_to=phone,
                participant_identity=customer,
                wait_until_answered=True
            )
        )
        # wait for the agent session start and participant join
        await session_started
        participant = await ctx.wait_for_participant(identity=f'{first_name} {last_name}')
        logger.info(f"This participant joined: {participant.identity}")
        await session.generate_reply(instructions=f"Confirm if you are talking to {customer}.")

    except api.TwirpError as e:
        logger.error(
            f"The following error occured while creating SIP participant: {e.message}, "
            f"SIP status: {e.metadata.get('sip_status_code')} "
            f"{e.metadata.get('sip_status')}"
        )
        ctx.shutdown()


if __name__ == "__main__":
    agents.cli.run_app(
        WorkerOptions(
            entrypoint_fnc=entrypoint,
            agent_name="Predixion-Voice-Agent",
            ws_url=LIVEKIT_URL,
            api_key=LIVEKIT_API_KEY,
            api_secret=LIVEKIT_API_SECRET
        )
    )
