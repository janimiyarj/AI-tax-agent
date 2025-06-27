# smart_suggestion.py
from tax_logic import calculate_tax

def suggest_better_option(income, deductions, personal_info, taxes_paid):
    """
    Suggests a better filing status that results in a higher refund (if any),
    by simulating tax calculations across all valid statuses.
    """

    original_status = personal_info.get("filing_status")
    num_dependents = deductions.get("dependents", 0)

    # Calculate tax for current status
    current_result = calculate_tax(
        income, deductions, original_status, num_dependents, taxes_paid
    )

    # Exit early if there's an error or zero refund
    if "error" in current_result or current_result.get("refund", 0) <= 0:
        return None

    best_result = current_result
    best_status = original_status
    max_gain = 0

    # Try all other statuses and compare refunds
    alternative_statuses = ["single", "married_joint", "married_separate", "head_household"]

    for alt_status in alternative_statuses:
        if alt_status == original_status:
            continue

        alt_result = calculate_tax(
            income, deductions, alt_status, num_dependents, taxes_paid
        )

        if "error" in alt_result:
            continue

        gain = alt_result.get("refund", 0) - current_result.get("refund", 0)
        if gain > max_gain:
            best_result = alt_result
            best_status = alt_status
            max_gain = gain

    if best_status != original_status and max_gain > 0:
        return {
            "suggested_status": best_status,
            "refund_boost": round(max_gain, 2),
            "new_result": best_result
        }

    return None
