import os
import logging

logger = logging.getLogger(__name__)

STRIPE_SECRET_KEY = os.getenv("STRIPE_SECRET_KEY")
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET")
STRIPE_PRO_PRICE_ID = os.getenv("STRIPE_PRO_PRICE_ID")
APP_BASE_URL = os.getenv("APP_BASE_URL", "http://localhost:8000")

_stripe = None


def is_configured() -> bool:
    return bool(STRIPE_SECRET_KEY and STRIPE_PRO_PRICE_ID)


def _get_stripe():
    global _stripe
    if _stripe is None:
        import stripe
        stripe.api_key = STRIPE_SECRET_KEY
        _stripe = stripe
    return _stripe


def create_checkout_session(company_id: str, company_email: str, stripe_customer_id: str | None) -> str:
    """Returns a Stripe Checkout URL for upgrading to the Pro plan. Raises
    RuntimeError if Stripe isn't configured yet — callers should catch this
    and show a friendly "billing not set up" message instead of a 500."""
    if not is_configured():
        raise RuntimeError("Billing is not configured yet")

    stripe = _get_stripe()
    session = stripe.checkout.Session.create(
        mode="subscription",
        customer=stripe_customer_id,
        customer_email=company_email if not stripe_customer_id else None,
        line_items=[{"price": STRIPE_PRO_PRICE_ID, "quantity": 1}],
        success_url=f"{APP_BASE_URL}/?billing=success",
        cancel_url=f"{APP_BASE_URL}/?billing=cancelled",
        client_reference_id=company_id,
        metadata={"company_id": company_id},
        subscription_data={"metadata": {"company_id": company_id}},
    )
    return session.url


def verify_webhook(payload: bytes, signature: str):
    """Validates and parses a Stripe webhook payload. Raises if Stripe isn't
    configured or the signature is invalid."""
    if not STRIPE_SECRET_KEY or not STRIPE_WEBHOOK_SECRET:
        raise RuntimeError("Billing webhooks are not configured yet")
    stripe = _get_stripe()
    return stripe.Webhook.construct_event(payload, signature, STRIPE_WEBHOOK_SECRET)


def extract_subscription_update(event) -> dict | None:
    """Maps a Stripe event to the fields that should be written onto the
    Company row, or None if the event type isn't one we act on."""
    event_type = event["type"]
    obj = event["data"]["object"]

    if event_type == "checkout.session.completed":
        return {
            "company_id": obj.get("client_reference_id") or obj.get("metadata", {}).get("company_id"),
            "stripe_customer_id": obj.get("customer"),
            "stripe_subscription_id": obj.get("subscription"),
            "plan": "pro",
            "subscription_status": "active",
        }

    if event_type in ("customer.subscription.updated", "customer.subscription.deleted"):
        status = obj.get("status")
        plan = "pro" if status in ("active", "trialing", "past_due") else "free"
        return {
            "company_id": obj.get("metadata", {}).get("company_id"),
            "stripe_customer_id": obj.get("customer"),
            "stripe_subscription_id": obj.get("id"),
            "plan": plan,
            "subscription_status": status,
        }

    return None
