from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from database import get_db, Company
from services.auth import get_current_company
from services.plans import PLAN_LIMITS, get_limits
from services import billing
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/billing", tags=["billing"])


@router.get("/plans")
def list_plans():
    return PLAN_LIMITS


@router.get("/status")
def billing_status(company: Company = Depends(get_current_company)):
    return {
        "plan": company.plan,
        "subscription_status": company.subscription_status,
        "limits": get_limits(company.plan),
        "billing_configured": billing.is_configured(),
    }


@router.post("/checkout")
def create_checkout(
    company: Company = Depends(get_current_company),
    db: Session = Depends(get_db)
):
    if not billing.is_configured():
        raise HTTPException(
            status_code=503,
            detail="Billing isn't set up yet. Add Stripe API keys to enable upgrades."
        )
    try:
        url = billing.create_checkout_session(
            company_id=company.id,
            company_email=company.email,
            stripe_customer_id=company.stripe_customer_id
        )
    except Exception as e:
        logger.error(f"Stripe checkout session creation failed: {e}")
        raise HTTPException(status_code=502, detail="Could not start checkout. Please try again later.")
    return {"checkout_url": url}


@router.post("/webhook")
async def stripe_webhook(request: Request, db: Session = Depends(get_db)):
    payload = await request.body()
    signature = request.headers.get("stripe-signature", "")

    try:
        event = billing.verify_webhook(payload, signature)
    except Exception as e:
        logger.warning(f"Stripe webhook verification failed: {e}")
        raise HTTPException(status_code=400, detail="Invalid webhook signature")

    update = billing.extract_subscription_update(event)
    if update and update.get("company_id"):
        company = db.query(Company).filter(Company.id == update["company_id"]).first()
        if company:
            company.plan = update["plan"]
            company.subscription_status = update["subscription_status"]
            if update.get("stripe_customer_id"):
                company.stripe_customer_id = update["stripe_customer_id"]
            if update.get("stripe_subscription_id"):
                company.stripe_subscription_id = update["stripe_subscription_id"]
            db.commit()

    return {"received": True}
