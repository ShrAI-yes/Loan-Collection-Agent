import logging
logger = logging.getLogger("outbound-caller")
logger.setLevel(logging.INFO)

import json
import datetime, pytz
import asyncio
import os
from dotenv import load_dotenv
load_dotenv()

from livekit import agents
from livekit import api, rtc
from livekit.agents import AgentSession, Agent, WorkerOptions
from livekit.agents import function_tool, get_job_context, RunContext, ChatContext, JobContext, RoomInputOptions
from livekit.plugins import (
    groq,
    elevenlabs,
    deepgram,
    silero
)


LIVEKIT_URL = 'wss://loan-agent-kizvtg5x.livekit.cloud'
LIVEKIT_API_KEY = 'APIiiDz7SFzAkJt'
LIVEKIT_API_SECRET = 'AFrTpDWMI5nIfuXbT8e2VOtYL4cugGPiTXTeevcUPuZA'

DEEPGRAM_API_KEY = os.getenv("DEEPGRAM_API_KEY")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
ELEVENLABS_API_KEY = os.getenv("ELEVEN_API_KEY")


class VoiceAgent(Agent):
    def __init__(self, chat_ctx: ChatContext) -> None:
        super().__init__(
            instructions="""
            You are a professional and friendly FEMALE credit card payment assistant from Predixion AI named Riya. 
            Your job is to help customers understand their outstanding balance, send reminders for upcoming payments, 
            offer repayment options to eligible customers, and ensure a smooth repayment experience while maintaining a polite and empathetic tone.

            Generate conversational responses in simple Hindi or English according to the customer's input language.

            **Generate responses in a single line without any line breaks.**

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
                voice_id="mActWQg9kibLro6Z2ouY",
                model="eleven_multilingual_v2",
                api_key=ELEVENLABS_API_KEY
            ),
            vad=silero.VAD.load()
        )

    async def hangup(self):
        """Helper function to hang up the call by deleting the room"""
        job_ctx = get_job_context()
        await job_ctx.api.room.delete_room(
            api.DeleteRoomRequest(
                room=job_ctx.room.name,
            )
        )

    @function_tool()
    async def current_date_time(self, context: RunContext) -> dict:
        """Returns the current server day, date and time in JSON format."""
        now = datetime.datetime.now()
        ist_timezone = pytz.timezone('Asia/Kolkata')
        dt_ist = now.astimezone(ist_timezone)

        current_time = dict()
        current_time['day'] = dt_ist.strftime('%A')
        current_time['date'] = f"{dt_ist.day} {dt_ist.strftime('%B')}, {dt_ist.year}"
        current_time['time'] = dt_ist.strftime('%I:%M %p')
        return current_time

    @function_tool()
    async def end_call(self, ctx: RunContext):
        """Called when the user wants to end the call"""
        logger.info(f"Ending the call")

        # let the agent finish speaking
        current_speech = ctx.session.current_speech
        if current_speech:
            await current_speech.wait_for_playout()

        await self.hangup()

async def entrypoint(ctx: JobContext):
    logger.info(f"connecting to room {ctx.room.name}")

    metadata = json.loads(ctx.job.metadata)
    phone = metadata['phone']

    first_name = metadata['first_name']
    last_name = metadata['last_name']
    balance_to_pay = metadata['balance_to_pay']
    start_date = metadata['start_date']
    last_date = metadata['last_date']
    installment = metadata['installment']
    customer = f'{first_name} {last_name}'

    initial_ctx = ChatContext()
    initial_ctx.add_message(
        role='system',
        content=f"""
            You are talking to our customer named {first_name} {last_name}.
            They have a total outstandiing loan repayment balance of Rupees {balance_to_pay}.
            According to their agreement they need to pay Rupees {installment} as monthly installment.
    """
    )

    agent = VoiceAgent(chat_ctx=initial_ctx)

    await ctx.connect()

    session = AgentSession(
        stt=agent.stt,
        llm=agent.llm,
        tts=agent.tts,
        vad=agent.vad,
        turn_detection='stt',
        allow_interruptions=True
    )

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
                sip_trunk_id='ST_7apPJUZRJ4kH',
                sip_call_to=phone,
                participant_identity=customer,
                wait_until_answered=True
            )
        )
        # wait for the agent session start and participant join
        await session_started
        participant = await ctx.wait_for_participant(identity=f'{first_name} {last_name}')
        logger.info(f"participant joined: {participant.identity}")
        await session.generate_reply(instructions="Greet the user with their name.")

    except api.TwirpError as e:
        logger.error(
            f"error creating SIP participant: {e.message}, "
            f"SIP status: {e.metadata.get('sip_status_code')} "
            f"{e.metadata.get('sip_status')}"
        )
        ctx.shutdown()


if __name__ == "__main__":
    agents.cli.run_app(
        WorkerOptions(
            entrypoint_fnc=entrypoint,
            agent_name="Voice_Agent_Riya",
            ws_url=LIVEKIT_URL,
            api_key=LIVEKIT_API_KEY,
            api_secret=LIVEKIT_API_SECRET
        )
    )
