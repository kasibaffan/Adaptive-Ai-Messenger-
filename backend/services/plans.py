PLAN_LIMITS = {
    "free": {
        "max_documents": 1,
        "max_messages_per_month": 100,
        "label": "Free",
        "price_display": "$0",
    },
    "pro": {
        "max_documents": 20,
        "max_messages_per_month": 5000,
        "label": "Pro",
        "price_display": "$49/month",
    },
    "enterprise": {
        "max_documents": None,  # unlimited
        "max_messages_per_month": None,  # unlimited
        "label": "Enterprise",
        "price_display": "Contact sales",
    },
}


def get_limits(plan: str) -> dict:
    return PLAN_LIMITS.get(plan, PLAN_LIMITS["free"])
