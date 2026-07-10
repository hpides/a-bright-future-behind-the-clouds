HOURS_PER_YEAR = 24 * 365  # 8,760

def discount_factor(r, t):
    return 1.0 / ((1.0 + r) ** t)


def npv_of_cash_flows(cash_flows, r):
    """
    cash_flows: dict {year: amount}
    r: discount rate (e.g. 0.05 for 5%)
    """
    return sum(amount * discount_factor(r, t) for t, amount in cash_flows.items())



