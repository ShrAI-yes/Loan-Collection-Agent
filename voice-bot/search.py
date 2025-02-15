#!/usr/bin/env python
# coding: utf-8

import os
import time
from gtts import gTTS
import speech_recognition as sr
from langchain_mistralai import ChatMistralAI
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings
from db_search import get_info as search

llm = ChatMistralAI(
    model="mistral-large-latest",
    temperature=0,
    max_retries=5,
    api_key="API_KEY"  
)

embedder = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
db = Chroma(persist_directory="./vector_db", embedding_function=embedder)

def get_response(user_query, doc_context):
    """
    Generates a response based on the user query and document context.
    """
    llm_query_res_template = """
        Answer the question based on the context below. If the question cannot be answered using the information provided, reply with "I don't know". Also, make sure to answer the following questions considering the history of the conversation:
        
        You are an intelligent virtual financial assistant for Predixion AI, directly engaging with customers about their loan repayments. Your role is to help manage their loan, facilitate payments, and answer financial questions in a clear, professional way. Communicate in a friendly, authoritative manner, addressing the customer directly ("you") with concise responses suitable for WhatsApp.
        
        Make sure you communicate with the user in such a way that your response should always lead to payment collection.
        
        Instructions:
        1. Use precise financial language and ensure clear, accurate information.
        2. Facilitate payments: If the user is willing to pay the loan then please provide this link 'https://paymentUSER1UDN.com'. Do not send the link until user requests or user wants to pay the loan.
        3. Offer solutions: If the customer is struggling, provide options like grace periods, payment restructuring, or deadline extensions.
        4. Keep responses short and to the point.
        5. Ensure confidentiality and remind the customer to keep their payment details secure.
        6. You can only extend the loan dates by 10 days if user requests for grace periods or deadline extensions.
        
        Context: "NONE"
        Question: {user_query}
        Doc context: {doc_context}
        Answer:
    """
    
    prompt_query_res_template = ChatPromptTemplate.from_template(llm_query_res_template)
    llm_chain = prompt_query_res_template | llm | StrOutputParser()
    
    response = ''.join([chunk for chunk in llm_chain.stream({
        "user_query": user_query,
        "doc_context": doc_context,
    })])
    
    return response

if __name__ == "__main__":
    phone_number = 9988953565  #replace with dynamic input if needed
    person_info = search(phone_number)
    
    if person_info:
        print(f"Information found for {phone_number}: {person_info}")
    else:
        print(f"No information found for {phone_number}.")