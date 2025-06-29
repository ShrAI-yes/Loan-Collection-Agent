
import os
from livekit.agents.metrics import LLMMetrics, STTMetrics, TTSMetrics, EOUMetrics

def serialize_metrics(obj):
    """
    Serializes a Livekit Metric object into a dictionary.

    This function checks if the input object is an instance of a Livekit Metric class
    (LLMMetrics, STTMetrics, TTSMetrics, or EOUMetrics) and returns its
    __dict__ representation.

    Args:
        obj (object): The object to be serialized.

    Returns:
        dict or None: A dictionary representation of the object's attributes if
                      it's a supported metric type, otherwise None.
    """

    if isinstance(obj, (LLMMetrics, STTMetrics, TTSMetrics, EOUMetrics)):
        return obj.__dict__

def save_to_file(file_content, filename):
    """
    Saves the provided content to a text file in a 'log_metrics' directory.

    If the 'log_metrics' directory does not exist in the same directory as the
    script, it will be created. The content is then written to a file with the
    specified filename and a '.txt' extension.

    Args:
        file_content (str): The content to be written to the file.
        filename (str): The name of the file to save the content to (without the extension).
    """

    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'log_metrics')

    if not os.path.exists(path):
        os.makedirs(path)

    try:
        with open(os.path.join(path,f"{filename}.txt"),"w") as file:
            file.write(file_content)

    except Exception as e:
        print(e)