
import pandas as pd
import subprocess
import time
from context_manager import UserData, Database

import os
import json

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
    # return df[['Name', 'Phone', 'Loan Amount', 'Preference']]
    return df[['F_Name', 'L_Name', 'Mobile_No', 'Name', 'Phone', 'Loan Amount', 'Preference']]

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
    time.sleep(15)  # Wait for worker to initialize
    threading.Thread(target=print_output, args=(job_dispatch_process, "JobDispatch"), daemon=True).start()
    
    return worker_process, job_dispatch_process


def fetch_conversation_history(phone_number):
    """Fetches the conversation history for a given phone number from supabase."""
    db = Database()
    ref = db.init_user(phone=phone_number)
    history = db.get_convo(ref, agent='voice')
    return history

def fetch_metrics(phone_number):
    """Fetches the most recent call metrics file for the given phone number from log_metrics."""
    folder_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'log_metrics')
    if not os.path.exists(folder_path):
        return "No metrics directory found."

    # Filter for files matching pattern
    matching_files = [f for f in os.listdir(folder_path) if f.startswith(f"+91{phone_number}_CallMetrics_") and f.endswith(".txt")]
    if not matching_files:
        return "No metrics file found for this user."

    # Sort by date/time in filename (assumes they are formatted correctly)
    matching_files.sort(reverse=True)
    latest_file = matching_files[0]

    try:
        with open(os.path.join(folder_path, latest_file), 'r') as f:
            metrics_content = f.read()
            return metrics_content
    except Exception as e:
        return f"Error reading metrics: {str(e)}"


def stop_worker():
    global worker_process, job_dispatch_process
    if worker_process and worker_process.poll() is None:
        worker_process.terminate()
        worker_process.wait(timeout=5)
        worker_process = None
    if job_dispatch_process and job_dispatch_process.poll() is None:
        job_dispatch_process.terminate()
        job_dispatch_process.wait(timeout=5)
        job_dispatch_process = None