import logging
import random

logger = logging.getLogger(__name__)

FALLBACK_MESSAGE = (
    "I don't have that information yet — our team will follow up with you shortly."
)

NEGATIVE_KEYWORDS = {
    "angry", "furious", "terrible", "awful", "horrible", "worst", "useless",
    "refund", "cancel", "scam", "fraud", "unacceptable", "disgusted",
    "complaint", "sue", "lawsuit", "never again", "disappointed", "ridiculous",
}

POSITIVE_KEYWORDS = {
    "thanks", "thank you", "great", "awesome", "love", "perfect", "excellent",
    "amazing", "happy", "wonderful", "appreciate",
}

# Chroma reports squared-L2 distance between normalized embeddings (roughly 0-2).
# Above this, the closest chunk found is too unrelated to the question to use.
# Calibrated empirically: genuine matches with different phrasing land ~1.0-1.45;
# off-topic questions land ~1.6+.
MAX_RELEVANT_DISTANCE = 1.5

# Below this confidence, the QA model's extracted span is unreliable — fall back
# to the full matched passage instead of a possibly-wrong short answer.
MIN_QA_SCORE = 0.05

REPLY_TEMPLATES = [
    "{answer}",
    "Here's what I found: {answer}",
    "Sure — {answer}",
    "Good question. {answer}",
    "{persona} here: {answer}",
]


def detect_sentiment(text: str) -> str:
    """Free, offline sentiment check based on keyword matching — no LLM call."""
    lowered = text.lower()
    if any(kw in lowered for kw in NEGATIVE_KEYWORDS):
        return "negative"
    if any(kw in lowered for kw in POSITIVE_KEYWORDS):
        return "positive"
    return "neutral"


_qa_pipeline = None


def _get_qa_pipeline():
    """Lazily loads a local, free extractive question-answering model
    (DistilBERT fine-tuned on SQuAD). Downloads once from Hugging Face and
    then runs entirely offline — no API key, no per-message cost."""
    global _qa_pipeline
    if _qa_pipeline is None:
        from transformers import pipeline
        _qa_pipeline = pipeline(
            "question-answering",
            model="distilbert-base-cased-distilled-squad",
            framework="pt",
        )
    return _qa_pipeline


def _extract_answer(question: str, context: str) -> tuple[str, float]:
    qa = _get_qa_pipeline()
    result = qa(question=question, context=context[:3000])
    return result["answer"].strip(), result["score"]


def chat_with_company_context(
    company_name: str,
    persona_name: str,
    tone: str,
    context_chunks: list[str],
    conversation_history: list[dict],
    user_message: str,
    distances: list[float] | None = None,
) -> str:
    """Answers only from the company's own uploaded documents. Retrieval picks
    the most relevant passage(s); a local NLP model then extracts the precise
    answer phrase from that passage instead of returning the whole thing
    verbatim. No external LLM, no API key, no hallucination outside the
    provided knowledge base."""
    if not context_chunks:
        return FALLBACK_MESSAGE

    if distances and distances[0] > MAX_RELEVANT_DISTANCE:
        return FALLBACK_MESSAGE

    context = " ".join(context_chunks[:3])
    try:
        answer, score = _extract_answer(user_message, context)
    except Exception as e:
        logger.warning(f"QA extraction failed, falling back to raw passage: {e}")
        answer, score = "", 0.0

    body = answer if answer and score >= MIN_QA_SCORE else context_chunks[0].strip()

    template = random.choice(REPLY_TEMPLATES)
    return template.format(answer=body, persona=persona_name)


def is_unanswerable(reply: str) -> bool:
    return reply.strip() == FALLBACK_MESSAGE
