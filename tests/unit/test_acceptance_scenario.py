from scripts.acceptance_scenario import reconcile_balance


def test_reconcile_balance_matches_transactions() -> None:
    transactions = [
        {"transaction_type": "initial_grant", "amount": 100},
        {"transaction_type": "inference_hold", "amount": -7},
        {"transaction_type": "inference_capture", "amount": 0},
    ]

    assert reconcile_balance(transactions, reserved_balance=0) == 93
