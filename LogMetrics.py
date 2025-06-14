
import os
import json
from livekit.agents.metrics import LLMMetrics, STTMetrics, TTSMetrics, EOUMetrics

def serialize_metrics(obj):
    if isinstance(obj, (LLMMetrics, STTMetrics, TTSMetrics, EOUMetrics)):
        return obj.__dict__

def save_to_file(file_content, filename):

    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'log_metrics')

    if not os.path.exists(path):
        os.makedirs(path)

    #content = json.dumps(file_content, indent=4, default=serialize_metrics)

    try:
        with open(os.path.join(path,f"{filename}.txt"),"w") as file:
            file.write(file_content)

    except Exception as e:
        print(e)