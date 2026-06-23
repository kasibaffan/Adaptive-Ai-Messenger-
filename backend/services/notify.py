import os
import smtplib
import logging
from email.mime.text import MIMEText

logger = logging.getLogger(__name__)

SMTP_HOST = os.getenv("SMTP_HOST")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")
FROM_EMAIL = os.getenv("FROM_EMAIL", SMTP_USER or "no-reply@adaptive-messenger.local")

TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_SMS_FROM_NUMBER = os.getenv("TWILIO_SMS_FROM_NUMBER")
TWILIO_WHATSAPP_FROM_NUMBER = os.getenv("TWILIO_WHATSAPP_FROM_NUMBER")  # e.g. "whatsapp:+14155238886" (Twilio sandbox is free for testing)

_twilio_client = None


def _get_twilio_client():
    global _twilio_client
    if _twilio_client is None:
        from twilio.rest import Client
        _twilio_client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
    return _twilio_client


def send_email(to_address: str, subject: str, body: str) -> bool:
    """Send an email via SMTP. Returns False (and logs instead) if SMTP isn't configured,
    so the prototype keeps working out of the box without mail credentials."""
    if not (SMTP_HOST and SMTP_USER and SMTP_PASSWORD):
        logger.info(f"[no SMTP configured] would send to {to_address}: {subject} — {body}")
        return False

    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["From"] = FROM_EMAIL
    msg["To"] = to_address

    try:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_USER, SMTP_PASSWORD)
            server.sendmail(FROM_EMAIL, [to_address], msg.as_string())
        return True
    except Exception as e:
        logger.error(f"Failed to send email to {to_address}: {e}")
        return False


def send_sms(to_number: str, body: str) -> bool:
    """Send an SMS via Twilio. Returns False (and logs instead) if Twilio
    isn't configured — same graceful-degradation pattern as send_email."""
    if not (TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN and TWILIO_SMS_FROM_NUMBER):
        logger.info(f"[no Twilio SMS configured] would text {to_number}: {body}")
        return False
    try:
        client = _get_twilio_client()
        client.messages.create(to=to_number, from_=TWILIO_SMS_FROM_NUMBER, body=body)
        return True
    except Exception as e:
        logger.error(f"Failed to send SMS to {to_number}: {e}")
        return False


def send_whatsapp(to_number: str, body: str) -> bool:
    """Send a WhatsApp message via Twilio. Twilio's WhatsApp Sandbox is free
    for development/testing; production numbers need WhatsApp Business
    approval. Returns False (and logs instead) if not configured."""
    if not (TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN and TWILIO_WHATSAPP_FROM_NUMBER):
        logger.info(f"[no Twilio WhatsApp configured] would message {to_number}: {body}")
        return False
    try:
        client = _get_twilio_client()
        to_whatsapp = to_number if to_number.startswith("whatsapp:") else f"whatsapp:{to_number}"
        client.messages.create(to=to_whatsapp, from_=TWILIO_WHATSAPP_FROM_NUMBER, body=body)
        return True
    except Exception as e:
        logger.error(f"Failed to send WhatsApp message to {to_number}: {e}")
        return False
