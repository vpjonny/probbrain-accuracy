from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class Market:
    id: str
    slug: str
    question: str
    category: str
    yes_price: float          # 0.0–1.0
    no_price: float           # 0.0–1.0
    volume_usd: float
    liquidity_usd: float
    close_date: Optional[datetime]
    image_url: Optional[str]
    url: str
    fetched_at: datetime = field(default_factory=datetime.utcnow)

    @property
    def implied_probability(self) -> float:
        return round(self.yes_price * 100, 1)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "slug": self.slug,
            "question": self.question,
            "category": self.category,
            "yes_price": self.yes_price,
            "no_price": self.no_price,
            "implied_probability_pct": self.implied_probability,
            "volume_usd": self.volume_usd,
            "liquidity_usd": self.liquidity_usd,
            "close_date": self.close_date.isoformat() if self.close_date else None,
            "image_url": self.image_url,
            "url": self.url,
            "fetched_at": self.fetched_at.isoformat(),
        }
