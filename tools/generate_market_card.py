#!/usr/bin/env python3
"""
Generate Polymarket market cards as images for Twitter posting.

Creates a clean, branded image card showing market probability, our estimate, and gap.
"""

from PIL import Image, ImageDraw, ImageFont
import os
import tempfile

def generate_market_card(
    market_question: str,
    market_price_yes: float,
    our_estimate: float,
    gap_pct: float,
    confidence: str,
    volume_usdc: float = None,
    output_path: str = None
) -> str:
    """
    Generate a market card image for Twitter.

    Args:
        market_question: Market question/title (e.g., "Will China invade Taiwan before GTA VI?")
        market_price_yes: Market price as percentage (0-100 or 0-1)
        our_estimate: Our estimate as percentage (0-100 or 0-1)
        gap_pct: Gap in percentage points
        confidence: "HIGH" or "MEDIUM"
        volume_usdc: Market volume (optional)
        output_path: Path to save image. If None, uses temp file.

    Returns:
        Path to generated image
    """
    # Normalize prices to 0-100 range if needed
    if market_price_yes <= 1:
        market_price_yes *= 100
    if our_estimate <= 1:
        our_estimate *= 100

    # Create image
    width, height = 1200, 675
    background_color = (15, 23, 42)  # Dark blue
    image = Image.new("RGB", (width, height), background_color)
    draw = ImageDraw.Draw(image)

    # Load fonts (fallback to default if not available)
    try:
        title_font = ImageFont.truetype("/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf", 32)
        header_font = ImageFont.truetype("/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf", 24)
        value_font = ImageFont.truetype("/usr/share/fonts/truetype/liberation/LiberationMono-Bold.ttf", 48)
        small_font = ImageFont.truetype("/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf", 20)
    except:
        # Fallback to default font
        title_font = ImageFont.load_default()
        header_font = ImageFont.load_default()
        value_font = ImageFont.load_default()
        small_font = ImageFont.load_default()

    # Colors
    white = (255, 255, 255)
    accent = (74, 222, 128)  # Bright green
    market_color = (96, 165, 250)  # Blue
    estimate_color = (251, 146, 60)  # Orange
    warning_color = (248, 113, 113)  # Red

    # Decide gap color
    gap_color = accent if abs(gap_pct) >= 10 else (107, 114, 128)  # Green if significant gap, gray otherwise

    # Title
    title_bbox = draw.textbbox((0, 0), market_question, font=title_font)
    title_height = title_bbox[3] - title_bbox[1]
    title_y = 40

    # Wrap title if needed
    if title_bbox[2] - title_bbox[0] > width - 80:
        # Simple wrapping
        words = market_question.split()
        lines = []
        current_line = []

        for word in words:
            test_line = " ".join(current_line + [word])
            bbox = draw.textbbox((0, 0), test_line, font=title_font)
            if bbox[2] - bbox[0] > width - 80:
                if current_line:
                    lines.append(" ".join(current_line))
                current_line = [word]
            else:
                current_line.append(word)
        if current_line:
            lines.append(" ".join(current_line))

        for i, line in enumerate(lines):
            draw.text((40, title_y + i * (title_height + 10)), line, fill=white, font=title_font)
        title_y += len(lines) * (title_height + 10)
    else:
        draw.text((40, title_y), market_question, fill=white, font=title_font)
        title_y += title_height + 30

    # Market section
    y_pos = title_y + 40
    draw.text((40, y_pos), "MARKET PRICE", fill=market_color, font=small_font)
    draw.text((40, y_pos + 35), f"{market_price_yes:.1f}%", fill=market_color, font=value_font)

    # Our estimate section
    draw.text((400, y_pos), "OUR ESTIMATE", fill=estimate_color, font=small_font)
    draw.text((400, y_pos + 35), f"{our_estimate:.1f}%", fill=estimate_color, font=value_font)

    # Gap section
    draw.text((760, y_pos), "GAP", fill=gap_color, font=small_font)
    draw.text((760, y_pos + 35), f"{gap_pct:.1f}pp", fill=gap_color, font=value_font)

    # Confidence and volume footer
    footer_y = height - 80
    confidence_emoji = "🔴" if confidence == "HIGH" else "🟡"
    footer_text = f"{confidence_emoji} {confidence} | Vol: ${volume_usdc/1e6:.1f}M" if volume_usdc else f"{confidence_emoji} {confidence}"
    draw.text((40, footer_y), footer_text, fill=white, font=header_font)

    # Branding
    draw.text((40, height - 40), "@ProbBrain", fill=(107, 114, 128), font=small_font)

    # Save image
    if output_path is None:
        temp_file = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
        output_path = temp_file.name
        temp_file.close()

    image.save(output_path, "PNG")
    return output_path

if __name__ == "__main__":
    import sys

    if len(sys.argv) < 4:
        print("Usage: python3 generate_market_card.py <question> <market%> <estimate%> <gap%> [confidence] [volume]")
        sys.exit(1)

    question = sys.argv[1]
    market = float(sys.argv[2])
    estimate = float(sys.argv[3])
    gap = float(sys.argv[4])
    confidence = sys.argv[5] if len(sys.argv) > 5 else "MEDIUM"
    volume = float(sys.argv[6]) if len(sys.argv) > 6 else None

    print(f"Generating market card...")
    path = generate_market_card(question, market, estimate, gap, confidence, volume)
    print(f"✓ Saved to: {path}")
