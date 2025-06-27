import os
import openai
from dotenv import load_dotenv

load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")

def generate_financial_suggestion(income, deductions, personal_info, taxes_paid):
    prompt = f"""
You are a certified financial advisor. Based on the following taxpayer's financial profile, suggest one legal and smart tax strategy to increase their refund or reduce their tax owed. 
A "smart" strategy is one that is commonly applicable and aims for significant impact given the provided information.

**Taxpayer's Profile:**
* Filing Status: {personal_info['filing_status']}
* Income: {income}
* Deductions: {deductions}
* Taxes Paid: {taxes_paid}

Keep the suggestion in the form of a short explanation and an estimated extra refund amount in U.S. dollars. The estimated extra refund should be a reasonable approximation based on typical tax savings from the suggested strategy.

Respond in the exact format below, including the disclaimer:

Explanation: <your suggestion text>
Refund_Boost: <estimated extra refund as a whole number in USD>
Disclaimer: This is a general tax strategy suggestion and not personalized tax advice. Please consult with a qualified tax professional for advice tailored to your specific situation.
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
