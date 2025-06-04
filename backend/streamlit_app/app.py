# import streamlit as st
# import pandas as pd
# from backend import read_borrowers, dispatch_call

# st.set_page_config(page_title="Loan Debt Collector", layout="wide")
# st.title("Predixion Loan Debt Collector")

# uploaded_file = st.file_uploader("Upload Borrower CSV", type=["csv"])

# st.divider()

# if uploaded_file:
#     import os
#     os.makedirs("user_files", exist_ok=True)
#     with open("user_files/borrower.csv", "wb") as f:
#         f.write(uploaded_file.getbuffer())

#     df = read_borrowers("user_files/borrower.csv")
#     st.session_state['borrower_df'] = df
#     st.dataframe(df)
    # for i, row in df.iterrows():
    #     col1, col2, col3, col4, col5 = st.columns([2, 2, 2, 2, 2])
    #     with col1: st.write(row['Name'])
    #     with col2: st.write(row['Phone'])
    #     with col3: st.write(row['Loan Amount'])
    #     with col4: st.write(row['Preference'])
    #     with col5:
    #         if row['Preference'].lower() == 'call':
    #             if st.button("\U0001F4DE Call", key=f"call_{i}"):
    #                 st.session_state['selected_user'] = row.to_dict()
    #                 dispatch_call(row['Phone'])
    #                 st.switch_page("call_interface.py")


# app.py
import streamlit as st
import pandas as pd
from backend import read_borrowers

st.set_page_config(page_title="Conversational AI Portal", layout="wide")

st.markdown("""
    <style>
        .main-title {
            text-align: center;
            font-size: 36px;
            color: #1F4E79;
        }
        .subtitle {
            text-align: center;
            font-size: 18px;
            color: #888;
        }
        .status-box {
            border-radius: 10px;
            padding: 15px;
            background-color: #E0E0FF;
            font-weight: bold;
            text-align: center;
        }
    </style>
""", unsafe_allow_html=True)

st.markdown('<div class="main-title">Conversational AI Portal</div>', unsafe_allow_html=True)
st.markdown('<div class="subtitle">Efficient Borrower Communication</div>', unsafe_allow_html=True)
st.write("")

col1, col2 = st.columns([2, 2])

with col1:
    st.header("📁 Upload Borrower")
    uploaded_file = st.file_uploader("Choose File", type=["csv"])
    if uploaded_file:
        with open("user_files/borrower.csv", "wb") as f:
            f.write(uploaded_file.read())
        st.success(f"{uploaded_file.name} uploaded")

        df = read_borrowers("user_files/borrower.csv")
        st.session_state["borrowers"] = df
        selected = st.selectbox(
            "Select Borrower",
            df.itertuples(),
            format_func=lambda row: f"{row.Name} (+91{row.Phone})"
        )
    else:
        selected = None

with col2:
    st.header("📋 Borrower Details")
    if selected:
        st.markdown(f"**Name:** {selected.Name}")
        st.markdown(f"**Phone:** +91{selected.Phone}")
        st.markdown(f"**Preference:** {selected.Preference}")
        st.markdown(f"**Loan Amount:** ₹{selected._3}")

# ---- START CALL ----
st.divider()
if selected:
    if st.button("📞 Start Campaign", use_container_width=True):
        print("[DEBUG] Start Campaign button pressed")  # DEBUG
        st.session_state["selected_user"] = {
            "Name": selected.Name,
            "Phone": selected.Phone,
            "Preference": selected.Preference,
            "Loan Amount": selected._3
        }
        st.session_state["call_active"] = False  # ensure fresh session
        print("[DEBUG] Switching to call_interface.py")  # DEBUG
        st.switch_page("pages/call_interface.py")