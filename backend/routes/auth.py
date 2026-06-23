from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from database import get_db, Company
from models import CompanyRegister, CompanyLogin, TokenResponse, CompanyUpdate
from services.auth import hash_password, verify_password, create_token, get_current_company
from services.rate_limit import limiter
import uuid

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=TokenResponse)
@limiter.limit("5/minute")
def register(request: Request, payload: CompanyRegister, db: Session = Depends(get_db)):
    if db.query(Company).filter(Company.email == payload.email).first():
        raise HTTPException(status_code=400, detail="Email already registered")

    company = Company(
        id=str(uuid.uuid4()),
        name=payload.name,
        email=payload.email,
        password_hash=hash_password(payload.password),
        tone=payload.tone,
        persona_name=payload.persona_name
    )
    db.add(company)
    db.commit()
    return TokenResponse(
        access_token=create_token(company.id),
        company_id=company.id,
        company_name=company.name
    )


@router.post("/login", response_model=TokenResponse)
@limiter.limit("5/minute")
def login(request: Request, payload: CompanyLogin, db: Session = Depends(get_db)):
    company = db.query(Company).filter(Company.email == payload.email).first()
    if not company or not verify_password(payload.password, company.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    return TokenResponse(
        access_token=create_token(company.id),
        company_id=company.id,
        company_name=company.name
    )


@router.patch("/settings")
def update_settings(
    payload: CompanyUpdate,
    company: Company = Depends(get_current_company),
    db: Session = Depends(get_db)
):
    if payload.tone:
        company.tone = payload.tone
    if payload.persona_name:
        company.persona_name = payload.persona_name
    if payload.brand_color:
        company.brand_color = payload.brand_color
    if payload.logo_url is not None:
        company.logo_url = payload.logo_url
    if payload.slack_webhook_url is not None:
        company.slack_webhook_url = payload.slack_webhook_url
    db.commit()
    return {
        "message": "Settings updated",
        "tone": company.tone,
        "persona_name": company.persona_name,
        "brand_color": company.brand_color,
        "logo_url": company.logo_url,
        "slack_webhook_url": company.slack_webhook_url
    }


@router.get("/me")
def me(company: Company = Depends(get_current_company)):
    return {
        "id": company.id,
        "name": company.name,
        "email": company.email,
        "tone": company.tone,
        "persona_name": company.persona_name,
        "brand_color": company.brand_color,
        "logo_url": company.logo_url,
        "plan": company.plan,
        "slack_webhook_url": company.slack_webhook_url
    }
