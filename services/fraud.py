def run_fraud_checks(order, amount, receipt):

    if order.mpesa_receipt:
        return False

    if order.total != amount:
        return False

    if not order:
        return False

    return True