import logging
import httpx

logger = logging.getLogger(__name__)


def notify_slack(webhook_url: str | None, text: str) -> bool:
    """Posts a message to a company's Slack Incoming Webhook. No OAuth or app
    install required — the company creates a free Incoming Webhook in their
    own Slack workspace and pastes the URL into Settings. No-ops (and logs
    instead) if the company hasn't configured one."""
    if not webhook_url:
        logger.info(f"[no Slack webhook configured] would post: {text}")
        return False
    try:
        response = httpx.post(webhook_url, json={"text": text}, timeout=5.0)
        response.raise_for_status()
        return True
    except Exception as e:
        logger.warning(f"Failed to post Slack notification: {e}")
        return False
