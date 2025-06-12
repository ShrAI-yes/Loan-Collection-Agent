
import os
from dotenv import load_dotenv
load_dotenv()

import asyncio
import numpy as np
import json
from superAgent import SuperAgent

from livekit import api
from livekit.api import CreateRoomRequest


async def create_explicit_dispatch(customer_phone : int):
    LIVEKIT_URL = os.getenv('LIVEKIT_URL')
    LIVEKIT_API_KEY = os.getenv("LIVEKIT_API_KEY")
    LIVEKIT_API_SECRET = os.getenv("LIVEKIT_API_SECRET")
    room_name = f'livekit_room_{np.random.randint(10 ** 8, 10 ** 9 - 1)}'

    superagent = SuperAgent()
    superagent.read_document('borrower.csv')
    user_info = superagent.agent_context(customer_phone)

    metadata = {
        'phone': f"+91{customer_phone}",
        'first_name': user_info['first_name'],
        'last_name': user_info['last_name'],
        'balance_to_pay': user_info['balance_to_pay'],
        'installment': user_info['installment'],
        'due_date': '2025-06-15',
        'pending_days': '10',
        'outstanding_amount': user_info['balance_to_pay'],
        'minimum_due_amount': '1000',
        'late_fees': '500',
        'interest_rate': user_info['interest_rate'],
        'emi_eligible': 'True',
        'whatsapp_summary': user_info['whatsapp_summary'],
        'call_summary': user_info['call_summary'],
    }

    lkapi = api.LiveKitAPI(
        url=LIVEKIT_URL,
        api_key=LIVEKIT_API_KEY,
        api_secret=LIVEKIT_API_SECRET
    )

    room = await lkapi.room.create_room(CreateRoomRequest(
        name=room_name,
        empty_timeout=30,
        max_participants=2,
    ))

    dispatch = await lkapi.agent_dispatch.create_dispatch(
        api.CreateAgentDispatchRequest(
            agent_name='Predixion-Voice-Agent',
            room=room_name,
            metadata= json.dumps(metadata)
        )
    )
    print(f"Created following dispatch to phone number {customer_phone}:\n {dispatch}")

    dispatches = await lkapi.agent_dispatch.list_dispatch(room_name=room_name)
    print(f"There are {len(dispatches)} dispatches in {room_name}")
    await lkapi.aclose()


#--------------------Use Case: Change the 'customer_phone= 10-digit phone number' in main function--------------------------#
if __name__ == '__main__':
    asyncio.run(create_explicit_dispatch(customer_phone=7700979995))