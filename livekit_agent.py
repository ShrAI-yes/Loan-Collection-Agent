##
import asyncio
from livekit.agents import AutoSubscribe, JobContext, WorkerOptions, cli, llm
from livekit.agents.voice_assistant import VoiceAssistant
from livekit.plugins import openai, silero

##
OPENAI_API = ""

LIVEKIT_URL = ""
LIVEKTI_API = ""
LK_SECRET = ""

##
async def entrypoint(ctx: JobContext):
    initial_ctx = llm.ChatContext().append(
        role="system",
        text="""You are an intelligent virtual financial agent helping our customer.
                Your role is to help manage the customer's loan repayment and answer their financial questions in a clear and precise way. 

                Instructions:
                1. Use precise financial language and ensure clear, accurate information.
                2. If the user is willing to pay the loan then please provide this link '''https://paymentUSER1UDN.com'''. Do not send the link until user requests or user wants to pay the loan.
                3. If the customer is struggling, provide options like grace periods, payment restructuring, or deadline extensions considering their income, number of late repayment and loan amount yet to be repayed.
                4. Keep responses short and to the point.
                5. Ensure confidentiality and remind the customer to keep their payment details secure.
                6. You can only extend the last loan repayment date by a maximum of 10 days if user requests for grace periods or deadline extensions considering their income, number of late repayment and loan amount yet to be repayed.
                7. If the question cannot be answered using the information provided, reply with "Sorry, but I am unable to answer this query".
            """
    )

    await ctx.connect(auto_subscribe=AutoSubscribe.AUDIO_ONLY)

    agent = VoiceAssistant(
        vad=silero.VAD.load(),
        stt=openai.STT(api_key=OPENAI_API), #Change the plugin here
        tts=openai.TTS(api_key=OPENAI_API), #Change the plugin here
        llm=openai.TTS(api_key=OPENAI_API),
        chat_ctx=initial_ctx
    )

    agent.start(ctx.room)
    await asyncio.sleep(1)

    await agent.say('Hello! I have called to remind you about your loan reapyment', allow_interruptions=False)

##
if __name__ == '__main__':
    cli.run_app(WorkerOptions(
        entrypoint_fnc=entrypoint,
        api_key=LIVEKTI_API,
        api_secret=LK_SECRET,
        ws_url=LIVEKIT_URL
    ))