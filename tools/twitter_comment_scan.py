#!/usr/bin/env python3
"""
Twitter Comment Agent — heartbeat scan
Checks for reply opportunities on our threads and in relevant discussions.
"""
import os
import sys
import json
from pathlib import Path

# Load .env
env_file = Path(__file__).parent.parent / ".env"
if env_file.exists():
    with open(env_file) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, val = line.split("=", 1)
                os.environ[key] = val

try:
    import tweepy
except ImportError:
    print("ERROR: tweepy not installed. Run: pip install tweepy", file=sys.stderr)
    sys.exit(1)

BEARER_TOKEN = os.getenv("X_BEARER_TOKEN")
CONSUMER_KEY = os.getenv("X_CONSUMER_KEY")
CONSUMER_SECRET = os.getenv("X_CONSUMER_SECRET")
ACCESS_TOKEN = os.getenv("X_ACCESS_TOKEN")
ACCESS_TOKEN_SECRET = os.getenv("X_ACCESS_TOKEN_SECRET")

if not all([BEARER_TOKEN, CONSUMER_KEY, CONSUMER_SECRET, ACCESS_TOKEN, ACCESS_TOKEN_SECRET]):
    print("ERROR: Missing Twitter credentials", file=sys.stderr)
    sys.exit(1)

client = tweepy.Client(
    bearer_token=BEARER_TOKEN,
    consumer_key=CONSUMER_KEY,
    consumer_secret=CONSUMER_SECRET,
    access_token=ACCESS_TOKEN,
    access_token_secret=ACCESS_TOKEN_SECRET,
    wait_on_rate_limit=True,
)

# Load published signals to get recent tweet IDs
pub_file = Path(__file__).parent.parent / "data" / "published_signals.json"
with open(pub_file) as f:
    published = json.load(f)

# Get the 5 most recent signals with tweet IDs (for checking replies on our own threads)
recent_with_tweets = []
for sig in reversed(published):
    tweet_ids = sig.get("x_tweet_ids")
    if isinstance(tweet_ids, list) and tweet_ids:
        root_id = tweet_ids[0]
        recent_with_tweets.append({
            "signal_id": sig.get("signal_id", sig.get("thread_id", "?")),
            "question": sig.get("question", sig.get("title", "?")),
            "root_tweet_id": root_id,
        })
    elif isinstance(tweet_ids, dict) and tweet_ids:
        root_id = tweet_ids.get("tweet_1")
        if root_id:
            recent_with_tweets.append({
                "signal_id": sig.get("signal_id", sig.get("thread_id", "?")),
                "question": sig.get("question", sig.get("title", "?")),
                "root_tweet_id": root_id,
            })
    if len(recent_with_tweets) >= 5:
        break

print(f"\n=== OWN THREAD SCANS ({len(recent_with_tweets)} threads) ===\n")

own_thread_replies = []
for thread in recent_with_tweets:
    print(f"Checking: {thread['signal_id']} — {thread['question'][:60]}")
    print(f"  Root tweet: {thread['root_tweet_id']}")
    try:
        # Search for replies in the conversation
        results = client.search_recent_tweets(
            query=f"conversation_id:{thread['root_tweet_id']} -from:ProbBrain",
            tweet_fields=["author_id", "conversation_id", "created_at", "in_reply_to_user_id", "text"],
            expansions=["author_id"],
            user_fields=["username", "name"],
            max_results=10,
        )
        if results.data:
            users = {u.id: u for u in (results.includes.get("users") or [])}
            for tweet in results.data:
                author = users.get(tweet.author_id)
                username = author.username if author else "unknown"
                print(f"  REPLY from @{username}: {tweet.text[:100]}")
                own_thread_replies.append({
                    "thread_signal_id": thread["signal_id"],
                    "tweet_id": tweet.id,
                    "author": username,
                    "text": tweet.text,
                    "conversation_id": thread["root_tweet_id"],
                })
        else:
            print(f"  No replies found.")
    except tweepy.errors.TweepyException as e:
        print(f"  Error: {e}")

print(f"\n=== OUTSIDE OPPORTUNITY SCAN ===\n")

outside_opportunities = []
search_queries = [
    "Polymarket mispricing -from:ProbBrain lang:en",
    "Polymarket prediction market inefficiency -from:ProbBrain lang:en",
    "Polymarket odds wrong -from:ProbBrain lang:en",
]

for query in search_queries:
    print(f"Query: {query}")
    try:
        results = client.search_recent_tweets(
            query=query,
            tweet_fields=["author_id", "conversation_id", "created_at", "public_metrics", "text"],
            expansions=["author_id"],
            user_fields=["username", "name", "public_metrics"],
            max_results=10,
        )
        if results.data:
            users = {u.id: u for u in (results.includes.get("users") or [])}
            for tweet in results.data:
                author = users.get(tweet.author_id)
                username = author.username if author else "unknown"
                followers = author.public_metrics.get("followers_count", 0) if author and hasattr(author, "public_metrics") and author.public_metrics else 0
                likes = tweet.public_metrics.get("like_count", 0) if tweet.public_metrics else 0
                retweets = tweet.public_metrics.get("retweet_count", 0) if tweet.public_metrics else 0
                print(f"  @{username} ({followers} followers): {tweet.text[:100]}")
                print(f"    Likes: {likes} | RTs: {retweets} | ID: {tweet.id}")
                outside_opportunities.append({
                    "tweet_id": tweet.id,
                    "author": username,
                    "followers": followers,
                    "text": tweet.text,
                    "likes": likes,
                    "retweets": retweets,
                    "conversation_id": tweet.conversation_id,
                })
        else:
            print("  No results.")
    except tweepy.errors.TweepyException as e:
        print(f"  Error: {e}")
    print()

print("\n=== SUMMARY ===")
print(f"Own thread replies found: {len(own_thread_replies)}")
print(f"Outside opportunities found: {len(outside_opportunities)}")

# Save results for agent review
results_out = {
    "scanned_at": "2026-03-29",
    "own_thread_replies": own_thread_replies,
    "outside_opportunities": outside_opportunities,
}
out_file = Path(__file__).parent.parent / "data" / "comment_scan_2026-03-29.json"
with open(out_file, "w") as f:
    json.dump(results_out, f, indent=2)
print(f"\nResults saved to: {out_file}")
