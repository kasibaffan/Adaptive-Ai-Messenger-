
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db, Company, Reminder
from models import ReminderCreate, ReminderResponse
from services.auth import get_current_company
from services.scheduler import schedule_reminder, cancel_reminder
from typing import List
import uuid

router = APIRouter(prefix="/reminders", tags=["reminders"])


VALID_CHANNELS = {"email", "sms", "whatsapp"}


@router.post("/", response_model=ReminderResponse)
def create_reminder(
    payload: ReminderCreate,
    company: Company = Depends(get_current_company),
    db: Session = Depends(get_db)
):
    channel = payload.channel or "email"
    if channel not in VALID_CHANNELS:
        raise HTTPException(status_code=400, detail=f"channel must be one of {sorted(VALID_CHANNELS)}")
    if channel == "email" and not payload.customer_email:
        raise HTTPException(status_code=400, detail="customer_email is required for the email channel")
    if channel in ("sms", "whatsapp") and not payload.customer_phone:
        raise HTTPException(status_code=400, detail="customer_phone is required for the sms/whatsapp channel")

    reminder = Reminder(
        id=str(uuid.uuid4()),
        company_id=company.id,
        customer_email=payload.customer_email,
        customer_phone=payload.customer_phone,
        channel=channel,
        message=payload.message,
        trigger_type=payload.trigger_type,
        trigger_value=payload.trigger_value
    )
    db.add(reminder)
    db.commit()
    db.refresh(reminder)

    if payload.trigger_value:
        schedule_reminder(reminder.id, payload.trigger_type, payload.trigger_value)

    return reminder


@router.get("/", response_model=List[ReminderResponse])
def list_reminders(company: Company = Depends(get_current_company), db: Session = Depends(get_db)):
    return db.query(Reminder).filter(Reminder.company_id == company.id).all()


@router.delete("/{reminder_id}")
def delete_reminder(
    reminder_id: str,
    company: Company = Depends(get_current_company),
    db: Session = Depends(get_db)
):
    reminder = db.query(Reminder).filter(Reminder.id == reminder_id, Reminder.company_id == company.id).first()
    if not reminder:
        raise HTTPException(status_code=404, detail="Reminder not found")
    cancel_reminder(reminder_id)
    db.delete(reminder)
    db.commit()
    return {"message": "Reminder deleted"}
