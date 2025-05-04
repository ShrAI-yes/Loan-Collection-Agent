
import os
import time, datetime, pytz
from dotenv import load_dotenv
load_dotenv()

from Prompt import load_prompt
from superAgent import SuperAgent

from livekit import agents
from livekit.agents import AgentSession, Agent
from livekit.agents import function_tool, RunContext, ChatContext, JobContext
from livekit.agents import RoomInputOptions

from livekit.plugins import (
    groq,
    elevenlabs,
    deepgram,
    silero
)
from livekit.plugins.turn_detector.multilingual import MultilingualModel


@function_tool()
async def current_date_time(
    context:RunContext
) -> dict:

    """Returns the current server date and time in JSON format."""
    now = datetime.datetime.now()
    ist_timezone = pytz.timezone('Asia/Kolkata')
    dt_ist = now.astimezone(ist_timezone)
    current_time = dict()
    current_time['day'] = dt_ist.strftime('%A')
    current_time['month'] = dt_ist.strftime('%B')
    current_time['date'] = dt_ist.strftime('%Y-%m-%d')
    current_time['time'] = dt_ist.strftime('%H:%M')
    return current_time

@function_tool()
async def get_user_data(
        context:RunContext
) -> dict:
    """Returns all information about the customer and their loan details."""
    supagent = SuperAgent()
    supagent.read_document('borrower.csv')
    context = supagent.agent_context(7700979995) #Change Phone Number Here
    user_data = {key: value for key, value in context.items() if key not in ('whatsapp_summary', 'call_summary')}
    return user_data

class VoiceAgent(Agent):
    def __init__(self, chat_ctx: ChatContext) -> None:
        super().__init__(
            instructions=load_prompt('voice_agent.yaml'),
            tools=[current_date_time,get_user_data],
            chat_ctx=chat_ctx
        )

async def entrypoint(ctx: agents.JobContext):
    await ctx.connect()

    supagent = SuperAgent()
    supagent.read_document('borrower.csv')
    user_info = supagent.agent_context(7700979995) #Change Phone Number Here

    session = AgentSession(
        stt=deepgram.STT(
            model="nova-3",
            language="multi",
            api_key=os.getenv('DEEPGRAM_API_KEY')
        ),
        llm=groq.LLM(
            model="llama3-8b-8192",
            api_key=os.getenv('GROQ_API_KEY')
        ),
        tts=elevenlabs.TTS(
            voice_id="wlmwDR77ptH6bKHZui0l",
            model="eleven_multilingual_v2",
            api_key=os.getenv('ELEVEN_API_KEY')
        ),
        vad=silero.VAD.load(),
        turn_detection=MultilingualModel(),
    )

    initial_ctx = ChatContext()
    initial_ctx.add_message(
        role="system",
        content=f"""User Information:
        ('first_name')={user_info['first_name']},
        ('last_name')={user_info['last_name']},
        ('balance_to_pay')={user_info['balance_to_pay']},
        ('start_date')={user_info['start_date']}
        ('last_date')={user_info['last_date']}
        ('installment')={user_info['installment']}"""
    )

    await session.start(
        room=ctx.room,
        agent=VoiceAgent(
            chat_ctx=initial_ctx
        )
    )

    await session.generate_reply(
        instructions="Greet the customer"
    )

if __name__ == "__main__":
    agents.cli.run_app(agents.WorkerOptions(entrypoint_fnc=entrypoint))