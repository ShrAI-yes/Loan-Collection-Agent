import os
from dotenv import load_dotenv
load_dotenv()

import asyncio
import numpy as np
import json
from superAgent import SuperAgent
import sys
from livekit import api
from livekit.api import CreateRoomRequest


async def create_explicit_dispatch(customer_phone : int):
    print(f"[DEBUG] create_explicit_dispatch called with customer_phone={customer_phone}")  # DEBUG
    LIVEKIT_URL = os.getenv('LIVEKIT_URL')
    LIVEKIT_API_KEY = os.getenv("LIVEKIT_API_KEY")
    LIVEKIT_API_SECRET = os.getenv("LIVEKIT_API_SECRET")
    room_name = f'livekit_room_{np.random.randint(10 ** 8, 10 ** 9 - 1)}'

    print("[DEBUG] Instantiating SuperAgent...")  # DEBUG
    superagent = SuperAgent()
    superagent.read_document('borrower.csv')
    user_info = superagent.agent_context(customer_phone)
    print(f"[DEBUG] user_info: {user_info}")  # DEBUG

    metadata = {
        'phone': f"+91{customer_phone}",
        'first_name': user_info['first_name'],
        'last_name': user_info['last_name'],
        'balance_to_pay': user_info['balance_to_pay'],
        'start_date': user_info['start_date'],
        'last_date': user_info['last_date'],
        'installment': user_info['installment'],
        'whatsapp_summary': user_info['whatsapp_summary'],
        'call_summary': user_info['call_summary']
    }
    # print(metadata)
    print(f"[DEBUG] Metadata for dispatch: {metadata}")  # DEBUG


    lkapi = api.LiveKitAPI(
        url=LIVEKIT_URL,
        api_key=LIVEKIT_API_KEY,
        api_secret=LIVEKIT_API_SECRET
    )
    print("[DEBUG] Creating LiveKit room...")  # DEBUG

    room = await lkapi.room.create_room(CreateRoomRequest(
        name=room_name,
        empty_timeout=30,
        max_participants=2,
    ))
    print(f"[DEBUG] Room created: {room}")  # DEBUG

    print("[DEBUG] Creating agent dispatch...")  # DEBUG

    dispatch = await lkapi.agent_dispatch.create_dispatch(
        api.CreateAgentDispatchRequest(
            agent_name='Predixion-Voice-Agent',
            room=room_name,
            metadata= json.dumps(metadata)
        )
    )
    # print(f"[DEBUG] Dispatch created: {dispatch}")  # DEBUG
    print(f"Created following dispatch to phone number {customer_phone}:\n {dispatch}")

    dispatches = await lkapi.agent_dispatch.list_dispatch(room_name=room_name)
    print(f"[DEBUG] There are {len(dispatches)} dispatches in {room_name}")  # DEBUG

    # print(f"There are {len(dispatches)} dispatches in {room_name}")
    await lkapi.aclose()


#--------------------Use Case: Change the 'customer_phone= 10-digit phone number' in main function--------------------------#
# if __name__ == '__main__':
#     asyncio.run(create_explicit_dispatch(customer_phone=7208303007))
if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Error: Phone number not provided.")
        sys.exit(1)

    try:
        phone = int(sys.argv[1])  # Convert argument to integer
    except ValueError:
        print("Invalid phone number format.")
        sys.exit(1)

    asyncio.run(create_explicit_dispatch(customer_phone=phone))