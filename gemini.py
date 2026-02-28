import chromadb
from dotenv import load_dotenv
from google import genai
import streamlit as st
from db import get_db
import os

from GeminiEmbeddingFunction import GeminiEmbeddingFunction  
load_dotenv()
from config import GEMINI_API_KEY, LLM_MODEL
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
try:
    _masked = (GEMINI_API_KEY[:6] + "..." + GEMINI_API_KEY[-4:]) if GEMINI_API_KEY else "(none)"
except Exception:
    _masked = "(masked)"
print(f"[gemini.py] Initialized client model={LLM_MODEL}, api_key={_masked}")

def chat(query):
    db = get_db()

    # Example query
    
    result = db.query(query_texts=[query], n_results=5)
    [all_passages] = result["documents"]
    query_oneline = query.replace("\n", " ")

    
    prompt = f"""
You are a helpful and informative assistant for university students. 
Answer questions and explain concepts clearly and simply, using the reference passage included below to guide your response. 
Don't answer questions that are not related to the passage.
Be sure to provide complete answers with useful background context, and keep your tone friendly and conversational.
Do not mention the passage or reference materials — just provide confident, natural-sounding answers.
Only rely on outside knowledge if it's absolutely necessary.
Be sure to give complete answers with useful background context, and keep your tone friendly and conversational.


    QUESTION: {query_oneline}
    """

    
    for passage in all_passages:
        passage_oneline = passage.replace("\n", " ")
        prompt += f"PASSAGE: {passage_oneline}\n"

   
    response = client.models.generate_content(
        model=LLM_MODEL,
        contents=prompt,
    )
    return response.text
