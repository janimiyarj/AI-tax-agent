from flask import Flask, render_template, request, redirect, session, send_file, url_for
from tax_logic import calculate_tax
from pdf_generator import generate_tax_pdf
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
        session.pop('income', None)  # clear only on first arrival


    if request.method == 'POST':
        try:
            wages = float(request.form.get('wages', 0))
            interest = float(request.form.get('interest', 0))
            dividends = float(request.form.get('dividends', 0))
            business_income = float(request.form.get('business_income', 0))
            other_income = float(request.form.get('other_income', 0))

            if wages > 1000000 or other_income > 2000000:
                raise ValueError("Income values exceed allowed range.")

            taxes_paid = float(request.form.get('taxes_paid', 0))
            form_data = {
                'wages': wages,
                'interest': interest,
                'dividends': dividends,
                'business_income': business_income,
                'other_income': other_income,
                'taxes_paid': taxes_paid
            }

            session['income'] = form_data
            return redirect('/step3')
        except ValueError as ve:
            error = str(ve)
            form_data = {
                'wages': request.form.get('wages', ''),
                'interest': request.form.get('interest', ''),
                'dividends': request.form.get('dividends', ''),
                'business_income': request.form.get('business_income', ''),
                'other_income': request.form.get('other_income', ''),
                'taxes_paid': request.form.get('taxes_paid', '')
            }


    return render_template('form_step_2.html', error=error, form_data=form_data)


@app.route('/step3', methods=['GET', 'POST'])
def step3():
    errors = []
    form_data = session.get('deductions') or {}
    if request.method == 'GET' and 'from_back' not in request.args:
        session.pop('deductions', None)


    if request.method == 'POST':
        deduction_type = request.form.get('deduction_type')
        form_data['deduction_type'] = deduction_type

        for field in ['mortgage', 'state_taxes', 'charity', 'medical']:
            form_data[field] = request.form.get(field, '')

        if deduction_type == 'itemized':
            try:
                mortgage = float(form_data['mortgage'])
                if mortgage < 0 or mortgage > 100000:
                    errors.append("Mortgage must be a valid number between 0 and 100000.")
            except ValueError:
                errors.append("Mortgage must be a number.")
            try:
                state_taxes = float(form_data['state_taxes'])
                if state_taxes < 0 or state_taxes > 50000:
                    errors.append("State taxes must be between 0 and 50000.")
            except ValueError:
                errors.append("State taxes must be a number.")
            try:
                charity = float(form_data['charity'])
                if charity < 0 or charity > 50000:
                    errors.append("Charity must be between 0 and 50000.")
            except ValueError:
                errors.append("Charity must be a number.")
            try:
                medical = float(form_data['medical'])
                if medical < 0 or medical > 100000:
                    errors.append("Medical expenses must be between 0 and 100000.")
            except ValueError:
                errors.append("Medical must be a number.")
        else:
            mortgage = state_taxes = charity = medical = 0

        try:
            dependents_raw = request.form.get('dependents', "0")
            dependents = int(float(dependents_raw))
            if dependents < 0 or dependents > 15:
                errors.append("Dependents must be between 0 and 15.")
        except ValueError:
            errors.append("Dependents must be a whole number.")

        form_data['dependents'] = dependents_raw

        if errors:
            return render_template('form_step_3.html', errors=errors, form_data=form_data)

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

        if "error" in result:
            return render_template("error.html", message=result["error"])

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
        generate_tax_pdf(personal_info, income, deductions, result, filename)
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
