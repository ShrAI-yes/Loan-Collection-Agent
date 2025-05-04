#Voice Agent with Livekit CLI 
NOTE: Telephony Integration with Twillio is not present. The Phone Number is hard-coded in the code-file and needs to be changed to your phone number.

By running the [livekit_test.py](https://github.com/ShrAI-yes/Loan-Collection-Agent/blob/Livekit/livekit_test.py) file the Voice Agent will run in your Console Window using your system Microphone. 


---



# How To Run Voice Agent Pipeline

### 1. Install necessary libraries  
pip install livekit-agents[deepgram,groq,elevenlabs,silero,turn-detector]~=1.0\

### 2. Create Livekit Cloud Account
* Create a Livekit Cloud API key and API secret.

### 3. Create '.env' File for API keys
Keys to include:
* DEEPGRAM_API_KEY
* GROQ_API_KEY
* ELEVEN_API_KEY
* LIVEKIT_API_KEY (From Livekit CLoud Settings -> Keys)
* LIVEKIT_API_SECRET (From Livekit CLoud Settings -> Keys) 
* LIVEKIT_URL (From Livekit CLoud Settings-> Projects)          

### 4. Add your details in CSV
* Add your details in the [borrower.csv](https://github.com/ShrAI-yes/Loan-Collection-Agent/blob/Livekit/borrower.csv) file in user_files/ directory

### 5. Change the Phone Number in [livekit_test.py](https://github.com/ShrAI-yes/Loan-Collection-Agent/blob/Livekit/livekit_test.py). 
* Phone number needs to be changed in 2 lines. I have commented where to change them.

### 6. Run the File
* In command prompt, activate the environment and then run 'python livekit_test.py console'.
* The Agent will intitalize (approx. 10s) and then start talking with you.


