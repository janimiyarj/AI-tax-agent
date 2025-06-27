#  AI Tax Agent – Smart Tax Filing Prototype

A full-stack AI-powered web application that assists users in preparing simplified U.S. federal tax returns. The system securely collects user information, calculates estimated taxes, generates a downloadable PDF return, and offers AI-powered financial suggestions.

---

##  Features

-  **Secure Login & Registration** (Flask-Login + bcrypt + SQLite)
-  **Smart Financial Suggestions** via OpenAI
-  **W-2-style Income Input** with data validations
-  **PDF Tax Form Generator** using user session data
-  **Integrated AI Chatbot** for personalized tax help
-  **Refund/Owe Summary** and Filing Suggestions
-  **Session-based Data Flow** across multiple steps

---

##  Tech Stack

- **Backend**: Python, Flask, SQLite
- **Frontend**: HTML, Jinja2, Bootstrap 5
- **AI/LLM**: OpenAI GPT (suggestions + chatbot)
- **PDF**: FPDF / Custom PDF Generator
- **Authentication**: Flask-Login, bcrypt
- **Security**: Encrypted passwords, CSRF-safe cookies, session protection

---

##  Folder Structure

![image](https://github.com/user-attachments/assets/13601573-cab8-48ae-baeb-7710a2ade9f7)


yaml
Copy
Edit

---

##  Setup Instructions

1. **Clone this repo**

### Command 1:
   git clone https://github.com/yourname/ai-tax-agent.git
  
   cd ai-tax-agent

Install dependencies

### Command 2:

pip install -r requirements.txt

Set your OpenAI API key

Create a .env file:

### Command 3:
OPENAI_API_KEY=your_key_here

Run the app

### Command 4:
python app.py
Visit

Open http://127.0.0.1:5000 in your browser.

## System Architecture
Frontend (HTML + Jinja2 + Bootstrap)
Renders multi-step forms, chat interface, PDF preview UI.

Backend (Flask)
Handles user input, stores sessions, controls navigation, enforces auth.

Tax Calculation Engine
tax_logic.py handles deductions, credits, dependents, refund/owe logic.

AI Suggestion Module
openai_suggestions.py uses OpenAI GPT-4 for optimizing refund strategy.

Data Flow
Form steps → session storage → tax logic → result generation → PDF export.

## Demo Flow
User registers & logs in securely.

Completes Step 1: Personal Info (SSN, address, status).

Completes Step 2: Income Details (Wages, interest, etc.).

Completes Step 3: Deductions + dependents.

Receives AI smart suggestion (e.g., change status to boost refund).

User accepts or rejects.

PDF summary generated → downloadable return.

## Deliverables
1. Full working prototype for end-to-end tax prep

2. Clean, modular codebase (Flask MVC structure)

3.  PDF download + AI Chat + financial suggestions

4.  User authentication with security best practices

5. Detailed documentation & deployment instructions

## Future Enhancements
1. IRS & MCPS API Integration for real-time e-filing

2.  OCR-based W-2/1099 uploads and autofill

3.  Multi-user dashboards to track filings

4.  Expanded deduction support (education, HSA, mortgage)

5.  AI-based audit risk detection

6.  Full GDPR & IRS compliance

## Author
Jani Miya Shaik
M.S. in Data Science and AI, SDSU
3.8+ years experience in AI, LLMs, and cloud deployments
LinkedIn : https://www.linkedin.com/in/jani-miya-shaik/

## Disclaimer
This is a prototype developed for educational and demonstration purposes.
Not intended for official tax filing. Always consult a licensed tax professional.
