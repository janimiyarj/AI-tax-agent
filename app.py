from flask import Flask, render_template, request, redirect, session, send_file
from datetime import datetime
import os, re
from tax_logic import calculate_tax, generate_filled_pdf, suggest_smart_filing
from openai_suggestions import generate_financial_suggestion
import os
import openai
from flask import send_file
from io import BytesIO
from pdf_generator import generate_better_tax_pdf
from flask_login import LoginManager, login_user, logout_user, login_required, UserMixin, current_user
from flask_bcrypt import Bcrypt
import sqlite3
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

app.config.update(
    SESSION_COOKIE_HTTPONLY=True,   # Prevent JS from accessing cookies
    SESSION_COOKIE_SECURE=True,     # Only transmit cookies over HTTPS
    SESSION_COOKIE_SAMESITE='Lax'   # Helps prevent CSRF
)

app.secret_key = 'your_secret_key_here'

bcrypt = Bcrypt(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

class User(UserMixin):
    def __init__(self, id, username, email, password):
        self.id = id
        self.username = username
        self.email = email
        self.password = password

@login_manager.user_loader
def load_user(user_id):
    conn = sqlite3.connect('user_auth.db')
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    row = cursor.fetchone()
    conn.close()
    if row:
        return User(*row)
    return None

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        email = request.form['email']
        password = bcrypt.generate_password_hash(request.form['password']).decode('utf-8')

        conn = sqlite3.connect('user_auth.db')
        cursor = conn.cursor()
        try:
            cursor.execute("INSERT INTO users (username, email, password) VALUES (?, ?, ?)",
                           (username, email, password))
            conn.commit()
        except sqlite3.IntegrityError:
            return "Username already exists"
        finally:
            conn.close()

        return redirect('/login')
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    toast = session.pop('show_logout_toast', False)  # Remove after 1 use
    error = None
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form['password']

        conn = sqlite3.connect('user_auth.db')
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
        row = cursor.fetchone()
        conn.close()

        if row and bcrypt.check_password_hash(row[3], password):
            user = User(*row)
            login_user(user)
            # 🧹 Clear session fields from previous user/form (but keep login session)
            for key in [
                'personal_info', 'income_data', 'deductions',
                'tax_result', 'smart_suggestion', 'suggestion_seen'
            ]:
                session.pop(key, None)
            return redirect('/')
        else:
            return "Invalid credentials"

    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    session['show_logout_toast'] = True  # ✅ Set flag to show toast
    return redirect('/')

@app.route('/')
@login_required
def index():
    return render_template('index.html')

from smart_suggestion import suggest_better_option

def run_smart_suggestion():
    income = session.get("income_data", {})
    deductions = session.get("deductions", {})
    personal_info = session.get("personal_info", {})
    taxes_paid = float(income.get("taxes_paid", 0) or 0)

    return suggest_better_option(income, deductions, personal_info, taxes_paid)


@app.route('/step1', methods=['GET', 'POST'])
@login_required
def step1():
    if request.method == 'POST':
        full_name = request.form.get('full_name', '').strip()
        ssn = request.form.get('ssn', '').strip()
        filing_status = request.form.get('filing_status', '')
        address = request.form.get('address', '').strip()
        city = request.form.get('city', '').strip()
        state = request.form.get('state', '').strip()
        zip_code = request.form.get('zip_code', '').strip()

        errors = []
        if not full_name:
            errors.append("Please enter your full name.")
        if not ssn or not re.match(r"^\d{3}-\d{2}-\d{4}$", ssn):
            errors.append("Please enter a valid SSN in the format XXX-XX-XXXX.")
        if not filing_status:
            errors.append("Please select your filing status.")
        if not address:
            errors.append("Please enter your street address.")
        if not city:
            errors.append("City field is required.")
        if not state or len(state) != 2:
            errors.append("Enter a valid 2-letter state code (e.g., CA).")
        if not zip_code:
            errors.append("ZIP Code is required.")
        print(errors)
        if errors:
            return render_template("form_step_1.html", form_data=request.form, errors=errors)
        else:
            session['personal_info'] = {
                'full_name': full_name,
                'ssn': ssn,
                'filing_status': filing_status,
                'address': address,
                'city': city,
                'state': state,
                'zip_code': zip_code
            }
            return redirect('/step2')

    return render_template('form_step_1.html', form_data=session.get('personal_info', {}))


@app.route('/step2', methods=['GET', 'POST'])
@login_required
def step2():
    if request.method == 'POST':
        form_data = {
            'wages': request.form.get('wages', ''),
            'interest': request.form.get('interest', ''),
            'dividends': request.form.get('dividends', ''),
            'business_income': request.form.get('business_income', ''),
            'other_income': request.form.get('other_income', ''),
            'taxes_paid': request.form.get('taxes_paid', '')
        }

        errors = []

        def is_valid_number(val, min_val=0, max_val=1_000_000):
            try:
                f = float(val)
                if f < min_val or f > max_val:
                    return False
                return True
            except:
                return False

        # Wages - Required
        if not form_data['wages']:
            errors.append("Wages (W-2) is required for federal filing.")
        elif not is_valid_number(form_data['wages'], 0, 1_000_000):
            errors.append("Wages (W-2) must be a valid number between $0 and $1,000,000.")

        # Optional fields (check if entered, then validate)
        if form_data['interest'] and not is_valid_number(form_data['interest'], 0, 500_000):
            errors.append("Interest income must be a number between $0 and $500,000.")

        if form_data['dividends'] and not is_valid_number(form_data['dividends'], 0, 500_000):
            errors.append("Dividend income must be a number between $0 and $500,000.")

        if form_data['business_income'] and not is_valid_number(form_data['business_income'], 0, 5_000_000):
            errors.append("Business income must be a number between $0 and $5,000,000.")

        if form_data['other_income'] and not is_valid_number(form_data['other_income'], 0, 2_000_000):
            errors.append("Other income must be a number between $0 and $2,000,000.")

        if form_data['taxes_paid'] and not is_valid_number(form_data['taxes_paid'], 0, 1_000_000):
            errors.append("Taxes paid must be a number between $0 and $1,000,000.")

        if errors:
            return render_template("form_step_2.html", form_data=form_data, errors=errors)

        # If all good, save and go to step3
        session['income_data'] = form_data
        return redirect('/step3')

    # GET Request: Load existing values
    return render_template('form_step_2.html', form_data=session.get('income_data', {}))


from flask import request, render_template, session, redirect
from smart_suggestion import suggest_better_option  # assuming this is your function

@app.route('/step3', methods=['GET', 'POST'])
@login_required
def step3():
    if request.method == 'POST':
        form = request.form
        errors = []

        deduction_type = form.get("deduction_type")
        dependents_input = form.get("dependents", "").strip()

        # Only parse itemized fields if itemized is selected
        mortgage_input = form.get("mortgage", "").strip() if deduction_type == "itemized" else "0"
        state_taxes_input = form.get("state_taxes", "").strip() if deduction_type == "itemized" else "0"
        charity_input = form.get("charity", "").strip() if deduction_type == "itemized" else "0"
        medical_input = form.get("medical", "").strip() if deduction_type == "itemized" else "0"

        # --- Safe parsing ---
        def safe_float(val, label):
            try:
                return float(val)
            except ValueError:
                errors.append(f"{label} must be a valid number.")
                return 0.0

        mortgage = safe_float(mortgage_input, "Mortgage Interest")
        state_taxes = safe_float(state_taxes_input, "State Taxes")
        charity = safe_float(charity_input, "Charitable Contributions")
        medical = safe_float(medical_input, "Medical Expenses")


        try:
            dependents = int(dependents_input)
        except ValueError:
            errors.append("Number of dependents must be a valid whole number.")
            dependents = 0

        # --- Validation Rules ---
        if deduction_type not in ['standard', 'itemized']:
            errors.append("Please select a deduction type — this is required.")

        if deduction_type == 'itemized':
            if mortgage < 0 or mortgage > 1_000_000:
                errors.append("Mortgage Interest must not exceed $1,000,000.")
            if state_taxes < 0 or state_taxes > 10_000:
                errors.append("State and local taxes deduction is capped at $10,000.")
            if charity < 0 or charity > 500_000:
                errors.append("Charity donations must be $500,000 or less.")
            if medical < 0 or medical > 250_000:
                errors.append("Medical expenses must not exceed $250,000.")

        if dependents < 0 or dependents > 15:
            errors.append("Number of dependents should be between 0 and 15.")

        # --- On Validation Failure ---
        if errors:
            return render_template(
                "form_step_3.html",
                form_data=form,
                errors=errors
            )

        # --- Save to Session ---
        session['deductions'] = {
            "deduction_type": deduction_type,
            "itemized": {
                "mortgage": mortgage,
                "state_taxes": state_taxes,
                "charity": charity,
                "medical": medical
            } if deduction_type == "itemized" else {},
            "dependents": dependents
        }

        # --- Get OpenAI suggestion ---
        # --- Check if suggestion already seen ---
        if not session.get('suggestion_seen'):
            suggestion = generate_financial_suggestion(
                session.get('income_data', {}),
                session.get('deductions', {}),
                session.get('personal_info', {}),
                float(session.get('income_data', {}).get('taxes_paid', 0) or 0)
            )
            print("🔍 OpenAI Suggestion Output:", suggestion)

            if suggestion and suggestion.get("refund_boost", 0) > 0:
                session['smart_suggestion'] = suggestion
                return redirect('/suggestion_review')

        # If already seen or no valid suggestion, go to summary
        return redirect('/summary')

    # On GET
    return render_template("form_step_3.html", form_data=session.get('deductions', {}), errors=[])


@app.route('/apply_suggestion', methods=['GET'])
@login_required
def apply_suggestion():
    suggestion = session.get('smart_suggestion')
    if suggestion:
        # Apply suggested filing status
        session['personal_info']['filing_status'] = suggestion['suggested_status']

        # Recalculate taxes fresh to get full result
        income = session.get('income_data', {})
        deductions = session.get('deductions', {})
        taxes_paid = float(income.get("taxes_paid", 0) or 0)
        dependents = deductions.get("dependents", 0)

        session['tax_result'] = calculate_tax(
            income_data=income,
            deductions_data=deductions,
            filing_status=suggestion['suggested_status'],
            dependents=dependents,
            taxes_paid=taxes_paid
        )

    return redirect('/summary')


@app.route('/suggestion_review', methods=['GET'])
@login_required
def suggestion_review():
    suggestion = session.get('smart_suggestion')
    if not suggestion:
        return redirect('/summary')  # fallback if no suggestion

    return render_template("suggestion_review.html", suggestion=suggestion)


@app.route('/apply_openai_suggestion', methods=['GET', 'POST'])
@login_required
def apply_openai_suggestion():
    # ✅ Just redirect back to Step 3 without modifying session data
    session['suggestion_seen'] = True
    return redirect('/step3')


@app.route('/reject_openai_suggestion', methods=['GET', 'POST'])
@login_required
def reject_openai_suggestion():
    # Use existing values, just recalculate tax normally
    income = session.get('income_data', {})
    deductions = session.get('deductions', {})
    dependents = deductions.get("dependents", 0)
    taxes_paid = float(income.get("taxes_paid", 0) or 0)

    session['tax_result'] = calculate_tax(
        income_data=income,
        deductions_data=deductions,
        filing_status=session['personal_info'].get("filing_status", "single"),
        dependents=dependents,
        taxes_paid=taxes_paid
    )

    return redirect('/summary')


@app.route('/summary')
@login_required
def summary():
    personal = session.get('personal_info', {})
    income = session.get('income_data', {})
    deductions = session.get('deductions', {})
    taxes_paid = float(income.get("taxes_paid", 0) or 0)
    dependents = deductions.get("dependents", 0)
    filing_status = personal.get("filing_status", "single")

    # Calculate tax if not already stored (i.e., not from suggestion flow)
    if 'tax_result' not in session:
        session['tax_result'] = calculate_tax(
            income_data=income,
            deductions_data=deductions,
            filing_status=filing_status,
            dependents=dependents,
            taxes_paid=taxes_paid
        )

    return render_template(
    'summary.html',
    info=personal,
    income=income,
    deductions=deductions,
    tax_result=session.get('tax_result', {}),
    result=session.get('tax_result', {}),  # <-- add this line
    suggestion=session.get('smart_suggestion', {})
)


@app.route("/download")
@login_required
def download_pdf():
    info = session.get("personal_info", {})
    income = session.get("income_data", {})
    deductions = session.get("deductions", {})
    result = session.get("tax_result", {})

    pdf_bytes, filename = generate_better_tax_pdf(info, income, deductions, result)
    return send_file(BytesIO(pdf_bytes), download_name=filename, as_attachment=True)


chat_memory = []
@app.route("/ai_tax_advice", methods=["GET", "POST"])
@login_required
def ai_chat():
    global chat_memory

    if request.method == 'POST':
        if request.form.get("reset"):
            chat_memory = []
        else:
            user_input = request.form.get("user_input", "").strip()
            if user_input:
                openai.api_key = os.getenv("OPENAI_API_KEY")
                response = openai.ChatCompletion.create(
                    model="gpt-4",
                    messages=[
                        {"role": "system", "content": "You are a helpful AI Tax Advisor."},
                        *[
                            {"role": "user", "content": entry["user"]} if i % 2 == 0 else
                            {"role": "assistant", "content": entry["ai"]}
                            for i, entry in enumerate(chat_memory)
                        ],
                        {"role": "user", "content": user_input}
                    ]
                )
                ai_response = response.choices[0].message['content']
                chat_memory.append({"user": user_input, "ai": ai_response})

    return render_template("ai_chat.html", chat_history=chat_memory)

@app.route("/reset_chat")
@login_required
def reset_chat():
    session.pop("chat_history", None)
    return redirect("/ai_tax_advice")


if __name__ == '__main__':
    app.run(debug=True)
