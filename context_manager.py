import os
import json
import pandas as pd
import firebase_admin
from firebase_admin import credentials, firestore

from clean_variables import money_to_words, date_to_words
import RAGer as rag

class UserData:
    def __init__(self):
        self.dir_path = os.path.join(os.path.dirname(os.path.abspath(__file__)),'user_files')
        self.file_path = ''
        self.Data = None

    def read_file(self,file_name):
        self.file_path = os.path.join(self.dir_path, file_name)
        file_extension = os.path.splitext(self.file_path)[1]
        if file_extension == '.csv':
            try:
                self.Data = pd.read_csv(self.file_path)
            except FileNotFoundError as e:
                print(f"I dont think the file '{file_name}' exists. Did you add it in the 'user_files' directory?")

        elif file_extension == '.pdf':
            docs = rag.load_dir(self.file_path)
            ids, texts, metadata = rag.chunking(docs)
            rag.embed_chunks(ids, texts, metadata)
            self.Data = "Data is Vectorized. Use fetch_info(query) method to get data."

        else:
            print("Currently only 'csv' and 'pdf' files can be read")

    def fetch_user(self,phone_no):
        try:
            phone_no = int(phone_no)
            if phone_no in self.Data['Mobile_No'].values:
                user_data = self.Data.loc[self.Data['Mobile_No'] == phone_no]
                user_info = {
                    "first_name": user_data['F_Name'].item(),
                    "last_name": user_data['L_Name'].item(),
                    "phone_no": user_data['Mobile_No'].item(),
                    "gender": user_data['Gender'].item(),
                    "income_in_inr": money_to_words(user_data['Income'].item()),
                    "credit_score": user_data['Bureau_score'].item(),
                    "loan_type": user_data['Loan_type'].item(),
                    "loan_amount": money_to_words(user_data['Loan_amount'].item()),
                    "interest_rate": f"{user_data['Interest_Rate'].item()} percent",
                    "process_fee": money_to_words(user_data['Loan_Processing_Fee'].item()),
                    "installment": money_to_words(user_data['Installment_Amount'].item()),
                    "start_date": date_to_words(user_data['Repayment_Start_Date'].item()),
                    "tenure": f"{user_data['Repayment_tenure'].item()} months",
                    "balance_to_pay": money_to_words(user_data['Current_balance'].item()),
                    "payment_mode": user_data['Repayment_mode'].item(),
                    "late_payment": user_data['No_of_late_payments'].item(),
                    "last_date": date_to_words(user_data['Date_of_last_payment'].item()),
                    "due_date": date_to_words(user_data['Next_due_date'].item()),
                    "pending_days": user_data['Pending_days'].item(),
                    "minimum_due_amount": money_to_words(user_data['Minimum_amount_due'].item()),
                    "late_fees": money_to_words(user_data["Late_Fees"].item()),
                    "emi_eligible": user_data["Eligible_for_EMI"].item()
                }
                return user_info
            else:
                print('User does not exist.')
                return {"Error": "User does not exist."}
        except (TypeError) as e:
            print(f'Such a Phone Number does not exist in {self.file_path}')
            return {}

    def fetch_info(self,query):
        result = rag.fetch_query(query)
        return result

class Database:
    def __init__(self):
        self.cred = credentials.Certificate("./predixion-145c5-firebase-adminsdk-fbsvc-67522dea10.json")
        try:
            firebase_admin.initialize_app(self.cred)
        except ValueError as e:
            print('Firebase App already Initialized')
        self.db = firestore.client()

    def init_user(self,phone: str, wa_id=None, chat_id=None, name=None):
        doc_ref = self.db.collection("testing").document(phone)
        if not doc_ref.get().exists:
            data = {
                "whatsapp_id": wa_id,
                "id": chat_id,
                "phone": phone,
                "name": name,
                "whatsapp_messages": [],
                "call_transcripts": []
            }
            self.db.collection("testing").document(phone).set(data)

        return self.db.collection("testing").document(phone)

    def payload(self, name, text, time):
        msg = {
            f"{name}": str(text),
            "timestamp": time
        }
        return msg

    def add_convo(self, ref, agent, msg):
        if agent == 'voice':
            ref.update({"call_transcripts": firestore.ArrayUnion(msg)})
        elif agent == 'whatsapp':
            ref.update({"whatsapp_messages": firestore.ArrayUnion(msg)})
        else:
            raise Exception('Invalid Agent')

    def get_convo(self, ref, agent):
        if agent == 'voice':
            conversation = ref.get().to_dict()['call_transcripts']
        elif agent == 'whatsapp':
            conversation = ref.get().to_dict()['whatsapp_messages']
        else:
            raise Exception('Invalid Agent')

        for msg in conversation:
            if 'timestamp' in msg:
                del msg['timestamp']

        latest_conversation = conversation[-10:]  # Slicing the list
        return latest_conversation