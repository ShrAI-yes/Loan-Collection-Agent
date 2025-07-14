import streamlit as st
import pandas as pd
from backend import read_borrowers

st.set_page_config(page_title="PredixionAI Loan Collection Agent", layout="wide")

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
# st.markdown('<div class="subtitle">Efficient Borrower Communication</div>', unsafe_allow_html=True)
st.write("")

borrower = None

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
        # print(df.head())
        
        borrower_options = []
        borrower_rows = []
        for row in df.itertuples():
            borrower_options.append(f"{row.F_Name} {row.L_Name} : {row.Mobile_No}")
            borrower_rows.append(row)

        selected_idx = st.selectbox(
            "Select Borrower",
            range(len(borrower_options)),
            format_func=lambda i: borrower_options[i] if borrower_options else ""
        )
        borrower = borrower_rows[selected_idx] if borrower_options else None
        # print("Selected :", borrower)
            
    else:
        selected = None

with col2:
    st.session_state.setdefault("borrowers", pd.DataFrame())
    st.header("📋 Borrower Details")
    if borrower:
        st.markdown(f"**Name:** {borrower.F_Name} {borrower.L_Name}")
        st.markdown(f"**Phone:** {borrower.Mobile_No}")
        # st.markdown(f"**Loan Amount:** ₹{getattr(borrower, 'Loan_amount', '')}")
        st.markdown(f"**Loan Amount:** ₹{borrower._6}")
    
    else:
        borrower = None
        st.markdown("No borrower selected. Please upload a file and select a borrower.")

# ---- START CALL ----
st.divider()
if borrower:
    if st.button("📞 Start Campaign", use_container_width=True):
        print("[DEBUG] Start Campaign button pressed")  # DEBUG
        st.session_state["selected_user"] = {
            "Name": borrower.Name,
            "Phone": borrower.Phone,
            "Preference": borrower.Preference,
            "Loan Amount": borrower._6
        }
        st.session_state["call_active"] = False  # ensure fresh session
        print("[DEBUG] Switching to call_interface.py")  # DEBUG
        st.switch_page("pages/call_interface.py")