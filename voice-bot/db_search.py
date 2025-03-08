#this code has a function to search for the information of the user based on the phone number

import pandas as pd

dataset = pd.read_csv('../RAG docs/indian_borrowers_dataset_modified.csv')

data = [
    'F_Name','L_Name', "Gender", 'Mobile_No', "Income", 'Bureau_score', 
    "Loan_amount", "Loan_type", "Interest_Rate", 'Interest', 'Loan_Processing_Fee', "Current_balance", "Installment_Amount",
    'Disbursal_Date', "Repayment_Start_Date", "Repayment_tenure", "Date_of_last_payment", 'Repayment_mode',
    "No_of_late_payments"
]

def get_info(phone):
    if phone in dataset['Mobile_No'].values:
        user_data = dataset[dataset['Mobile_No'] == phone][data]

        user_info = {
            "first_name": user_data['F_Name'].item(),
            "last_name": user_data['L_Name'].item(),
            "phone_no": user_data['Mobile_No'].item(),
            "gender": user_data['Gender'].item(),
            "income_in_inr": user_data['Income'].item(),
            "credit_score": user_data['Bureau_score'].item(),
            "loan_type": user_data['Loan_type'].item(),
            "loan_amount" : user_data['Loan_amount'].item(),
            "interest_rate": user_data['Interest_Rate'].item(),
            "process_fee": user_data['Loan_Processing_Fee'].item(),
            "installment": user_data['Installment_Amount'].item(),
            "start_date": user_data['Repayment_Start_Date'].item(),
            "tenure": user_data['Repayment_tenure'].item(),
            "balance_to_pay": user_data['Current_balance'].item(),
            "payment_mode": user_data['Repayment_mode'].item(),
            "late_payment": user_data['No_of_late_payments'].item(),
            "last_date": user_data['Date_of_last_payment'].item()
        }

        return user_info
    else:
        return None