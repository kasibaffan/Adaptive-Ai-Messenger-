import os
import shutil
import logging

logger = logging.getLogger(__name__)

UPLOAD_DIR = os.getenv("UPLOAD_DIR", "./uploads")

S3_BUCKET = os.getenv("S3_BUCKET")
S3_ENDPOINT_URL = os.getenv("S3_ENDPOINT_URL")  # set for R2/B2/MinIO; leave blank for AWS S3
S3_ACCESS_KEY_ID = os.getenv("S3_ACCESS_KEY_ID")
S3_SECRET_ACCESS_KEY = os.getenv("S3_SECRET_ACCESS_KEY")
S3_REGION = os.getenv("S3_REGION", "auto")

_s3_client = None


def is_s3_configured() -> bool:
    return bool(S3_BUCKET and S3_ACCESS_KEY_ID and S3_SECRET_ACCESS_KEY)


def _get_s3_client():
    global _s3_client
    if _s3_client is None:
        import boto3
        _s3_client = boto3.client(
            "s3",
            endpoint_url=S3_ENDPOINT_URL or None,
            aws_access_key_id=S3_ACCESS_KEY_ID,
            aws_secret_access_key=S3_SECRET_ACCESS_KEY,
            region_name=S3_REGION,
        )
    return _s3_client


def save_local(company_id: str, filename_with_ext: str, file_obj) -> str:
    """Writes the uploaded file to local disk — required either way, since the
    PDF/DOCX parsing libraries need a real file path — and returns that path."""
    company_dir = os.path.join(UPLOAD_DIR, company_id)
    os.makedirs(company_dir, exist_ok=True)
    local_path = os.path.join(company_dir, filename_with_ext)
    with open(local_path, "wb") as f:
        shutil.copyfileobj(file_obj, f)
    return local_path


def backup_to_s3(company_id: str, doc_id: str, local_path: str):
    """Best-effort durable backup of the raw uploaded file to S3-compatible
    storage (AWS S3, Cloudflare R2, Backblaze B2, etc). No-ops if S3 isn't
    configured — local disk stays the source of truth for re-ingestion, same
    as before this feature existed. This guards against losing uploaded
    documents on hosts with ephemeral disks (most PaaS free tiers)."""
    if not is_s3_configured():
        return
    try:
        s3 = _get_s3_client()
        key = f"{company_id}/{doc_id}{os.path.splitext(local_path)[1]}"
        s3.upload_file(local_path, S3_BUCKET, key)
    except Exception as e:
        logger.warning(f"S3 backup failed for {local_path}: {e}")


def delete_backup(company_id: str, doc_id: str, ext: str):
    if not is_s3_configured():
        return
    try:
        s3 = _get_s3_client()
        key = f"{company_id}/{doc_id}{ext}"
        s3.delete_object(Bucket=S3_BUCKET, Key=key)
    except Exception as e:
        logger.warning(f"S3 delete failed for {company_id}/{doc_id}: {e}")
