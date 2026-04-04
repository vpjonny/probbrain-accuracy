"""
Message formatting templates for ProbBrain Telegram bot.
All text uses Telegram MarkdownV2 escaping where needed.
"""
import os
from datetime import datetime
from typing import Optional

DISCLAIMER = (
    "_Not financial advice\\. Prediction markets carry risk\\. "
    "Trade only what you can afford to lose\\._"
)

_DASHBOARD_URL = os.getenv("DASHBOARD_URL", "https://vpjonny.github.io/probbrain-accuracy/")
_X_PROFILE_URL = os.getenv("X_PROFILE_URL", "https://x.com/ProbBrain")
_TELEGRAM_CHANNEL_URL = os.getenv("TELEGRAM_CHANNEL_URL", "https://t.me/ProbBrain")


def format_onboarding_day0(dashboard_url: str = _DASHBOARD_URL) -> str:
    """Day 0 welcome message — sent immediately when a new subscriber starts the bot."""
    return "\n".join([
        "Hey — welcome to *ProbBrain*\\.",
        "",
        "Here's what this is:",
        "",
        "We look at prediction markets \\(Polymarket and others\\), run our own "
        "evidence\\-based probability estimates, and flag the gaps\\. "
        "When a market prices something at 35% and we think it's closer to 19%, "
        "that's a signal\\.",
        "",
        "We're not a tipster service\\. We don't guarantee outcomes\\. "
        "We track every call publicly — wins and losses — so you can judge "
        "the track record yourself\\.",
        "",
        "*How signals work:*",
        "• We post our estimate, the market price, and the key evidence behind the gap",
        "• The market resolves, we log the result honestly",
        f"• Accuracy record: [Dashboard]({dashboard_url})",
        "",
        "Expect a message every few days when we find a genuine edge\\. "
        "If we don't see one, we don't send anything\\.",
        "",
        "That's it\\. No hype, just the numbers\\.",
        "",
        DISCLAIMER,
        "",
        f"[Follow us on X]({_X_PROFILE_URL}) \\| [Telegram channel]({_TELEGRAM_CHANNEL_URL})",
        "",
        "Unsubscribe any time: /stop",
    ])

def format_onboarding_day3(dashboard_url: str = _DASHBOARD_URL) -> str:
    """Day 3 education message — how to read a signal and what the gap means."""
    return "\n".join([
        "Quick note on how to read what we send you\\.",
        "",
        "Every signal has three numbers:",
        "",
        "*Market price* — what the crowd is collectively betting",
        "*Our estimate* — what we think based on base rates and current evidence",
        "*The gap* — the difference between them",
        "",
        "Example:",
        "Market says 35% chance of X\\. We think 19%\\. Gap: \\-16 points\\.",
        "That means the market is overpricing the event relative to our read of the evidence\\.",
        "",
        "We don't always get it right\\. Some calls resolve against us\\. "
        "That's expected — probability estimates aren't predictions, "
        "they're calibrated bets\\.",
        "",
        "What actually matters is whether our estimates are *better calibrated* "
        "than the market over many calls\\. That's what the accuracy dashboard tracks:",
        f"[Track record]({dashboard_url})",
        "",
        "When a signal resolves, we post the result honestly — win or loss\\.",
        "",
        "That's the whole system\\. More signals coming as we find genuine edges\\.",
        "",
        DISCLAIMER,
        "",
        f"[Follow us on X]({_X_PROFILE_URL}) \\| [Telegram channel]({_TELEGRAM_CHANNEL_URL})",
        "",
        "Unsubscribe any time: /stop",
    ])


DUB_LINK_PLACEHOLDER = "{dub_link}"


def _escape(text: str) -> str:
    """Escape special MarkdownV2 characters."""
    special = r"\_*[]()~`>#+-=|{}.!"
    return "".join(f"\\{c}" if c in special else c for c in text)


