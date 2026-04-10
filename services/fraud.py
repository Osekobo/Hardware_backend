def run_fraud_checks(order, amount, receipt):

    # Rule 1: duplicate payment
    if order.mpesa_receipt:
        return False

    # Rule 2: amount mismatch
    if order.total != amount:
        return False

    # Rule 3: invalid order
    if not order:
        return False

    return True