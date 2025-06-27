import os
import openai
from dotenv import load_dotenv

load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")

def generate_financial_suggestion(income, deductions, personal_info, taxes_paid):
    prompt = f"""
You are a certified financial advisor. Based on this taxpayer's profile, suggest one legal and smart tax strategy to increase refund or reduce tax owed.

Filing Status: {personal_info.get("filing_status")}
Income: {income}
Deductions: {deductions}
Taxes Paid: {taxes_paid}

Respond in the format:
Explanation: <your suggestion text>
Refund_Boost: <estimated extra refund as a number>
"""

    try:
        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are a helpful tax advisor."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.5,
            max_tokens=300
        )

        content = response['choices'][0]['message']['content']

        # Parse response
        explanation = None
        refund_boost = 0.0
        for line in content.splitlines():
            if line.lower().startswith("explanation:"):
                explanation = line.split(":", 1)[1].strip()
            elif line.lower().startswith("refund_boost:"):
                try:
                    refund_boost = float(line.split(":", 1)[1].strip().replace("$", ""))
                except ValueError:
                    refund_boost = 0.0

        return {
            "explanation": explanation or "No suggestion provided.",
            "refund_boost": refund_boost
        }

    except Exception as e:
        print("OpenAI Error:", e)
        return None
