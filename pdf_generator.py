from fpdf import FPDF

def generate_tax_pdf(info, income, deductions, result, filename):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=15)

    # Header
    pdf.set_font("Helvetica", 'B', 16)
    pdf.cell(0, 10, "U.S. Individual Income Tax Return Summary", ln=True, align='C')
    pdf.set_font("Helvetica", '', 10)
    pdf.cell(0, 10, "For Tax Year 2023 - Simplified Prototype", ln=True, align='C')
    pdf.ln(10)

    # Personal Info
    pdf.set_font("Helvetica", 'B', 12)
    pdf.cell(0, 10, "Personal Information", ln=True)
    pdf.set_font("Helvetica", '', 11)
    pdf.cell(0, 8, f"Name: {info.get('full_name')}", ln=True)
    pdf.cell(0, 8, f"SSN: {info.get('ssn')}", ln=True)
    pdf.cell(0, 8, f"Filing Status: {info.get('filing_status').title()}", ln=True)
    pdf.cell(0, 8, f"Address: {info.get('address')}, {info.get('city')}, {info.get('state')} - {info.get('zip_code')}", ln=True)
    pdf.ln(5)

    # Income Summary
    pdf.set_font("Helvetica", 'B', 12)
    pdf.cell(0, 10, "Income Breakdown", ln=True)
    pdf.set_font("Helvetica", '', 11)
    pdf.cell(0, 8, f"Wages: ${income.get('wages', 0)}", ln=True)
    pdf.cell(0, 8, f"Interest: ${income.get('interest', 0)}", ln=True)
    pdf.cell(0, 8, f"Dividends: ${income.get('dividends', 0)}", ln=True)
    pdf.cell(0, 8, f"Business Income: ${income.get('business_income', 0)}", ln=True)
    pdf.cell(0, 8, f"Other Income: ${income.get('other_income', 0)}", ln=True)
    pdf.cell(0, 8, f"Total Income: ${result.get('total_income')}", ln=True)
    pdf.ln(5)

    # Deduction Summary
    pdf.set_font("Helvetica", 'B', 12)
    pdf.cell(0, 10, "Deductions & Dependents", ln=True)
    pdf.set_font("Helvetica", '', 11)
    pdf.cell(0, 8, f"Deduction Type: {deductions.get('deduction_type').title()}", ln=True)
    if deductions.get('deduction_type') == 'itemized':
        itemized = deductions.get('itemized', {})
        pdf.cell(0, 8, f"  Mortgage: ${itemized.get('mortgage', 0)}", ln=True)
        pdf.cell(0, 8, f"  State Taxes: ${itemized.get('state_taxes', 0)}", ln=True)
        pdf.cell(0, 8, f"  Charity: ${itemized.get('charity', 0)}", ln=True)
        pdf.cell(0, 8, f"  Medical: ${itemized.get('medical', 0)}", ln=True)
    pdf.cell(0, 8, f"Dependents: {deductions.get('dependents', 0)}", ln=True)
    pdf.cell(0, 8, f"Total Deductions: ${result.get('total_deductions')}", ln=True)
    pdf.ln(5)

    # Tax Result
    pdf.set_font("Helvetica", 'B', 12)
    pdf.cell(0, 10, "Tax Result", ln=True)
    pdf.set_font("Helvetica", '', 11)
    pdf.cell(0, 8, f"Taxable Income: ${result.get('taxable_income')}", ln=True)
    if result.get('tax_owed') > 0:
        pdf.cell(0, 8, f"Tax Owed: ${result.get('tax_owed')}", ln=True)
    else:
        pdf.cell(0, 8, f"Refund Due: ${result.get('refund_due')}", ln=True)
    pdf.cell(0, 8, f"Effective Tax Rate: {result.get('effective_tax_rate')}%", ln=True)
    pdf.cell(0, 8, f"Marginal Tax Rate: {result.get('marginal_tax_rate')}%", ln=True)

    # Footer
    pdf.ln(15)
    pdf.set_font("Helvetica", 'I', 9)
    pdf.multi_cell(0, 8, "This document is a prototype tax summary and is not intended for official tax filing. Consult a certified tax professional before submission to IRS.")
    
    # Save file
    pdf.output(filename)
