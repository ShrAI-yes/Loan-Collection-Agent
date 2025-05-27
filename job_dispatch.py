##
import os
from dotenv import load_dotenv
load_dotenv()

import asyncio
import json
from superAgent import SuperAgent

from livekit import api
from livekit.api import CreateRoomRequest

LIVEKIT_URL = os.getenv('LIVEKIT_URL')
LIVEKIT_API_KEY = os.getenv("LIVEKIT_API_KEY")
LIVEKIT_API_SECRET = os.getenv("LIVEKIT_API_SECRET")

phone_no = 7700979995
room_name = 'my-sip-room'

supagent = SuperAgent()
supagent.read_document('borrower.csv')
user_info = supagent.agent_context(phone_no)

metadata = {
    'phone' : f"+91{phone_no}",
    'first_name' : user_info['first_name'],
    'last_name': user_info['last_name'],
    'balance_to_pay' : user_info['balance_to_pay'],
    'start_date' : user_info['start_date'],
    'last_date' : user_info['last_date'],
    'installment' : user_info['installment']
}

async def create_explicit_dispatch():
    lkapi = api.LiveKitAPI(
        url="wss://loan-agent-kizvtg5x.livekit.cloud",  # Replace with your LiveKit server URL
        api_key="APIiiDz7SFzAkJt",  # Replace with your LiveKit API key
        api_secret="AFrTpDWMI5nIfuXbT8e2VOtYL4cugGPiTXTeevcUPuZA"
    )

    room = await lkapi.room.create_room(CreateRoomRequest(
        name=room_name,
        empty_timeout=10 * 60,
        max_participants=20,
    ))

    dispatch = await lkapi.agent_dispatch.create_dispatch(
        api.CreateAgentDispatchRequest(
            agent_name='Voice_Agent_Riya',
            room=room_name,
            metadata= json.dumps(metadata)
        )
    )
    print("created dispatch", dispatch)

    dispatches = await lkapi.agent_dispatch.list_dispatch(room_name=room_name)
    print(f"there are {len(dispatches)} dispatches in {room_name}")
    await lkapi.aclose()

asyncio.run(create_explicit_dispatch())