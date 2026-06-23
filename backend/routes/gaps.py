from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db, Company, KnowledgeGap
from models import KnowledgeGapResponse, GapResolve
from services.auth import get_current_company
from services.rag import ingest_document
from typing import List
import uuid, os, tempfile

router = APIRouter(prefix="/gaps", tags=["knowledge-gaps"])


@router.get("/", response_model=List[KnowledgeGapResponse])
def list_gaps(company: Company = Depends(get_current_company), db: Session = Depends(get_db)):
    return db.query(KnowledgeGap).filter(
        KnowledgeGap.company_id == company.id,
        KnowledgeGap.resolved == False
    ).order_by(KnowledgeGap.asked_at.desc()).all()


@router.patch("/{gap_id}/resolve")
def resolve_gap(
    gap_id: str,
    payload: GapResolve,
    company: Company = Depends(get_current_company),
    db: Session = Depends(get_db)
):
    gap = db.query(KnowledgeGap).filter(KnowledgeGap.id == gap_id, KnowledgeGap.company_id == company.id).first()
    if not gap:
        raise HTTPException(status_code=404, detail="Gap not found")

    # Write answer as a temp txt and ingest it into the vector store
    content = f"Q: {gap.question}\nA: {payload.answer}"
    tmp_path = os.path.join(tempfile.gettempdir(), f"gap_{gap_id}.txt")
    with open(tmp_path, "w", encoding="utf-8") as f:
        f.write(content)
    ingest_document(company.id, f"gap_{gap_id}", tmp_path)
    os.remove(tmp_path)

    gap.resolved = True
    gap.answer = payload.answer
    db.commit()
    return {"message": "Gap resolved and added to knowledge base"}
