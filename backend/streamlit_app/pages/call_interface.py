# import streamlit as st
# import time
# from backend import dispatch_call, fetch_live_transcript_and_latency

# st.set_page_config(page_title="Live Call View", layout="wide")
# st.title("📞 Live Call Session")

# user = st.session_state.get("selected_user")
# if not user:
#     st.warning("No user selected. Please start from the main app.")
#     st.stop()

# st.subheader(f"Active Call with {user['Name']}")

# # Display borrower metadata
# with st.expander("📋 Borrower Details"):
#     for key, value in user.items():
#         st.markdown(f"**{key}:** {value}")

# # Launch call only once
# if not st.session_state.get("call_active"):
#     st.session_state["call_active"] = True
#     dispatch_call(user["Phone"])

# st.divider()

# # Stream transcript and latency
# transcript_area = st.empty()
# latency_chart = st.empty()

# # for _ in range(30):  # Simulate real-time transcript stream
# #     transcript, latency = fetch_live_transcript_and_latency(user["Phone"])
# #     transcript_area.code(transcript or "Waiting for responses...", language="text")
# #     # if latency:
# #     #     latency_chart.line_chart(latency)
# #     time.sleep(2)

# for _ in range(30):  # Simulate real-time transcript stream
#     transcript, latency = fetch_live_transcript_and_latency(user["Phone"])
#     # Only append new lines
#     new_lines = [line for line in transcript.splitlines() if line not in st.session_state["full_transcript"]]
#     st.session_state["full_transcript"].extend(new_lines)
#     transcript_area.code("\n".join(st.session_state["full_transcript"]) or "Waiting for responses...", language="text")
#     time.sleep(2)


import streamlit as st
import time
from backend import dispatch_call, fetch_live_transcript_and_latency

st.set_page_config(page_title="Live Call View", layout="wide")
st.title("📞 Live Call Session")

user = st.session_state.get("selected_user")
if not user:
    st.warning("No user selected. Please start from the main app.")
    st.stop()

st.subheader(f"Active Call with {user['Name']}")

# Initialize transcript in session state
if 'full_transcript' not in st.session_state:
    st.session_state.full_transcript = []

# Display borrower metadata
with st.expander("📋 Borrower Details"):
    for key, value in user.items():
        st.markdown(f"**{key}:** {value}")

# Launch call only once
if not st.session_state.get("call_active"):
    st.session_state["call_active"] = True
    dispatch_call(user["Phone"])

st.divider()

# Stream transcript
transcript_area = st.empty()

while st.session_state.get("call_active", True):
    transcript, _ = fetch_live_transcript_and_latency(user["Phone"])
    if transcript:
        st.session_state.full_transcript.append(transcript)
    
    # Display last 20 lines of conversation
    transcript_area.code("\n".join(st.session_state.full_transcript[-20:]), language="text")
    time.sleep(1)