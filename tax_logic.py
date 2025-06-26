def validate_amount(field_name, value, max_allowed):
    try:
        val = float(value) if value not in ("", None) else 0.0
        if val < 0 or val > max_allowed:
            raise ValueError
        return val
    except:
        raise ValueError(f"{field_name} must be a valid number between 0 and {max_allowed}.")


def calculate_tax(income_data, deductions_data, filing_status, dependents, taxes_paid=0):
    try:
        # --- Validate and sum income
        wages = validate_amount("Wages", income_data.get("wages", 0), 1_000_000)
        interest = validate_amount("Interest", income_data.get("interest", 0), 500_000)
        dividends = validate_amount("Dividends", income_data.get("dividends", 0), 500_000)
        business_income = validate_amount("Business Income", income_data.get("business_income", 0), 5_000_000)
        other_income = validate_amount("Other Income", income_data.get("other_income", 0), 2_000_000)
        total_income = wages + interest + dividends + business_income + other_income

        # --- Calculate total deductions
        deduction_type = deductions_data.get('deduction_type', 'standard')
        if deduction_type == 'standard':
            standard_deductions = {
                'single': 13850,
                'married_joint': 27700,
                'married_separate': 13850,
                'head_household': 20800
            }
            total_deductions = standard_deductions.get(filing_status, 13850)
        else:
            itemized = deductions_data.get('itemized', {})
            mortgage = validate_amount("Mortgage", itemized.get('mortgage', 0), 100_000)
            state_taxes = validate_amount("State Taxes", itemized.get('state_taxes', 0), 100_000)
            charity = validate_amount("Charity", itemized.get('charity', 0), 100_000)
            medical = validate_amount("Medical", itemized.get('medical', 0), 100_000)
            total_deductions = mortgage + state_taxes + charity + medical

        taxable_income = max(0, total_income - total_deductions)

        # --- Tax brackets (2023)
        brackets = {
            "single": [
                (0, 11000, 0.10),
                (11000, 44725, 0.12),
                (44725, 95375, 0.22),
                (95375, 182100, 0.24)
            ],
            "married_joint": [
                (0, 22000, 0.10),
                (22000, 89450, 0.12),
                (89450, 190750, 0.22),
                (190750, 364200, 0.24)
            ],
            "married_separate": [
                (0, 11000, 0.10),
                (11000, 44725, 0.12),
                (44725, 95375, 0.22),
                (95375, 182100, 0.24)
            ],
            "head_household": [
                (0, 15700, 0.10),
                (15700, 59850, 0.12),
                (59850, 95350, 0.22),
                (95350, 182100, 0.24)
            ]
        }

        # --- Tax calculation
        tax_owed = 0
        marginal_rate = 0
        for lower, upper, rate in brackets.get(filing_status, brackets["single"]):
            if taxable_income > lower:
                income_in_bracket = min(taxable_income, upper) - lower
                tax_owed += income_in_bracket * rate
                marginal_rate = rate
            else:
                break

        effective_rate = (tax_owed / total_income * 100) if total_income > 0 else 0

        # --- Refund / Tax Due
        tax_due = max(0, tax_owed - taxes_paid)
        refund = max(0, taxes_paid - tax_owed)

        # --- Dependent credit (only when tax owed is $0)
        dependent_credit = 0
        if tax_owed == 0 and dependents > 0:
            dependent_credit = dependents * 12
            refund += dependent_credit  # add to existing refund

        return {
            "total_income": round(total_income, 2),
            "total_deductions": round(total_deductions, 2),
            "taxable_income": round(taxable_income, 2),
            "tax_owed": round(tax_owed, 2),
            "tax_due": round(tax_due, 2),
            "refund": round(refund, 2),
            "effective_tax_rate": round(effective_rate, 2),
            "marginal_tax_rate": int(marginal_rate * 100)
        }

    except ValueError as ve:
        return {"error": str(ve)}
    except Exception as e:
        return {"error": f"Unexpected error: {str(e)}"}
