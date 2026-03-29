#!/usr/bin/env python3
import os, json
from pathlib import Path

env_file = Path('/home/slova/ProbBrain/.env')
if env_file.exists():
    with open(env_file) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, val = line.split('=', 1)
                os.environ[key] = val

import tweepy
client = tweepy.Client(bearer_token=os.getenv('X_BEARER_TOKEN'))

ids = ['2037968968112115896', '2037974788887785874', '2037247830855917570']
for tid in ids:
    r = client.get_tweet(tid, tweet_fields=['text', 'author_id', 'public_metrics'], expansions=['author_id'], user_fields=['username', 'public_metrics'])
    if r.data:
        users = {u.id: u for u in (r.includes.get('users') or [])}
        author = users.get(r.data.author_id)
        uname = author.username if author else '?'
        print(f'ID: {tid}')
        print(f'Author: @{uname}')
        print(f'Text: {r.data.text}')
        print()
