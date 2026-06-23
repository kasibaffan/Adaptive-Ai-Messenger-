from fastapi import APIRouter, Depends, Request, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, timedelta
from database import get_db, Company, ChatLog, KnowledgeGap, Document
from models import ChatRequest, ChatResponse
from services.auth import get_current_company
from services.rag import query_knowledge
from services.llm import chat_with_company_context, detect_sentiment, is_unanswerable
from services.rate_limit import limiter
from services.plans import get_limits
from services.slack import notify_slack
import uuid

router = APIRouter(prefix="/chat", tags=["chat"])
ESCALATION_THRESHOLD = "negative"
CAPACITY_MESSAGE = "Our assistant has reached its monthly capacity. Please reach out to us directly and we'll help you from there."


@router.post("/{company_id}", response_model=ChatResponse)
@limiter.limit("20/minute")
def chat(
    request: Request,
    company_id: str,
    payload: ChatRequest,
    db: Session = Depends(get_db)
):
    # Public endpoint — customers interact without login
    company = db.query(Company).filter(Company.id == company_id).first()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    max_messages = get_limits(company.plan)["max_messages_per_month"]
    if max_messages is not None:
        month_start = datetime.utcnow().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        messages_this_month = db.query(ChatLog).filter(
            ChatLog.company_id == company_id,
            ChatLog.role == "user",
            ChatLog.timestamp >= month_start
        ).count()
        if messages_this_month >= max_messages:
            return ChatResponse(reply=CAPACITY_MESSAGE, sentiment="neutral", escalate=True, sources_used=0)

    context_chunks, sources_count, distances = query_knowledge(company_id, payload.message)

    reply = chat_with_company_context(
        company_name=company.name,
        persona_name=company.persona_name,
        tone=company.tone,
        context_chunks=context_chunks,
        conversation_history=payload.conversation_history,
        user_message=payload.message,
        distances=distances
    )

    sentiment = detect_sentiment(payload.message)
    escalate = sentiment == ESCALATION_THRESHOLD

    # Log the exchange
    for role, content in [("user", payload.message), ("assistant", reply)]:
        db.add(ChatLog(
            id=str(uuid.uuid4()),
            company_id=company_id,
            customer_id=payload.customer_id,
            role=role,
            content=content,
            sentiment=sentiment if role == "user" else None
        ))

    # Log knowledge gap if AI couldn't answer
    if is_unanswerable(reply):
        db.add(KnowledgeGap(
            id=str(uuid.uuid4()),
            company_id=company_id,
            question=payload.message
        ))
        notify_slack(
            company.slack_webhook_url,
            f"❓ *{company.name}*: new question your assistant couldn't answer:\n>{payload.message}"
        )

    if escalate:
        notify_slack(
            company.slack_webhook_url,
            f"⚠️ *{company.name}*: a customer message was flagged as negative sentiment:\n>{payload.message}"
        )

    db.commit()
    return ChatResponse(reply=reply, sentiment=sentiment, escalate=escalate, sources_used=sources_count)


@router.get("/logs/all")
def get_chat_logs(company: Company = Depends(get_current_company), db: Session = Depends(get_db)):
    logs = db.query(ChatLog).filter(ChatLog.company_id == company.id).order_by(ChatLog.timestamp.desc()).limit(100).all()
    return [{"id": l.id, "customer_id": l.customer_id, "role": l.role, "content": l.content,
             "sentiment": l.sentiment, "timestamp": l.timestamp} for l in logs]


@router.get("/stats")
def get_chat_stats(company: Company = Depends(get_current_company), db: Session = Depends(get_db)):
    now = datetime.utcnow()
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    window_start = now - timedelta(days=13)

    messages_this_month = db.query(ChatLog).filter(
        ChatLog.company_id == company.id,
        ChatLog.role == "user",
        ChatLog.timestamp >= month_start
    ).count()

    sentiment_rows = db.query(ChatLog.sentiment, func.count(ChatLog.id)).filter(
        ChatLog.company_id == company.id,
        ChatLog.role == "user"
    ).group_by(ChatLog.sentiment).all()
    sentiment_breakdown = {"positive": 0, "neutral": 0, "negative": 0}
    for sentiment, count in sentiment_rows:
        if sentiment in sentiment_breakdown:
            sentiment_breakdown[sentiment] = count

    recent_logs = db.query(ChatLog.timestamp).filter(
        ChatLog.company_id == company.id,
        ChatLog.role == "user",
        ChatLog.timestamp >= window_start.replace(hour=0, minute=0, second=0, microsecond=0)
    ).all()
    counts_by_day: dict[str, int] = {}
    for (timestamp,) in recent_logs:
        day = timestamp.strftime("%Y-%m-%d")
        counts_by_day[day] = counts_by_day.get(day, 0) + 1

    daily_series = []
    for i in range(13, -1, -1):
        day = (now - timedelta(days=i)).strftime("%Y-%m-%d")
        daily_series.append({"date": day, "count": counts_by_day.get(day, 0)})

    limits = get_limits(company.plan)
    documents_used = db.query(Document).filter(Document.company_id == company.id).count()

    return {
        "plan": company.plan,
        "messages_this_month": messages_this_month,
        "messages_limit": limits["max_messages_per_month"],
        "documents_used": documents_used,
        "documents_limit": limits["max_documents"],
        "sentiment_breakdown": sentiment_breakdown,
        "daily_counts": daily_series,
    }


@router.get("/{company_id}/profile")
def get_public_profile(company_id: str, db: Session = Depends(get_db)):
    """Public branding info for the embeddable widget — persona name, accent
    color, logo — fetched cross-origin from whatever site embeds the widget."""
    company = db.query(Company).filter(Company.id == company_id).first()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    return {
        "persona_name": company.persona_name,
        "brand_color": company.brand_color,
        "logo_url": company.logo_url,
    }
