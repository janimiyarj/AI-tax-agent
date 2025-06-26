from flask import Flask, render_template, request, redirect, session, send_file, url_for
from tax_logic import calculate_tax
from pdf_generator import generate_better_tax_pdf
import os
import re
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'your_super_secure_secret_key_here'  # Change for production use

@app.context_processor
def inject_current_year():
    return {'current_year': datetime.now().year}

# Landing Page
@app.route('/')
def home():
    session.clear()
    return render_template('index.html')

# Step 1: Personal Information
@app.route('/step1', methods=['GET', 'POST'])
def step1():
    error = None
    form_data = session.get('personal_info') or {}
    if request.method == 'GET':
        session.pop('personal_info', None)  

    if request.method == 'POST':
        try:
            full_name = request.form.get("full_name", "").strip()
            if not full_name or len(full_name) > 100:
                raise ValueError("Full name is required and must be under 100 characters.")

            ssn = request.form.get("ssn", "").strip()
            if not ssn or not re.match(r"^\d{3}-\d{2}-\d{4}$", ssn):
                raise ValueError("SSN format must be 123-45-6789")

            filing_status = request.form.get("filing_status")
            if filing_status not in ["single", "married_joint", "married_separate", "head_household"]:
                raise ValueError("Invalid filing status selected.")

            dependents_raw = request.form.get("dependents", "0")
            dependents = int(float(dependents_raw))
            if dependents < 0 or dependents > 15:
                raise ValueError("Dependents must be between 0 and 15.")

            form_data = {
                'full_name': full_name,
                'ssn': ssn,
                'filing_status': filing_status,
                'address': request.form.get("address", "").strip(),
                'city': request.form.get("city", "").strip(),
                'state': request.form.get("state", "").strip(),
                'zip_code': request.form.get("zip_code", "").strip(),
                'dependents': dependents
            }

            session['personal_info'] = form_data
            return redirect(url_for('step2'))

        except ValueError as ve:
            error = str(ve)
            form_data = {
                'full_name': request.form.get("full_name", "").strip(),
                'ssn': request.form.get("ssn", "").strip(),
                'filing_status': request.form.get("filing_status"),
                'address': request.form.get("address", "").strip(),
                'city': request.form.get("city", "").strip(),
                'state': request.form.get("state", "").strip(),
                'zip_code': request.form.get("zip_code", "").strip(),
                'dependents': request.form.get("dependents", "0")
            }


    return render_template('form_step_1.html', error=error, form_data=form_data)


@app.route('/step2', methods=['GET', 'POST'])
def step2():
    error = None
    form_data = session.get('income') or {}

    if request.method == 'GET' and 'from_back' not in request.args:
        session.pop('income', None)

    if request.method == 'POST':
        # Collect raw input strings
        wages_raw = request.form.get('wages', '').strip()
        interest_raw = request.form.get('interest', '').strip()
        dividends_raw = request.form.get('dividends', '').strip()
        business_raw = request.form.get('business_income', '').strip()
        other_raw = request.form.get('other_income', '').strip()
        taxes_paid_raw = request.form.get('taxes_paid', '').strip()

        # Prepare form_data to repopulate fields in case of error
        form_data = {
            'wages': wages_raw,
            'interest': interest_raw,
            'dividends': dividends_raw,
            'business_income': business_raw,
            'other_income': other_raw,
            'taxes_paid': taxes_paid_raw
        }

        # Error if all fields are empty
        if all(v == "" for v in [wages_raw, interest_raw, dividends_raw, business_raw, other_raw, taxes_paid_raw]):
            error = "Please fill at least one field. If no income, enter 0 in the appropriate boxes."
            return render_template('form_step_2.html', error=error, form_data=form_data)

        try:
            # Convert to float, treating empty as 0.0
            wages = float(wages_raw) if wages_raw else 0.0
            interest = float(interest_raw) if interest_raw else 0.0
            dividends = float(dividends_raw) if dividends_raw else 0.0
            business_income = float(business_raw) if business_raw else 0.0
            other_income = float(other_raw) if other_raw else 0.0
            taxes_paid = float(taxes_paid_raw) if taxes_paid_raw else 0.0

            # Field validations
            if wages < 0 or wages > 1_000_000:
                error = "Wages must be a valid number between 0 and 1,000,000."
            elif other_income < 0 or other_income > 2_000_000:
                error = "Other income must be between 0 and 2,000,000."
            elif any(val < 0 for val in [interest, dividends, business_income, taxes_paid]):
                error = "Income fields cannot be negative."

            if error:
                return render_template('form_step_2.html', error=error, form_data=form_data)

            # Save cleaned values in session
            session['income'] = {
                'wages': wages,
                'interest': interest,
                'dividends': dividends,
                'business_income': business_income,
                'other_income': other_income,
                'taxes_paid': taxes_paid
            }

            return redirect('/step3')

        except ValueError:
            error = "Please enter valid numeric values only."
            return render_template('form_step_2.html', error=error, form_data=form_data)

    return render_template('form_step_2.html', error=error, form_data=form_data)


