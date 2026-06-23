from sqlalchemy import create_engine, Column, String, Integer, DateTime, Text, Boolean, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime
import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./messenger.db")

# Managed Postgres providers (Neon, Supabase, etc.) hand out bare
# "postgresql://" connection strings, but the psycopg3 driver in
# requirements.txt needs the "+psycopg" dialect suffix in the URL. Normalize
# it here so users can paste the connection string as-is.
if DATABASE_URL.startswith("postgresql://"):
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+psycopg://", 1)

# check_same_thread is a SQLite-only connect arg — passing it to a Postgres
# driver would raise. SQLite is the zero-setup dev/demo default; production
# should point DATABASE_URL at a managed Postgres instance instead.
connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class Company(Base):
    __tablename__ = "companies"
    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    email = Column(String, unique=True, nullable=False)
    password_hash = Column(String, nullable=False)
    tone = Column(String, default="professional")  # professional / friendly / formal
    persona_name = Column(String, default="Assistant")
    brand_color = Column(String, default="#4f46e5")
    logo_url = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    plan = Column(String, default="free")  # free / pro / enterprise
    stripe_customer_id = Column(String, nullable=True)
    stripe_subscription_id = Column(String, nullable=True)
    subscription_status = Column(String, nullable=True)  # active / past_due / canceled, etc.

    # Slack Incoming Webhook URL — company-pasted, no OAuth/app-install needed.
    # Used to notify the company's Slack of escalations and new knowledge gaps.
    slack_webhook_url = Column(String, nullable=True)

    documents = relationship("Document", back_populates="company", cascade="all, delete")
    reminders = relationship("Reminder", back_populates="company", cascade="all, delete")
    knowledge_gaps = relationship("KnowledgeGap", back_populates="company", cascade="all, delete")


class Document(Base):
    __tablename__ = "documents"
    id = Column(String, primary_key=True)
    company_id = Column(String, ForeignKey("companies.id"), nullable=False)
    filename = Column(String, nullable=False)
    uploaded_at = Column(DateTime, default=datetime.utcnow)
    company = relationship("Company", back_populates="documents")


class Reminder(Base):
    __tablename__ = "reminders"
    id = Column(String, primary_key=True)
    company_id = Column(String, ForeignKey("companies.id"), nullable=False)
    customer_email = Column(String, nullable=True)
    customer_phone = Column(String, nullable=True)  # required for sms/whatsapp channel
    channel = Column(String, default="email")  # email / sms / whatsapp
    message = Column(Text, nullable=False)
    trigger_type = Column(String, nullable=False)  # scheduled / no_reply / event
    trigger_value = Column(String, nullable=True)  # datetime string or delay in hours
    is_sent = Column(Boolean, default=False)
    sent_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    company = relationship("Company", back_populates="reminders")


class KnowledgeGap(Base):
    __tablename__ = "knowledge_gaps"
    id = Column(String, primary_key=True)
    company_id = Column(String, ForeignKey("companies.id"), nullable=False)
    question = Column(Text, nullable=False)
    asked_at = Column(DateTime, default=datetime.utcnow)
    resolved = Column(Boolean, default=False)
    answer = Column(Text, nullable=True)
    company = relationship("Company", back_populates="knowledge_gaps")


class ChatLog(Base):
    __tablename__ = "chat_logs"
    id = Column(String, primary_key=True)
    company_id = Column(String, nullable=False)
    customer_id = Column(String, nullable=False)
    role = Column(String, nullable=False)  # user / assistant
    content = Column(Text, nullable=False)
    sentiment = Column(String, nullable=True)  # positive / neutral / negative
    timestamp = Column(DateTime, default=datetime.utcnow)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    Base.metadata.create_all(bind=engine)
