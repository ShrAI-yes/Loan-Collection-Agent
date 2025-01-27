#!/usr/bin/env python
# coding: utf-8

# In[1]:


import os
import time
import pandas as pd
import pygame
from io import BytesIO
from gtts import gTTS
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from langchain_mistralai import ChatMistralAI
import speech_recognition as sr  


# In[2]:


# Text-to-speech function
def speak_text(text):
    try:
        tts = gTTS(text=text, lang='en')
        mp3_fp = BytesIO()  # Create in-memory file object
        tts.write_to_fp(mp3_fp)
        mp3_fp.seek(0)  # Rewind to the beginning of the file

        pygame.mixer.init()  # Initialize mixer (do this ONCE in your program)
        pygame.mixer.music.load(mp3_fp)
        pygame.mixer.music.play()

        while pygame.mixer.music.get_busy():
            pygame.time.Clock().tick(10)

    except Exception as e:
        print(f"Error: {e}")


# In[ ]:





# In[3]:


import time
import pygame
from gtts import gTTS
from io import BytesIO

def speak_text(text):
    try:
        start_time = time.time()

        tts = gTTS(text=text, lang='en')
        mp3_fp = BytesIO()
        tts.write_to_fp(mp3_fp)
        mp3_fp.seek(0)

        pygame.mixer.init()
        pygame.mixer.music.load(mp3_fp)
        pygame.mixer.music.play()

        while pygame.mixer.music.get_busy():
            pygame.time.Clock().tick(10)

        end_time = time.time()
        latency = end_time - start_time
        print(f"Latency: {latency:.4f} seconds")

    except Exception as e:
        print(f"Error: {e}")


# In[4]:


# Function to fetch borrower data based on name
def search_by_name(name, file_path="Demo1.csv"):
    try:
        data = pd.read_csv(file_path)
        # Now search for Borrower Name in the correct column
        borrower = data[data['Borrower Name'].str.lower() == name.lower()].to_dict(orient='records')
        return borrower[0] if borrower else None
    except FileNotFoundError:
        print(f"Error: File {file_path} not found.")
        return None


# In[5]:


# Function to fetch borrower data based on phone number
def search(phone_number, file_path="Demo1.csv"):
    try:
        data = pd.read_csv(file_path)
        borrower = data[data['Phone Number'] == phone_number].to_dict(orient='records')
        return borrower[0] if borrower else None
    except FileNotFoundError:
        print(f"Error: File {file_path} not found.")
        return None


# In[6]:


import speech_recognition as sr
import time

def listen_for_name_or_exit():
    recognizer = sr.Recognizer()
    with sr.Microphone() as source:
        print("Listening for name or exit command...")
        recognizer.adjust_for_ambient_noise(source)
        audio = recognizer.listen(source)

        try:
            response = recognizer.recognize_google(audio)
            print(f"Customer's response: {response}")
            # Check if the response contains "bye" or "quit"
            if response.lower() in ["bye", "quit"]:
                return "exit"
            return response
        except sr.UnknownValueError:
            print("Sorry, I couldn't understand the response. Please try again.")
            return None
        except sr.RequestError:
            print("Sorry, I'm having trouble connecting to the speech recognition service.")
            return None

