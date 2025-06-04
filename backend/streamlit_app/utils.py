# streamlit_app/utils.py

import pandas as pd

def calculate_latency(transcript):
    latency = []
    last_time = None
    for entry in transcript:
        ts = pd.to_datetime(entry.get("timestamp"))
        if last_time:
            latency.append((ts - last_time).total_seconds())
        last_time = ts
    return latency
# def format_transcript(transcript):
#     formatted = []
#     for entry in transcript:
#         speaker = entry.get("speaker", "Unknown")
#         text = entry.get("text", "")
#         timestamp = entry.get("timestamp", "")
#         formatted.append(f"{timestamp} - {speaker}: {text}")
#     return "\n".join(formatted)