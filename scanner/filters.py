import json
from pathlib import Path
from typing import List, Set
from .models import Market


MIN_VOLUME_USD = 50_000  # $50k minimum volume


def apply_filters(markets: List[Market]) -> List[Market]:
    """
    Keep markets with ≥$50k volume OR top 20% in their category by volume.
    """
    # Pass 1: always keep high-volume markets
    high_volume = {m.id for m in markets if m.volume_usd >= MIN_VOLUME_USD}

    # Pass 2: top 20% per category
    by_category: dict[str, List[Market]] = {}
    for m in markets:
        by_category.setdefault(m.category, []).append(m)

    top20_ids: set[str] = set()
    for cat_markets in by_category.values():
        sorted_markets = sorted(cat_markets, key=lambda m: m.volume_usd, reverse=True)
        cutoff = max(1, int(len(sorted_markets) * 0.20))
        for m in sorted_markets[:cutoff]:
            top20_ids.add(m.id)

    keep = high_volume | top20_ids
    filtered = [m for m in markets if m.id in keep]

    # Sort by volume descending
    filtered.sort(key=lambda m: m.volume_usd, reverse=True)
    return filtered


def _normalize_question(question: str) -> str:
    """Normalize question text for dedup comparison (lowercase, strip punctuation)."""
    if not question:
        return ""
    # Remove leading/trailing whitespace, convert to lowercase
    normalized = question.strip().lower()
    # Remove trailing question marks and extra punctuation
    normalized = normalized.rstrip("?!")
    return normalized


def _load_published_questions() -> Set[str]:
    """Load set of already-published market questions for dedup."""
    published_file = Path(__file__).parent.parent / "data" / "published_signals.json"
    if not published_file.exists():
        return set()

    try:
        with open(published_file, "r") as f:
            data = json.load(f)

        # Extract normalized questions from published signals
        published_questions = set()
        if isinstance(data, list):
            for signal in data:
                if "question" in signal:
                    normalized = _normalize_question(signal["question"])
                    if normalized:
                        published_questions.add(normalized)

        return published_questions
    except (json.JSONDecodeError, IOError):
        return set()


def _extract_core_theme(question: str) -> str:
    """
    Extract core betting theme from a question.
    Removes conditional qualifiers like 'before GTA VI', specific dates, etc.
    Examples:
      'Russia-Ukraine ceasefire before GTA VI?' → 'russia ukraine ceasefire'
      'Trump out as President before 2027?' → 'trump out as president'
      'Will China invade Taiwan before GTA VI?' → 'china invade taiwan'
    """
    theme = question.lower()

    # Remove common meme/date conditionals (in order of specificity)
    qualifiers = [
        # GTA VI variants
        'before gta vi', 'before gta6', 'before gtavi', ' gta vi', ' gta6', ' gtavi',
        # Specific dates
        ' by end of 2026', ' by march 31', ' by april 15', ' by june 2026', ' by july 2026',
        ' by march 31 2026', ' by april 30 2026',
        # Years
        ' 2026', ' 2027', ' 2025',
        # Temporal qualifiers
        ' before ', ' by ', ' by?',
    ]

    for qualifier in qualifiers:
        theme = theme.replace(qualifier, ' ').strip()

    # Remove punctuation (but keep spaces)
    theme = ''.join(c if c.isalnum() or c.isspace() else ' ' for c in theme)

    # Normalize whitespace
    theme = ' '.join(theme.split())

    return theme


def _load_published_themes() -> set:
    """Load set of core themes from already-published signals."""
    published_file = Path(__file__).parent.parent / "data" / "published_signals.json"
    if not published_file.exists():
        return set()

    try:
        with open(published_file, "r") as f:
            data = json.load(f)

        themes = set()
        if isinstance(data, list):
            for signal in data:
                if "question" in signal:
                    theme = _extract_core_theme(signal["question"])
                    if theme:
                        themes.add(theme)

        return themes
    except (json.JSONDecodeError, IOError):
        return set()


def filter_duplicates(markets: List[Market]) -> List[Market]:
    """
    Remove markets that duplicate or near-duplicate already-published signals.

    Two-pass filtering:
    1. Exact question match (fast check)
    2. Semantic theme match (catches GTA VI variants, date variants, etc.)
    """
    published_questions = _load_published_questions()
    published_themes = _load_published_themes()

    if not published_questions and not published_themes:
        return markets

    filtered = []
    for m in markets:
        normalized_q = _normalize_question(m.question)
        theme = _extract_core_theme(m.question)

        # Reject if exact question match
        if normalized_q in published_questions:
            continue

        # Reject if semantic theme match (catches meme variants like "before GTA VI")
        if theme in published_themes:
            continue

        filtered.append(m)

    return filtered