def initiate_call(phone_number):
    # Fetch borrower data
    borrower_data = search(phone_number)
    if not borrower_data:
        print(f"No data found for phone number: {phone_number}.")
        return

    # Borrower details
    agent_name = "Malti"
    company_name = "Predixion AI"
    borrower_name = borrower_data.get("Borrower Name", "Valued Customer")

    # Agent introduction and asking for the customer's name
    intro = f"Hi, I’m {agent_name} calling from {company_name}. Could you please tell me your first name?"
    speak_text(intro)

    transcript = []  # Initialize transcript list
    transcript.append(f"Bot: {intro}")

    while True:
        # Listen for the customer's name or exit command
        customer_response = listen_for_name_or_exit()
        if customer_response == "exit":
            disconnect_message = "Thank you for your time. Goodbye!"
            print("Call disconnected by the customer.")
            speak_text(disconnect_message)
            transcript.append(f"Customer: Bye/Quit")
            transcript.append(f"Bot: {disconnect_message}")
            save_transcript(transcript, phone_number)
            return
        elif customer_response:
            customer_name = customer_response
            transcript.append(f"Customer: {customer_name}")
            break

    # Cross-verify name with Demo1.csv
    matched_data = search_by_name(customer_name)
    if matched_data:
        print(f"Welcome, {customer_name}.")
        # Proceed with the rest of the conversation (loan details, etc.)
        transcript.append(f"Bot: Am I speaking with {customer_name}?")
        speak_text(f"Am I speaking with {customer_name}?")
        
        # Pause for customer confirmation
        customer_confirmation = listen_for_name_or_exit()
        transcript.append(f"Customer: {customer_confirmation if customer_confirmation else 'No response'}")
        
        # Purpose of the call
        purpose = (
            f"I’m calling today to welcome you to the loan recovery process. "
            f"You have an outstanding loan amount of ₹{borrower_data.get('Outstanding Balance', 'N/A')}, "
            f"which you need to pay over a period of 12 months. Your installments will begin next week, "
            f"and the due date for repayment is {borrower_data.get('Due Date', 'N/A')}."
        )
        transcript.append(f"Bot: {purpose}")
        speak_text(purpose)

        # Polite closure
        closure = "Thank you for taking the time to listen to me today. Have a great day!"
        transcript.append(f"Bot: {closure}")
        speak_text(closure)

        # Save the transcript
        save_transcript(transcript, phone_number)
        send_email(phone_number)
    else:
        not_found_message = f"Sorry, we could not find your name in our records. Please try again."
        transcript.append(f"Bot: {not_found_message}")
        speak_text(not_found_message)
        save_transcript(transcript, phone_number)
        initiate_call(phone_number)  # Retry if name is incorrect

def save_transcript(transcript, phone_number):
    # Save the transcript to a file
    with open(f"Call_Transcript_{phone_number}.txt", "w", encoding="utf-8") as transcript_file:
        transcript_file.write("\n".join(transcript))
        transcript_file.write("\n" + "-" * 50 + "\n")
    print(f"Transcript saved as Call_Transcript_{phone_number}.txt")




# In[7]:


# Function to send email reminders
def send_email(phone):
    user_data = search(phone)
    if not user_data:
        print(f"No user data found for phone number {phone}. Email not sent.")
        return

    email = user_data.get('Email', None)  # Changed field name to match your CSV
    first_name = user_data.get('F_Name', 'Valued Customer')
    last_name = user_data.get('L_Name', '')
    balance = user_data.get('Outstanding Balance', 'N/A')

    if not email:
        print("Email not found in user data. Email cannot be sent.")
        return

    # Email content
    subject = "Loan Payment Reminder"
    body = f"""
    Dear {first_name} {last_name},

    This is a friendly reminder regarding your outstanding loan balance. As of now, the remaining loan amount is INR {balance}.

    Please make your payment at the earliest to avoid any late payment charges. If you have already made the payment, kindly ignore this email.

    For payment, visit: https://paymentUSER1UDN.com

    Thank you,
    Your Financial Assistant
    """

    sender_email = "2021.sanika.dhuri@ves.ac.in"
    sender_password = "vjgu wxdi vekw fxwu"
    receiver_email = email

    msg = MIMEMultipart()
    msg["From"] = sender_email
    msg["To"] = receiver_email
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain"))

    try:
        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login(sender_email, sender_password)
        server.sendmail(sender_email, receiver_email, msg.as_string())
        server.quit()

        print(f"Email sent successfully to {receiver_email}")
    except Exception as e:
        print(f"Error sending email: {e}")


# In[8]:


if __name__ == "__main__":
    
    phone_number = 9324396175  
    initiate_call(phone_number)


# In[ ]:




