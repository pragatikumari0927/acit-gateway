"""Literal Protocol envelopes used by parser tests."""

AP2_VALID = {
    "vct": "mandate.checkout.open.1",
    "sub": "agent_01",
    "exp": 1893456000,
    "cnf": {"kid": "agent_01"},
    "constraints": {
        "max_amount": {"value": "50000", "currency": "INR"},
        "sku_allowlist": ["sku_tea"],
    },
    "items": [
        {"sku": "sku_tea", "quantity": 1, "unit_amount_paise": 10000},
    ],
}

P3P_VALID = {
    "agent_id": "agent_01",
    "authorization": {
        "max_txn_paise": 50000,
        "currency": "INR",
        "exp": 1893456000,
        "skus": ["sku_tea"],
    },
    "order": {
        "items": [
            {"sku": "sku_tea", "quantity": 1, "unit_amount_paise": 10000},
        ]
    },
}

TAP_VALID = {
    "agent_id": "agent_01",
    "max_amount_paise": 50000,
    "currency": "INR",
    "sku_allowlist": ["sku_tea"],
    "exp": 1893456000,
    "items": [
        {"sku": "sku_tea", "quantity": 1, "unit_amount_paise": 10000},
    ],
}

UAP_VALID = {
    "agent_id": "agent_01",
    "max_amount_paise": 50000,
    "currency": "INR",
    "sku_allowlist": ["sku_tea"],
    "exp": 1893456000,
    "user_id": "user_01",
    "items": [
        {"sku": "sku_tea", "quantity": 1, "unit_amount_paise": 10000},
    ],
}