def format_ns_signal(
    question: str,
    market_yes_pct: float,
    our_estimate_pct: float,
    gap_pct: float,
    direction: str,
    confidence: str,
    evidence: list[str],
    counter_evidence: str,
    close_date: str,
    volume_usdc: float,
) -> str:
    """
    Format a signal using the REQUIRED NS Telegram template.
    ALL agents (CEO, NS, any publisher) MUST use this function.
    Returns plain text (no MarkdownV2) for Telegram.

    Args:
        question: Market question (≤80 chars)
        market_yes_pct: Market YES price as percentage (e.g. 69.5)
        our_estimate_pct: Our calibrated estimate as percentage (e.g. 55.0)
        gap_pct: Absolute gap in percentage points (e.g. 14.5)
        direction: "YES_UNDERPRICED" or "NO_UNDERPRICED"
        confidence: "HIGH" or "MEDIUM"
        evidence: List of evidence strings with sources and dates
        counter_evidence: One sentence acknowledging the other side
        close_date: Close date string (YYYY-MM-DD)
        volume_usdc: Volume in USDC
    """
    # Badge
    overpriced = "YES" if direction == "NO_UNDERPRICED" else "NO"
    bet_direction = "NO" if direction == "NO_UNDERPRICED" else "YES"

    if confidence == "HIGH":
        badge = f"\U0001f534 HIGH \u2014 Bet {bet_direction}"
    else:
        badge = f"\U0001f7e1 MEDIUM \u2014 Lean {bet_direction}"

    # Volume formatting
    if volume_usdc >= 1_000_000:
        vol_str = f"${volume_usdc / 1_000_000:.1f}M"
    else:
        vol_str = f"${volume_usdc / 1_000:.0f}k"

    # Evidence bullets
    evidence_lines = "\n".join(f"\u2022 {e}" for e in evidence)

    lines = [
        f"{badge} MARKET SIGNAL",
        "",
        f"\U0001f4ca {question}",
        "",
        f"Market: {market_yes_pct:.1f}% YES | Our estimate: {our_estimate_pct:.1f}% YES",
        f"Gap: {gap_pct:.1f}% (market overpricing {overpriced})",
        f"Volume: {vol_str}",
        f"Closes: {close_date}",
        "",
        f"Evidence:",
        evidence_lines,
        "",
        f"Counter-evidence: {counter_evidence}",
        "",
        "\U0001f517 Trade on Polymarket: https://dub.sh/pb-tg",
        "",
        "\u26a0\ufe0f Not financial advice. Trade at your own risk.",
        "\U0001f4c8 Accuracy track record: https://vpjonny.github.io/probbrain-accuracy/",
        "\U0001f426 Follow us on X: https://x.com/ProbBrain",
    ]
    return "\n".join(lines)


def format_signal(
    question: str,
    yes_pct: float,
    volume_usd: float,
    close_date: Optional[datetime],
    category: str,
    market_url: str,
    dub_link: str,
    is_pro: bool = False,
) -> str:
    """
    Format a prediction signal for Telegram.

    Free tier: shows question, probability, disclaimer, affiliate link.
    Pro tier: adds volume, close date, category, and direct market link.
    """
    close_str = close_date.strftime("%b %d, %Y") if close_date else "TBD"
    vol_str = f"${volume_usd:,.0f}"

    lines = [
        f"*{_escape(question)}*",
        "",
        f"Probability: *{_escape(f'{yes_pct:.1f}%')}*",
    ]

    if is_pro:
        lines += [
            f"Volume: {_escape(vol_str)}",
            f"Closes: {_escape(close_str)}",
            f"Category: {_escape(category.title())}",
            "",
            f"[View on Polymarket]({market_url})",
        ]

    lines += [
        "",
        f"[Trade on Polymarket]({dub_link})",
        "",
        DISCLAIMER,
        "",
        f"[Follow us on X]({_X_PROFILE_URL}) \\| [Get DM signals]({_TELEGRAM_CHANNEL_URL})",
    ]

    return "\n".join(lines)


def format_signal_list(signals: list[dict], dub_link: str, is_pro: bool = False) -> str:
    """Format a list of top signals for a /signals command response."""
    if not signals:
        return "No active signals right now. Check back later\\!"

    header = "*Top Prediction Signals* 🎯" if is_pro else "*Top Signals* \\(Free\\)"
    parts = [header, ""]

    for i, sig in enumerate(signals[:5 if not is_pro else 10], 1):
        yes_pct = sig.get("implied_probability_pct", 50.0)
        question = sig.get("question", "Unknown market")
        parts.append(f"{i}\\. {_escape(question)} — *{yes_pct:.1f}%*")

    parts += [
        "",
        f"[Trade on Polymarket]({dub_link})",
        "",
        DISCLAIMER,
        "",
        f"[Follow us on X]({_X_PROFILE_URL}) \\| [Get DM signals]({_TELEGRAM_CHANNEL_URL})",
    ]
    return "\n".join(parts)


START_MESSAGE = (
    "Welcome to *ProbBrain* — AI\\-powered prediction market signals\\!\n\n"
    "I scan Polymarket and surface the most active markets with probability insights\\.\n\n"
    "Commands:\n"
    "/signals — top prediction signals right now\n"
    "/help — show this message\n\n"
    "_Free tier: top 5 signals\\. Upgrade to Pro for full access\\._\n\n"
    f"[Follow us on X]({_X_PROFILE_URL}) \\| [Join our Telegram channel]({_TELEGRAM_CHANNEL_URL})"
)

HELP_MESSAGE = (
    "*ProbBrain Commands*\n\n"
    "/signals — get current top prediction signals\n"
    "/help — show this message\n\n"
    "_Signals update every 2 hours\\._\n\n"
    + DISCLAIMER
    + f"\n\n[Follow us on X]({_X_PROFILE_URL}) \\| [Join our Telegram channel]({_TELEGRAM_CHANNEL_URL})"
)
