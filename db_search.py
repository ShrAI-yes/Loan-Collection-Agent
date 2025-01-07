import pandas as pd

dataset = pd.read_csv('RAG docs/indian_borrowers_dataset.csv')

data = [
    'F_Name','L_Name', "Gender", "Income", 'Bureau_score', 
    "Loan_amount", "Loan_type", "Interest_Rate", 'Interest', 'Loan_Processing_Fee', "Current_balance", "Installment_Amount",
    'Disbursal_Date', "Repayment_Start_Date", "Repayment_tenure", "Date_of_last_payment", 'Repayment_mode',
    "No_of_late_payments"
]

def get_info(phone):
    if phone in dataset['Mobile_No'].values:
        return dataset[dataset['Mobile_No'] == phone][data]
    else:
        return None