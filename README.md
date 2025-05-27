# Voice Agent with Livekit Telephony Integration 

This is a stand-alone Livekit Voice Agent integrated with Twillio.

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

### 5. Change the Phone Number in [job_dispatch.py](https://github.com/ShrAI-yes/Loan-Collection-Agent/blob/Livekit/job_dispatch.py). 
* Change the 'phone_no' variable to your 10-digit phone number to get Voice Agent call on your phone.   
* Save the file

### 6. Run the File
* In command prompt, activate the environment and then run 'python livekit_test.py dev'. This will initialize the Voice Agent and wait to recieve Livekit Job Requests.
* Seperately run the 'job_dispatch.py' file. This will send a Job Request along with your details to the running Voice Agent instance and initiate the call.


