"""
Subscriber tracking for the ProbBrain drip system.

Manages data/subscribers.json (drip state) and data/messages_log.json (audit log).
"""
import json
import logging
import os
from datetime import datetime, timezone
from typing import Optional

logger = logging.getLogger(__name__)

_DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")
_SUBSCRIBERS_PATH = os.path.join(_DATA_DIR, "subscribers.json")
_MESSAGES_LOG_PATH = os.path.join(_DATA_DIR, "messages_log.json")


def _load_json(path: str) -> list:
    try:
        with open(path) as f:
            data = json.load(f)
            return data if isinstance(data, list) else []
    except (FileNotFoundError, json.JSONDecodeError):
        return []


def _save_json(path: str, data: list) -> None:
    with open(path, "w") as f:
        json.dump(data, f, indent=2)


def get_subscriber(chat_id: int) -> Optional[dict]:
    return next(
        (s for s in _load_json(_SUBSCRIBERS_PATH) if s["chat_id"] == chat_id),
        None,
    )


def register_subscriber(chat_id: int, username: Optional[str] = None) -> tuple[dict, bool]:
    """
    Register a new subscriber or reactivate an unsubscribed one.

    Returns (subscriber_dict, is_new) where is_new=True means Day 0 should be sent.
    """
    subscribers = _load_json(_SUBSCRIBERS_PATH)
    now = datetime.now(timezone.utc).isoformat()

    existing = next((s for s in subscribers if s["chat_id"] == chat_id), None)
    if existing:
        if not existing.get("active", True):
            # Reactivate — reset drip so they get the welcome again
            existing.update({
                "active": True,
                "unsubscribed_at": None,
                "subscribed_at": now,
                "drip_day": 0,
                "last_message_at": None,
            })
            _save_json(_SUBSCRIBERS_PATH, subscribers)
            return existing, True
        return existing, False

    subscriber = {
        "chat_id": chat_id,
        "username": username,
        "subscribed_at": now,
        "tier": "free",
        "drip_day": 0,
        "last_message_at": None,
        "messages_sent": 0,
        "resolved_signals_seen": 0,
        "active": True,
        "unsubscribed_at": None,
    }
    subscribers.append(subscriber)
    _save_json(_SUBSCRIBERS_PATH, subscribers)
    return subscriber, True


def unsubscribe(chat_id: int) -> bool:
    """Mark a subscriber inactive. Returns True if the subscriber was found."""
    subscribers = _load_json(_SUBSCRIBERS_PATH)
    for s in subscribers:
        if s["chat_id"] == chat_id:
            s["active"] = False
            s["unsubscribed_at"] = datetime.now(timezone.utc).isoformat()
            _save_json(_SUBSCRIBERS_PATH, subscribers)
            return True
    return False


def log_message(chat_id: int, message_type: str, preview: str = "") -> None:
    """Log a sent message and update subscriber's last_message_at + messages_sent."""
    now = datetime.now(timezone.utc).isoformat()

    subscribers = _load_json(_SUBSCRIBERS_PATH)
    for s in subscribers:
        if s["chat_id"] == chat_id:
            s["last_message_at"] = now
            s["messages_sent"] = s.get("messages_sent", 0) + 1
            break
    _save_json(_SUBSCRIBERS_PATH, subscribers)

    messages_log = _load_json(_MESSAGES_LOG_PATH)
    messages_log.append({
        "chat_id": chat_id,
        "message_type": message_type,
        "sent_at": now,
        "preview": preview[:120] if preview else "",
    })
    _save_json(_MESSAGES_LOG_PATH, messages_log)
