# import pandas as pd
# import subprocess
# import time
# from context_manager import UserData

# def read_borrowers(filepath):
#     data = UserData()
#     data.read_file("borrower.csv")
#     df = data.Data
#     df['Name'] = df['F_Name'] + " " + df['L_Name']
#     df['Phone'] = df['Mobile_No']
#     df['Loan Amount'] = df['Loan_amount']
#     df['Preference'] = df.get('Preference', pd.Series(['call'] * len(df)))
#     return df[['Name', 'Phone', 'Loan Amount', 'Preference']]

# worker_process = None  # Used to track subprocess state
# job_dispatch_process = None
# def dispatch_call(phone_number):
#     phone_number = str(phone_number)
#     print(f"[DEBUG] dispatch_call called with phone_number={phone_number}")  # DEBUG

#     print(f"Dispatching call to {phone_number}")

#     global worker_process
#     print("[DEBUG] Starting LivekitWorker.py subprocess...")  # DEBUG

#     worker_process = subprocess.Popen(
#         ["python", "LivekitWorker.py", "dev"],
#         stdout=subprocess.PIPE,
#         stderr=subprocess.STDOUT,
#         text=True,
#         bufsize=1,  # Line buffered
#     )
#     print("[DEBUG] LivekitWorker.py subprocess started")  # DEBUG
#     time.sleep(15)
#     print(f"[DEBUG] Running job_dispatch.py for phone_number={phone_number}")  # DEBUG

#     subprocess.run(["python", "job_dispatch.py", str(phone_number)])
#     print("[DEBUG] job_dispatch.py finished")  # DEBUG

# # def fetch_live_transcript_and_latency(phone):
# #     global worker_process
# #     dialogue = []
# #     latency = []

# #     if worker_process and worker_process.stdout:
# #         for _ in range(10):  # Read latest 10 lines
# #             line = worker_process.stdout.readline()
# #             if not line:
# #                 break
# #             if "Agent said:" in line or "User said:" in line:
# #                 dialogue.append(line.strip())

# #     return "\n".join(dialogue), [1.0] * len(dialogue)
# def fetch_live_transcript_and_latency(phone):
#     global worker_process
#     dialogue = []
#     latency = []

#     # Read all output so far from the worker process
#     if worker_process and worker_process.stdout:
#         # Read all lines currently available (non-blocking)
#         output = worker_process.stdout.read()
#         for line in output.splitlines():
#             if "Agent said:" in line or "User said:" in line:
#                 dialogue.append(line.strip())

#     # Return the entire transcript so far
#     return "\n".join(dialogue), [1.0] * len(dialogue)

import pandas as pd
import subprocess
import time
from context_manager import UserData, Database

worker_process = None
job_dispatch_process = None

def read_borrowers(filepath):
    data = UserData()
    data.read_file("borrower.csv")
    df = data.Data
    df['Name'] = df['F_Name'] + " " + df['L_Name']
    df['Phone'] = df['Mobile_No']
    df['Loan Amount'] = df['Loan_amount']
    df['Preference'] = df.get('Preference', pd.Series(['call'] * len(df)))
    return df[['Name', 'Phone', 'Loan Amount', 'Preference']]

def dispatch_call(phone_number):
    global worker_process, job_dispatch_process
    phone_number = str(int(float(phone_number)))  # Handle scientific notation
    
    # Start LivekitWorker in dev mode
    worker_process = subprocess.Popen(
        ["python", "LivekitWorker.py", "dev"],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
        universal_newlines=True
    )
    
    # Start job_dispatch with phone number
    job_dispatch_process = subprocess.Popen(
        ["python", "job_dispatch.py", phone_number],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
        universal_newlines=True
    )

    # Start thread to print outputs
    import threading
    def print_output(process, name):
        while True:
            output = process.stdout.readline()
            if output == '' and process.poll() is not None:
                break
            if output:
                print(f"[{name}] {output.strip()}")
    
    threading.Thread(target=print_output, args=(worker_process, "LivekitWorker"), daemon=True).start()
    threading.Thread(target=print_output, args=(job_dispatch_process, "JobDispatch"), daemon=True).start()
    
    return worker_process, job_dispatch_process
    
def fetch_live_transcript_and_latency(phone):
    global worker_process
    transcript = []
    
    if worker_process and worker_process.stdout:
        # Read all available output without blocking
        while True:
            line = worker_process.stdout.readline()
            if not line:
                break
            if "Agent said:" in line or "User said:" in line:
                transcript.append(line.strip())
    
    # Return complete transcript history
    return "\n".join(transcript[-10:]), []