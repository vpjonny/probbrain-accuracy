import json
import httpx
from datetime import datetime, timezone

# Fetch high volume markets from Polymarket
resp = httpx.get('https://gamma-api.polymarket.com/markets?active=true&closed=false&limit=200', timeout=30)
markets = resp.json()

print(f"Fetched {len(markets)} active markets\n")

# Load existing signals to avoid duplicates
with open('data/signals.json') as f:
    signals = json.load(f)
existing_ids = {s.get('market_id') for s in signals}

# Look for mispriced markets
opportunities = []
for m in markets:
    mid = str(m.get('id', ''))
    if mid in existing_ids:
        continue
    
    vol = float(m.get('volume', 0) or 0)
    if vol < 500000:  # $500k min volume
        continue
    
    prices = m.get('outcomePrices', '[]')
    if isinstance(prices, str):
        prices = json.loads(prices)
    if not prices:
        continue
    
    yes_price = float(prices[0])
    
    # Look for extreme prices (potential mispricings)
    q = m.get('question', '')[:60]
    slug = m.get('slug', '')
    close = m.get('endDate', '')[:10] if m.get('endDate') else 'N/A'
    
    # Focus on geopolitics/politics (where we have edge)
    tags = m.get('tags', []) or []
    category = 'general'
    if any(t.get('label', '').lower() in ['geopolitics', 'politics', 'elections', 'world'] for t in tags if isinstance(t, dict)):
        category = 'geopolitics'
    elif any(t.get('label', '').lower() in ['crypto', 'bitcoin'] for t in tags if isinstance(t, dict)):
        category = 'crypto'
    
    # Only show markets with YES between 15-40% or 60-85% (potential edge zones)
    if (0.15 <= yes_price <= 0.40) or (0.60 <= yes_price <= 0.85):
        opportunities.append({
            'id': mid,
            'slug': slug,
            'q': q,
            'yes': yes_price,
            'vol': vol,
            'close': close,
            'cat': category
        })

# Sort by volume
opportunities.sort(key=lambda x: x['vol'], reverse=True)

print("TOP OPPORTUNITIES (not yet signaled):\n")
for opp in opportunities[:12]:
    print(f"YES: {opp['yes']:.0%} | ${opp['vol']/1e6:.1f}M | {opp['close']}")
    print(f"  {opp['q']}...")
    print(f"  slug: {opp['slug']}")
    print()
