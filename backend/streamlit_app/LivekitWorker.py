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
    Agent,
    AgentSession,
    ChatMessage,
    ChatContext,
    function_tool,
    get_job_context,
    JobContext,
    RunContext,
    WorkerOptions
)
from livekit.agents import RoomInputOptions
from livekit.plugins import (
    groq,
    elevenlabs,
    deepgram,
    silero
)


LIVEKIT_URL = os.getenv('LIVEKIT_URL')
LIVEKIT_API_KEY = os.getenv("LIVEKIT_API_KEY")
LIVEKIT_API_SECRET = os.getenv("LIVEKIT_API_SECRET")

DEEPGRAM_API_KEY="fac86ae1904bb9e5734a80dda31a5fb7da4acab6"


# DEEPGRAM_API_KEY = os.getenv("DEEPGRAM_API_KEY")
# if not DEEPGRAM_API_KEY:
#     raise RuntimeError("DEEPGRAM_API_KEY is not set. Please check your .env file or environment variables.")

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
ELEVENLABS_API_KEY = os.getenv("ELEVEN_API_KEY")


class VoiceAgent(Agent):
    def __init__(self, customer_phone, chat_ctx: ChatContext) -> None:
        self.customer_phone = customer_phone
        super().__init__(
            instructions="""
            You are a professional and friendly FEMALE credit card payment assistant from Predixion AI named Riya. 
            Your job is to help customers understand their outstanding balance, send reminders for upcoming payments, 
            offer repayment options to eligible customers, and ensure a smooth repayment experience while maintaining a polite and empathetic tone.

            ***Response Generation Rules***
            - Generate conversational responses in simple Hindi or English according to the customer's input language.
            - Generate responses in a single line without any line breaks.
            - Responses should NOT contain abbreviations. Use full forms of all words. 

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
            """,
            chat_ctx=chat_ctx,
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
                voice_id="KYiVPerWcenyBTIvWbfY",
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
                print(f'Agent said: {chat.content[0]}')
                break

        print(f"User said: {new_message.text_content}")

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

        logger.info(f"Ending the call")

        current_speech = ctx.session.current_speech
        if current_speech:
            await current_speech.wait_for_playout()

        await self.hangup()

async def entrypoint(ctx: JobContext):
    logger.info(f"\n------------------Connecting to room {ctx.room.name}---------------------\n")

    metadata = json.loads(ctx.job.metadata)

    first_name = metadata['first_name']
    last_name = metadata['last_name']
    balance_to_pay = metadata['balance_to_pay']
    start_date = metadata['start_date']
    last_date = metadata['last_date']
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
            They have a total outstandiing loan repayment balance of Rupees {balance_to_pay}.
            According to their agreement they need to pay Rupees {installment} as monthly installment.
            
            Here are the previous conversation summaries with the customer on WhatsApp and Phone Call.
            Use these conversation summaries for additional context if necessary:
            
            WhatsApp Conversation Summary: {wa_summary}
            
            Phone Call Conversation Summary: {call_summary}
    """
    )

    agent = VoiceAgent(customer_phone=phone[3:] ,chat_ctx=initial_ctx)

    await ctx.connect()

    session = AgentSession(
        stt=agent.stt,
        llm=agent.llm,
        tts=agent.tts,
        vad=agent.vad,
        turn_detection='stt',
        allow_interruptions=True
    )

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

    ctx.add_shutdown_callback(store_history)

    session_started = asyncio.create_task(
        session.start(
            agent=agent,
            room=ctx.room
        )
    )

    try:
        print(f"Creating SIP participant for {customer} at phone number {phone}")
        print(ctx.room.name)
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