import json
import httpx
from datetime import datetime, timezone

with open('data/signals.json') as f:
    signals = json.load(f)

# Check signals that haven't been marked resolved but might be closed
pending = [s for s in signals if not s.get('resolved', False) or s.get('status') in ['open', 'published']]
print(f'Checking {len(pending)} pending signals...\n')

for sig in pending[:20]:
    slug = sig.get('polymarket_slug', '')
    sig_id = sig.get('id', 'UNKNOWN')
    q = sig.get('question', sig.get('market_question', ''))[:55]
    
    try:
        resp = httpx.get(f'https://gamma-api.polymarket.com/markets?slug={slug}', timeout=10)
        if resp.status_code == 200:
            markets = resp.json()
            if markets:
                m = markets[0]
                closed = m.get('closed', False)
                resolved = m.get('resolved', False)
                prices = m.get('outcomePrices', '[]')
                if isinstance(prices, str):
                    prices = json.loads(prices)
                yes_price = float(prices[0]) if prices else 0.5
                
                status = 'OPEN'
                if resolved:
                    outcome = 'YES' if yes_price > 0.9 else 'NO' if yes_price < 0.1 else f'{yes_price:.0%}'
                    status = f'RESOLVED -> {outcome}'
                elif closed:
                    status = f'CLOSED (YES: {yes_price:.0%})'
                
                if closed or resolved:
                    print(f'{sig_id}: {status}')
                    print(f'  {q}...')
    except Exception as e:
        print(f'{sig_id}: ERROR - {e}')
