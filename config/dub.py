"""
Dub.co affiliate link management for ProbBrain.

Setup:
    1. Apply to Polymarket affiliate program at https://partners.dub.co/polymarket/apply
    2. Once approved, go to workspace settings → API Keys → create a key
    3. Set DUB_API_KEY and DUB_WORKSPACE_ID in .env
    4. Run provision_affiliate_links() once to create the three short-links
    5. Copy the returned short-link URLs into DUB_LINK_* env vars

Link templates (configure in Dub.co dashboard):
    - Telegram channel signals:  dub.sh/pb-tg
    - Telegram bot /signals cmd: dub.sh/pb-bot
    - X/Twitter posts:           dub.sh/pb-x

All links point to the Polymarket affiliate URL with ?ref=probbrain appended.
Polymarket referral program: $10 per first deposit, tracked via referral code.
"""
import logging
import os
from typing import Optional

import httpx

logger = logging.getLogger(__name__)

DUB_API_KEY = os.getenv("DUB_API_KEY", "")
DUB_WORKSPACE_ID = os.getenv("DUB_WORKSPACE_ID", "")
DUB_API_BASE = "https://api.dub.co"

POLYMARKET_REFERRAL_BASE = "https://polymarket.com"
REFERRAL_CODE = os.getenv("POLYMARKET_REFERRAL_CODE", "probbrain")

# Short-link keys configured in Dub.co — update these after account creation
LINK_KEYS = {
    "telegram_channel": os.getenv("DUB_LINK_TELEGRAM_CHANNEL", "pb-tg"),
    "telegram_bot":     os.getenv("DUB_LINK_TELEGRAM_BOT",     "pb-bot"),
    "twitter":          os.getenv("DUB_LINK_TWITTER",           "pb-x"),
}

# Resolved short URLs (set in .env after Dub account is configured)
DUB_DOMAIN = os.getenv("DUB_DOMAIN", "dub.sh")

LINKS = {
    channel: os.getenv(
        f"DUB_LINK_{channel.upper()}",
        f"https://{DUB_DOMAIN}/{key}"
    )
    for channel, key in LINK_KEYS.items()
}


def get_link(channel: str) -> str:
    """Return the short-link for the given channel, or the base referral URL."""
    return LINKS.get(channel, f"{POLYMARKET_REFERRAL_BASE}/?ref={REFERRAL_CODE}")


def create_link(slug: str, destination: str, comments: str = "") -> Optional[dict]:
    """
    Create a new short-link via the Dub.co API.
    Requires DUB_API_KEY and DUB_WORKSPACE_ID.
    """
    if not DUB_API_KEY:
        logger.error("DUB_API_KEY not set — cannot create link")
        return None

    headers = {
        "Authorization": f"Bearer {DUB_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "domain": DUB_DOMAIN,
        "key": slug,
        "url": destination,
        "workspaceId": DUB_WORKSPACE_ID,
        "comments": comments,
        "trackConversion": True,
    }

    try:
        with httpx.Client(timeout=15) as client:
            resp = client.post(f"{DUB_API_BASE}/links", headers=headers, json=payload)
            resp.raise_for_status()
            result = resp.json()
            logger.info("Created Dub link: %s → %s", result.get("shortLink"), destination)
            return result
    except httpx.HTTPError as exc:
        logger.error("Dub API error: %s", exc)
        return None


def provision_affiliate_links() -> dict:
    """
    Create all three ProbBrain affiliate short-links via the Dub API.
    Call once after account setup.
    """
    base_url = f"{POLYMARKET_REFERRAL_BASE}/?ref={REFERRAL_CODE}"
    results = {}

    specs = [
        ("pb-tg",  base_url, "Telegram channel signal posts"),
        ("pb-bot", base_url, "Telegram bot /signals command"),
        ("pb-x",   base_url, "X/Twitter posts"),
    ]

    for slug, dest, comment in specs:
        results[slug] = create_link(slug, dest, comment)

    return results


def get_click_stats(link_id: str) -> Optional[dict]:
    """Fetch click analytics for a link from Dub.co."""
    if not DUB_API_KEY:
        return None
    headers = {"Authorization": f"Bearer {DUB_API_KEY}"}
    try:
        with httpx.Client(timeout=15) as client:
            resp = client.get(f"{DUB_API_BASE}/links/{link_id}/stats", headers=headers)
            resp.raise_for_status()
            return resp.json()
    except httpx.HTTPError as exc:
        logger.error("Dub stats error: %s", exc)
        return None
