from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.date import DateTrigger
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from database import SessionLocal, Reminder, Company
from services.notify import send_email, send_sms, send_whatsapp
import logging

scheduler = BackgroundScheduler()
logger = logging.getLogger(__name__)


def _mark_sent(reminder_id: str):
    db: Session = SessionLocal()
    try:
        reminder = db.query(Reminder).filter(Reminder.id == reminder_id).first()
        if reminder and not reminder.is_sent:
            company = db.query(Company).filter(Company.id == reminder.company_id).first()
            sender_name = company.persona_name if company else "Your assistant"
            company_name = company.name if company else "the team"
            body = f"{reminder.message}\n\n— {sender_name} ({company_name})"

            channel = reminder.channel or "email"
            if channel == "sms":
                recipient = reminder.customer_phone
                delivered = send_sms(to_number=recipient, body=body)
            elif channel == "whatsapp":
                recipient = reminder.customer_phone
                delivered = send_whatsapp(to_number=recipient, body=body)
            else:
                recipient = reminder.customer_email
                delivered = send_email(
                    to_address=recipient,
                    subject=f"Reminder from {company_name}",
                    body=body
                )

            reminder.is_sent = True
            reminder.sent_at = datetime.utcnow()
            db.commit()
            logger.info(
                f"Reminder {reminder_id} ({channel}) to {recipient}: "
                f"{'sent' if delivered else 'logged (not configured)'}"
            )
    finally:
        db.close()


def schedule_reminder(reminder_id: str, trigger_type: str, trigger_value: str):
    if trigger_type == "scheduled":
        run_at = datetime.fromisoformat(trigger_value)
    elif trigger_type == "no_reply":
        hours = float(trigger_value)
        run_at = datetime.utcnow() + timedelta(hours=hours)
    elif trigger_type == "event":
        run_at = datetime.fromisoformat(trigger_value)
    else:
        return

    if run_at <= datetime.utcnow():
        _mark_sent(reminder_id)
        return

    scheduler.add_job(
        _mark_sent,
        trigger=DateTrigger(run_date=run_at),
        args=[reminder_id],
        id=reminder_id,
        replace_existing=True
    )


def cancel_reminder(reminder_id: str):
    if scheduler.get_job(reminder_id):
        scheduler.remove_job(reminder_id)


def start_scheduler():
    if not scheduler.running:
        scheduler.start()


def stop_scheduler():
    if scheduler.running:
        scheduler.shutdown()
