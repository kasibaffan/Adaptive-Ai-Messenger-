import chromadb
from chromadb.utils import embedding_functions
import pypdf
import docx
import os
import re
from pathlib import Path

CHROMA_PATH = os.getenv("CHROMA_STORE_PATH", "./chroma_store")
client = chromadb.PersistentClient(path=CHROMA_PATH)

# Uses chromadb's built-in sentence-transformers embeddings (no API key needed)
embed_fn = embedding_functions.DefaultEmbeddingFunction()


def _get_collection(company_id: str):
    return client.get_or_create_collection(
        name=f"company_{company_id}",
        embedding_function=embed_fn
    )


def _extract_text(filepath: str) -> str:
    ext = Path(filepath).suffix.lower()
    if ext == ".pdf":
        reader = pypdf.PdfReader(filepath)
        return "\n".join(page.extract_text() or "" for page in reader.pages)
    elif ext in (".docx", ".doc"):
        doc = docx.Document(filepath)
        return "\n".join(p.text for p in doc.paragraphs)
    else:  # plain text
        with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
            return f.read()


def _split_sentences(text: str) -> list[str]:
    # Split on sentence-ending punctuation AND on line breaks — headers/titles
    # without trailing punctuation would otherwise fuse with the next paragraph
    # into one oversized, unsplittable "sentence".
    parts = re.split(r"(?<=[.!?])\s+|\n+", text.strip())
    return [s.strip() for s in parts if s.strip()]


def _chunk_text(text: str, max_words: int = 40, overlap_sentences: int = 1) -> list[str]:
    """Groups sentences into small, topic-coherent chunks (instead of slicing by a
    raw word count) so retrieval can match a question to a specific passage rather
    than an entire document."""
    sentences = _split_sentences(text)
    if not sentences:
        return []

    chunks = []
    current: list[str] = []
    current_words = 0

    for sentence in sentences:
        words = len(sentence.split())
        if current and current_words + words > max_words:
            chunks.append(" ".join(current))
            current = current[-overlap_sentences:] if overlap_sentences else []
            current_words = sum(len(s.split()) for s in current)
        current.append(sentence)
        current_words += words

    if current:
        chunks.append(" ".join(current))
    return chunks


def ingest_document(company_id: str, doc_id: str, filepath: str):
    text = _extract_text(filepath)
    chunks = _chunk_text(text)
    collection = _get_collection(company_id)

    ids = [f"{doc_id}_chunk_{i}" for i in range(len(chunks))]
    collection.upsert(documents=chunks, ids=ids)


def delete_document(company_id: str, doc_id: str):
    collection = _get_collection(company_id)
    existing = collection.get()
    ids_to_delete = [i for i in existing["ids"] if i.startswith(f"{doc_id}_chunk_")]
    if ids_to_delete:
        collection.delete(ids=ids_to_delete)


def delete_company_collection(company_id: str):
    """Drops a company's entire vector collection — used when deleting the
    company's account, instead of removing documents one at a time."""
    try:
        client.delete_collection(name=f"company_{company_id}")
    except Exception:
        pass  # collection may not exist yet (e.g. company never uploaded a document)


def query_knowledge(company_id: str, question: str, top_k: int = 5) -> tuple[list[str], int, list[float]]:
    collection = _get_collection(company_id)
    count = collection.count()
    if count == 0:
        return [], 0, []
    results = collection.query(query_texts=[question], n_results=min(top_k, count))
    docs = results["documents"][0] if results["documents"] else []
    distances = results["distances"][0] if results.get("distances") else []
    return docs, len(docs), distances
