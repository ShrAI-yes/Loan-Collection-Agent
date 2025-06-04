# import pandas as pd
# import subprocess
# import time
# from context_manager import UserData, Database

# def read_borrowers(filepath):
#     data = UserData()
#     data.read_file("borrower.csv")
#     df = data.Data
#     df['Name'] = df['F_Name'] + " " + df['L_Name']
#     df['Phone'] = df['Mobile_No']
#     df['Loan Amount'] = df['Loan_amount']
#     df['Preference'] = df.get('Preference', pd.Series(['call'] * len(df)))
#     return df[['Name', 'Phone', 'Loan Amount', 'Preference']]

# import subprocess

# worker_process = None  # Global or class-level if needed

# def dispatch_call(phone_number):
#     global worker_process
#     worker_process = subprocess.Popen(
#         ["python", "LivekitWorker.py"],
#         stdout=subprocess.PIPE,
#         stderr=subprocess.STDOUT,
#         text=True
#     )
#     time.sleep(5)
#     subprocess.run(["python", "job_dispatch.py", str(phone_number)])


# def fetch_live_transcript_and_latency(phone):
#     global worker_process
#     dialogue = []
#     latency = []

#     if worker_process and worker_process.stdout:
#         lines = []
#         for _ in range(10):  # Fetch latest 10 lines
#             line = worker_process.stdout.readline()
#             if not line:
#                 break
#             if "Agent said:" in line or "User said:" in line:
#                 lines.append(line.strip())
#         dialogue = lines

#     # Return lines and dummy latency
#     return "\n".join(dialogue), [1.0] * len(dialogue)

import pandas as pd
import subprocess
import time
from context_manager import UserData, Database

def read_borrowers(filepath):
    data = UserData()
    data.read_file("borrower.csv")
    df = data.Data
    df['Name'] = df['F_Name'] + " " + df['L_Name']
    df['Phone'] = df['Mobile_No']
    df['Loan Amount'] = df['Loan_amount']
    df['Preference'] = df.get('Preference', pd.Series(['call'] * len(df)))
    return df[['Name', 'Phone', 'Loan Amount', 'Preference']]

worker_process = None  # Used to track subprocess state

def dispatch_call(phone_number):
    phone_number = str(phone_number)
    print(f"[DEBUG] dispatch_call called with phone_number={phone_number}")  # DEBUG

    print(f"Dispatching call to {phone_number}")

    global worker_process
    print("[DEBUG] Starting LivekitWorker.py subprocess...")  # DEBUG

    worker_process = subprocess.Popen(
        ["python", "LivekitWorker.py", "dev"],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True
    )
    print("[DEBUG] LivekitWorker.py subprocess started")  # DEBUG
    time.sleep(15)
    print(f"[DEBUG] Running job_dispatch.py for phone_number={phone_number}")  # DEBUG

    subprocess.run(["python", "job_dispatch.py", str(phone_number)])
    print("[DEBUG] job_dispatch.py finished")  # DEBUG

def fetch_live_transcript_and_latency(phone):
    global worker_process
    dialogue = []
    latency = []

    if worker_process and worker_process.stdout:
        for _ in range(10):  # Read latest 10 lines
            line = worker_process.stdout.readline()
            if not line:
                break
            if "Agent said:" in line or "User said:" in line:
                dialogue.append(line.strip())

    return "\n".join(dialogue), [1.0] * len(dialogue)