@app.route('/step3', methods=['GET', 'POST'])
def step3():
    errors = []
    form_data = session.get('deductions') or {}

    if request.method == 'GET' and 'from_back' not in request.args:
        session.pop('deductions', None)

    if request.method == 'POST':
        deduction_type = request.form.get('deduction_type', 'standard')
        form_data['deduction_type'] = deduction_type

        # Collect itemized values (even if not used)
        for field in ['mortgage', 'state_taxes', 'charity', 'medical']:
            form_data[field] = request.form.get(field, '').strip()

        mortgage = state_taxes = charity = medical = 0.0
        agi = float(session.get('agi', 0))  # Must be set earlier in the flow

        def safe_float(val):
            try:
                return float(val) if val.strip() not in ("", None) else 0.0
            except:
                return None

        if deduction_type == 'itemized':
            # Mortgage Interest
            mortgage = safe_float(form_data['mortgage'])
            if mortgage is None:
                errors.append("Mortgage must be a number.")
            elif mortgage > 50000:
                errors.append("Mortgage interest seems too high. Max allowed is typically ~$50,000/year on a $750,000 loan.")

            # State Taxes
            state_taxes = safe_float(form_data['state_taxes'])
            if state_taxes is None:
                errors.append("State taxes must be a number.")
            elif state_taxes > 10000:
                errors.append("State and local tax deductions are capped at $10,000 by the IRS.")

            # Charity
            charity = safe_float(form_data['charity'])
            if charity is None:
                errors.append("Charity must be a number.")
            elif agi and charity > 0.6 * agi:
                errors.append("Charitable contributions cannot exceed 60% of your AGI.")

            # Medical
            medical = safe_float(form_data['medical'])
            if medical is None:
                errors.append("Medical expenses must be a number.")
            elif agi and medical < 0.075 * agi:
                errors.append("Medical expenses are only deductible above 7.5% of AGI.")

        # Dependents
        dependents_raw = request.form.get('dependents', '').strip()
        form_data['dependents'] = dependents_raw

        try:
            dependents = int(float(dependents_raw)) if dependents_raw else 0
            if dependents < 0 or dependents > 15:
                errors.append("Dependents must be between 0 and 15.")
        except:
            errors.append("Dependents must be a whole number.")

        if errors:
            return render_template('form_step_3.html', errors=errors, form_data=form_data)

        # Save clean session
        session['deductions'] = {
            'deduction_type': deduction_type,
            'itemized': {
                'mortgage': mortgage,
                'state_taxes': state_taxes,
                'charity': charity,
                'medical': medical
            },
            'dependents': dependents
        }
        return redirect('/summary')

    return render_template('form_step_3.html', errors=errors, form_data=form_data)


@app.route('/summary')
def summary():
    try:
        personal_info = session.get('personal_info', {})
        income = session.get('income', {})
        deductions = session.get('deductions', {})

        if not (personal_info and income and deductions):
            return render_template("error.html", message="Incomplete session data. Please start again.")

        taxes_paid = float(income.get("taxes_paid", 0))
        result = calculate_tax(income, deductions, personal_info['filing_status'], deductions.get("dependents", 0), taxes_paid)

        # ✅ Avoid generic error.html redirect
        if "error" in result:
            # Stay on step2 and repopulate values instead of redirecting to error
            return render_template("form_step_2.html", error=result["error"], form_data=income)

        session['tax_result'] = result
        return render_template('summary.html', info=personal_info, income=income, deductions=deductions, result=result)

    except Exception as e:
        return render_template('error.html', message="Summary generation failed: " + str(e))


@app.route('/download')
def download():
    try:
        personal_info = session.get('personal_info', {})
        income = session.get('income', {})
        deductions = session.get('deductions', {})
        result = session.get('tax_result', {})

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"output/tax_return_{timestamp}.pdf"

        # ✅ Use the improved PDF generator
        generate_better_tax_pdf(personal_info, income, deductions, result, filename)

        return send_file(filename, as_attachment=True)
    except Exception as e:
        return render_template('error.html', message="Failed to generate PDF: " + str(e))


@app.errorhandler(404)
def page_not_found(e):
    return render_template('error.html', message="Page not found"), 404


if __name__ == '__main__':
    if not os.path.exists('output'):
        os.makedirs('output')
    app.run(debug=True)
