# import streamlit as st
# import time
# from backend import fetch_live_transcript_and_latency

# st.set_page_config(page_title="Live Call View", layout="wide")
# st.subheader("User Call Interface")

# user = st.session_state.get("selected_user")

# if not user:
#     st.warning("No user selected. Please start from the main app.")
#     st.stop()

# # st.markdown(f"Active Call with {user['Name']}")
# st.table(user)

# st.divider()

# transcript_area = st.empty()
# latency_chart = st.empty()

# for _ in range(30):  # Simulate real-time transcript stream
#     transcript, latency = fetch_live_transcript_and_latency(user['Phone'])
#     transcript_area.code(transcript, language="text")
#     latency_chart.line_chart(latency)
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

# Display borrower metadata
with st.expander("📋 Borrower Details"):
    for key, value in user.items():
        st.markdown(f"**{key}:** {value}")

# Launch call only once
if not st.session_state.get("call_active"):
    st.session_state["call_active"] = True
    dispatch_call(user["Phone"])

st.divider()

# Stream transcript and latency
transcript_area = st.empty()
latency_chart = st.empty()

for _ in range(30):  # Simulate real-time transcript stream
    transcript, latency = fetch_live_transcript_and_latency(user["Phone"])
    transcript_area.code(transcript or "Waiting for responses...", language="text")
    # if latency:
    #     latency_chart.line_chart(latency)
    time.sleep(2)