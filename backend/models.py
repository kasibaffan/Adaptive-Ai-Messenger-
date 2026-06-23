from pydantic import BaseModel, EmailStr
from typing import Optional, List
from datetime import datetime


class CompanyRegister(BaseModel):
    name: str
    email: EmailStr
    password: str
    tone: Optional[str] = "professional"
    persona_name: Optional[str] = "Assistant"


class CompanyLogin(BaseModel):
    email: EmailStr
    password: str


class CompanyUpdate(BaseModel):
    tone: Optional[str] = None
    persona_name: Optional[str] = None
    brand_color: Optional[str] = None
    logo_url: Optional[str] = None
    slack_webhook_url: Optional[str] = None


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    company_id: str
    company_name: str


class ChatRequest(BaseModel):
    message: str
    customer_id: str
    conversation_history: Optional[List[dict]] = []


class ChatResponse(BaseModel):
    reply: str
    sentiment: str
    escalate: bool
    sources_used: int


class ReminderCreate(BaseModel):
    message: str
    trigger_type: str        # "scheduled" | "no_reply" | "event"
    trigger_value: Optional[str] = None  # ISO datetime or hours as string
    channel: Optional[str] = "email"     # "email" | "sms" | "whatsapp"
    customer_email: Optional[EmailStr] = None   # required if channel == "email"
    customer_phone: Optional[str] = None        # required if channel in (sms, whatsapp), E.164 format e.g. +14155551234


class ReminderResponse(BaseModel):
    id: str
    customer_email: Optional[str]
    customer_phone: Optional[str]
    channel: str
    message: str
    trigger_type: str
    trigger_value: Optional[str]
    is_sent: bool
    created_at: datetime

    class Config:
        from_attributes = True


class KnowledgeGapResponse(BaseModel):
    id: str
    question: str
    asked_at: datetime
    resolved: bool
    answer: Optional[str]

    class Config:
        from_attributes = True


class GapResolve(BaseModel):
    answer: str
