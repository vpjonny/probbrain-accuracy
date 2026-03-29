#!/usr/bin/env python3
"""
Polymarket market card generator and Twitter upload helper.

This module provides utilities to:
1. Generate branded market card images from signal data
2. Upload to Twitter as media
3. Return media_id for tweet attachment
"""

import os
import sys
import tempfile
from pathlib import Path

# Import the market card generator
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from generate_market_card import generate_market_card

def upload_twitter_media_v2(image_path: str, twitter_client) -> str:
    """
    Upload image to Twitter and return media_id.

    Requires tweepy Client with v1.1 API access (which needs consumer/access tokens).

    Args:
        image_path: Path to image file
        twitter_client: tweepy.Client instance

    Returns:
        media_id string for use in tweet

    Raises:
        Exception: If upload fails
    """
    try:
        import tweepy

        # If twitter_client is a tweepy.Client, we need to create a v1.1 API object
        if isinstance(twitter_client, tweepy.Client):
            # Create API v1.1 object using the same credentials
            api = tweepy.API(
                auth=tweepy.OAuthHandler(
                    twitter_client.consumer_key,
                    twitter_client.consumer_secret
                )
            )
            api.auth.set_access_token(
                twitter_client.access_token,
                twitter_client.access_token_secret
            )
        else:
            api = twitter_client

        # Upload media
        media_response = api.media_upload(filename=image_path)
        return str(media_response.media_id)

    except Exception as e:
        raise Exception(f"Media upload failed: {e}")

def generate_market_image(
    market_question: str,
    market_price_yes: float,
    our_estimate: float,
    gap_pct: float,
    confidence: str,
    volume_usdc: float = None,
    output_path: str = None
) -> str:
    """
    Generate a market card image for the signal.

    Args:
        market_question: Market question
        market_price_yes: Market price (0-1 or 0-100)
        our_estimate: Our estimate (0-1 or 0-100)
        gap_pct: Gap in percentage points
        confidence: HIGH or MEDIUM
        volume_usdc: Volume in USDC (optional)
        output_path: Path to save. If None, uses temp file.

    Returns:
        Path to generated image
    """
    return generate_market_card(
        market_question=market_question,
        market_price_yes=market_price_yes,
        our_estimate=our_estimate,
        gap_pct=gap_pct,
        confidence=confidence,
        volume_usdc=volume_usdc,
        output_path=output_path
    )

def generate_and_upload_market_card(
    market_question: str,
    market_price_yes: float,
    our_estimate: float,
    gap_pct: float,
    confidence: str,
    twitter_client,
    volume_usdc: float = None
) -> str:
    """
    Generate market card and upload to Twitter.

    Args:
        market_question: Market question
        market_price_yes: Market price (0-1 or 0-100)
        our_estimate: Our estimate (0-1 or 0-100)
        gap_pct: Gap in percentage points
        confidence: HIGH or MEDIUM
        twitter_client: tweepy.Client instance
        volume_usdc: Volume in USDC (optional)

    Returns:
        media_id for tweet attachment, or None if upload fails

    Raises:
        Exception: If generation or upload fails
    """
    try:
        # Generate market card
        print(f"  Generating market card...")
        image_path = generate_market_image(
            market_question,
            market_price_yes,
            our_estimate,
            gap_pct,
            confidence,
            volume_usdc
        )
        print(f"  ✓ Market card generated: {image_path}")

        # Upload to Twitter
        print(f"  Uploading to Twitter...")
        media_id = upload_twitter_media_v2(image_path, twitter_client)
        print(f"  ✓ Media uploaded (ID: {media_id})")

        # Clean up temp file
        try:
            os.remove(image_path)
        except:
            pass

        return media_id
    except Exception as e:
        print(f"  ✗ Error: {e}")
        print(f"  Continuing without market card screenshot...")
        return None

if __name__ == "__main__":
    # Test: generate a market card
    if len(sys.argv) < 5:
        print("Usage: python3 polymarket_screenshot.py <question> <market%> <estimate%> <gap%> [confidence] [volume]")
        sys.exit(1)

    question = sys.argv[1]
    market = float(sys.argv[2])
    estimate = float(sys.argv[3])
    gap = float(sys.argv[4])
    confidence = sys.argv[5] if len(sys.argv) > 5 else "MEDIUM"
    volume = float(sys.argv[6]) if len(sys.argv) > 6 else None

    print(f"Generating market card...")
    try:
        path = generate_market_image(question, market, estimate, gap, confidence, volume)
        print(f"✓ Card saved to: {path}")
    except Exception as e:
        print(f"✗ Error: {e}")
        sys.exit(1)
