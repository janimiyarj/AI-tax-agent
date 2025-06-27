def validate_amount(field_name, value, max_allowed):
    try:
        val = float(value.strip()) if value not in ("", None) else 0.0
        if val < 0 or val > max_allowed:
            raise ValueError
        return val
    except:
        raise ValueError(f"{field_name} must be a valid number between 0 and {max_allowed}.")

def calculate_tax(income_data, deductions_data, filing_status, dependents, taxes_paid):
    wages = float(income_data.get("wages", 0) or 0)
    interest = float(income_data.get("interest", 0) or 0)
    dividends = float(income_data.get("dividends", 0) or 0)
    business_income = float(income_data.get("business_income", 0) or 0)
    other_income = float(income_data.get("other_income", 0) or 0)

    total_income = wages + interest + dividends + business_income + other_income

    # Determine deduction
    if deductions_data.get("deduction_type") == "standard":
        if filing_status == "single":
            total_deductions = 13850
        elif filing_status == "married_filing_jointly":
            total_deductions = 27700
        elif filing_status == "head_household":
            total_deductions = 20800
        else:
            total_deductions = 13850  # default
    else:
        itemized = deductions_data.get("itemized", {})
        total_deductions = sum([
            float(itemized.get("mortgage", 0)),
            float(itemized.get("state_taxes", 0)),
            float(itemized.get("charity", 0)),
            float(itemized.get("medical", 0)),
        ])

    taxable_income = max(0, total_income - total_deductions)

    # ✅ Use 2023 progressive tax brackets for SINGLE
    brackets = [
        (11000, 0.10),
        (44725, 0.12),
        (95375, 0.22),
        (182100, 0.24),
        (231250, 0.32),
        (578125, 0.35),
        (float('inf'), 0.37)
    ]

    tax_owed = 0
    remaining_income = taxable_income
    previous_limit = 0
    marginal_rate = 0

    for limit, rate in brackets:
        if taxable_income > limit:
            tax_owed += (limit - previous_limit) * rate
            previous_limit = limit
        else:
            tax_owed += (remaining_income - previous_limit) * rate
            marginal_rate = int(rate * 100)
            break

    refund = max(0, taxes_paid - tax_owed)

    return {
        "wages": wages,
        "interest": interest,
        "dividends": dividends,
        "business_income": business_income,
        "other_income": other_income,
        "total_income": total_income,
        "deduction_type": deductions_data.get("deduction_type"),
        "dependents": dependents,
        "total_deductions": total_deductions,
        "taxable_income": taxable_income,
        "effective_tax_rate": round((tax_owed / total_income) * 100, 2) if total_income else 0,
        "marginal_tax_rate": marginal_rate,
        "tax_owed": round(tax_owed, 2),
        "federal_tax_withheld": taxes_paid,
        "refund": round(refund, 2)
    }


def suggest_smart_filing(income_data, deductions_data, dependents, taxes_paid):
    statuses = ["single", "head_household"]
    base_status = "single"
    base_result = calculate_tax(income_data, deductions_data, base_status, dependents, taxes_paid)
    best_result = base_result
    best_status = base_status

    for status in statuses:
        if status != base_status:
            result = calculate_tax(income_data, deductions_data, status, dependents, taxes_paid)
            if result.get("refund", 0) > best_result.get("refund", 0):  # FIXED HERE
                best_result = result
                best_status = status

    if best_status != base_status:
        return {
            "suggested_status": best_status,
            "refund_boost": round(best_result['refund'] - base_result['refund'], 2),  # FIXED HERE
            "new_result": best_result
        }
    return None


def generate_filled_pdf(personal, income, deductions, dependents, result, output_path):
    from fpdf import FPDF

    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)

    pdf.cell(200, 10, "AI Tax Summary", ln=True, align="C")
    pdf.ln(5)

    for section, data in {
        "Personal Info": personal,
        "Income Details": income,
        "Deductions": deductions,
        "Dependents": {"dependents": dependents},
        "Results": result
    }.items():
        pdf.set_font("Arial", style="B", size=12)
        pdf.cell(200, 10, section, ln=True)
        pdf.set_font("Arial", size=11)
        for key, value in data.items():
            pdf.cell(200, 8, f"{key.replace('_', ' ').title()}: {value}", ln=True)
        pdf.ln(3)

    pdf.output(output_path)
