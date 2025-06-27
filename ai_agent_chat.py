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
                {
                    "role": "system",
                    "content": (
                        "You are a helpful and friendly U.S. tax advisor AI who speaks like a real-world human expert. "
                        "Keep answers concise, practical, and beginner-friendly (under 120 words). Use numbered or bulleted steps where helpful. "
                        "Avoid jargon, long paragraphs, and excessive detail. Always Offer the user a clear next step if possible. "
                        "Always sound calm, approachable, and reassuring. Format output for clarity."
                        "Format your responses for readability, using lists for advice."
                    )
                }
            ] + chat_history,
            temperature=0.7,
            max_tokens=150
        )
        return response['choices'][0]['message']['content'].strip()
    except Exception as e:
        return f"AI Error: {str(e)}"
