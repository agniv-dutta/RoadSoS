from __future__ import annotations

import logging

import httpx

from ..config import get_settings

logger = logging.getLogger(__name__)


async def send_sms(to_number: str, message: str) -> bool:
    """Send an SMS through Twilio when credentials are configured."""

    settings = get_settings()
    if not settings.twilio_account_sid or not settings.twilio_auth_token or not settings.twilio_from_number:
        logger.warning("Twilio is not configured; skipping SMS delivery")
        return False

    url = f"https://api.twilio.com/2010-04-01/Accounts/{settings.twilio_account_sid}/Messages.json"
    payload = {"To": to_number, "From": settings.twilio_from_number, "Body": message}

    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            response = await client.post(
                url,
                data=payload,
                auth=(settings.twilio_account_sid, settings.twilio_auth_token),
            )
            response.raise_for_status()
            return True
    except httpx.HTTPError as exc:
        logger.exception("Twilio SMS delivery failed: %s", exc)
        return False
