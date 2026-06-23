from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from sqlalchemy.orm import Session
from database import get_db, Company, Document
from services.auth import get_current_company
from services.rag import ingest_document, delete_document
from services.plans import get_limits
from services.storage import save_local, backup_to_s3, delete_backup
import uuid, os

router = APIRouter(prefix="/documents", tags=["documents"])
ALLOWED_EXTENSIONS = {".pdf", ".docx", ".doc", ".txt"}


@router.post("/upload")
async def upload_document(
    file: UploadFile = File(...),
    company: Company = Depends(get_current_company),
    db: Session = Depends(get_db)
):
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail=f"Unsupported file type: {ext}")

    max_documents = get_limits(company.plan)["max_documents"]
    if max_documents is not None:
        current_count = db.query(Document).filter(Document.company_id == company.id).count()
        if current_count >= max_documents:
            raise HTTPException(
                status_code=403,
                detail=f"Your {company.plan} plan allows up to {max_documents} document(s). Upgrade to upload more."
            )

    doc_id = str(uuid.uuid4())
    filepath = save_local(company.id, f"{doc_id}{ext}", file.file)
    backup_to_s3(company.id, doc_id, filepath)

    ingest_document(company.id, doc_id, filepath)

    doc = Document(id=doc_id, company_id=company.id, filename=file.filename)
    db.add(doc)
    db.commit()
    return {"message": "Document uploaded and indexed", "doc_id": doc_id, "filename": file.filename}


@router.get("/")
def list_documents(company: Company = Depends(get_current_company), db: Session = Depends(get_db)):
    docs = db.query(Document).filter(Document.company_id == company.id).all()
    return [{"id": d.id, "filename": d.filename, "uploaded_at": d.uploaded_at} for d in docs]


@router.delete("/{doc_id}")
def remove_document(
    doc_id: str,
    company: Company = Depends(get_current_company),
    db: Session = Depends(get_db)
):
    doc = db.query(Document).filter(Document.id == doc_id, Document.company_id == company.id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    delete_document(company.id, doc_id)
    delete_backup(company.id, doc_id, os.path.splitext(doc.filename)[1].lower())
    db.delete(doc)
    db.commit()
    return {"message": "Document removed"}
