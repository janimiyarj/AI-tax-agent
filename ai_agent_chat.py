# ai_agent.py
import os
import openai
from dotenv import load_dotenv

load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")

def ask_tax_assistant_chat(chat_history):
    try:
        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[
                {"role": "system", 
                 "content": "You are a helpful and expert tax advisor AI. The user will be asking questions related to finance or tax returns. Answer like a real-world financial advisor would: friendly, concise, practical, and tailored. Be under 220 words."}
            ] + chat_history,
            temperature=0.7,
            max_tokens=300
        )
        return response['choices'][0]['message']['content'].strip()
    except Exception as e:
        return f"AI Error: {str(e)}"
