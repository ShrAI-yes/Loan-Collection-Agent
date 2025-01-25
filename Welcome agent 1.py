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


# In[2]:


# Function to fetch borrower data based on phone number
def search(phone_number, file_path="Demo1.csv"):
    try:
        data = pd.read_csv(file_path)
        borrower = data[data['Phone Number'] == phone_number].to_dict(orient='records')
        return borrower[0] if borrower else None
    except FileNotFoundError:
        print(f"Error: File {file_path} not found.")
        return None


# In[3]:


# Text-to-speech function
def speak_text(text):
    try:
        tts = gTTS(text=text, lang='en')
        mp3_fp = BytesIO()  
        tts.write_to_fp(mp3_fp)
        mp3_fp.seek(0)  

        pygame.mixer.init()  
        pygame.mixer.music.load(mp3_fp)
        pygame.mixer.music.play()

        while pygame.mixer.music.get_busy():
            pygame.time.Clock().tick(10)

    except Exception as e:
        print(f"Error: {e}")


# In[4]:


# Function to fetch borrower data based on phone number
def search(phone_number, file_path="Demo1.csv"):
    try:
        data = pd.read_csv(file_path)
        borrower = data[data['Phone Number'] == phone_number].to_dict(orient='records')
        return borrower[0] if borrower else None
    except FileNotFoundError:
        print(f"Error: File {file_path} not found.")
        return None


# In[5]:


# Function to send email reminders
def send_email(phone):
    user_data = search(phone)
    if not user_data:
        print(f"No user data found for phone number {phone}. Email not sent.")
        return

    email = user_data.get('Email', None)  
    first_name = user_data.get('F_Name', 'Valued Customer')
    last_name = user_data.get('L_Name', '')
    balance = user_data.get('Current_balance', 'N/A')

    if not email:
        print("Email not found in user data. Email cannot be sent.")
        return

   
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


# In[6]:


# Function to initiate the call
def initiate_call(phone_number):
    # Fetch borrower data
    borrower_data = search(phone_number)
    if not borrower_data:
        print(f"No data found for phone number: {phone_number}.")
        return

    
    agent_name = "Malti"
    company_name = "Predixion AI"
    borrower_name = borrower_data.get("Borrower Name", "Valued Customer")
    loan_account = borrower_data.get("Loan Account Number", "N/A")
    outstanding_balance = borrower_data.get("Outstanding Balance", "N/A")
    due_date = borrower_data.get("Due Date", "N/A")

    
    transcript = []
    with open(f"Call_Transcript_{phone_number}.txt", "w", encoding="utf-8") as transcript_file:
        
        greeting = f"Good morning! This is {agent_name} calling on behalf of {company_name}."
        print(f"Bot: {greeting}")
        speak_text(greeting)
        transcript.append(greeting)

        
        confirmation = f"Am I speaking with {borrower_name}?"
        print(f"Bot: {confirmation}")
        speak_text(confirmation)
        transcript.append(confirmation)
        time.sleep(1)  

        
        purpose = (
            f"I’m calling to welcome you to the loan recovery process and assist you in resolving "
            f"the outstanding balance for your loan."
        )
        print(f"Bot: {purpose}")
        speak_text(purpose)
        transcript.append(purpose)

        
        loan_details = (
            f"I see that the outstanding balance on your loan is ₹{outstanding_balance}, "
            f"and the due date for repayment is {due_date}."
        )
        print(f"Bot: {loan_details}")
        speak_text(loan_details)
        transcript.append(loan_details)

        # Polite Closure
        closure = "Thank you for taking the time to speak with me today. Have a great day!"
        print(f"Bot: {closure}")
        speak_text(closure)
        transcript.append(closure)

        # Save the transcript
        transcript_file.write(f"Transcript for {borrower_name}:\n")
        transcript_file.write("\n".join(transcript))
        transcript_file.write("\n" + "-" * 50 + "\n")
        print(f"Transcript saved as Call_Transcript_{phone_number}.txt")

    send_email(phone_number)


# In[7]:


if __name__ == "__main__":
    phone_number = 9324396175  
    initiate_call(phone_number)


# In[ ]:




