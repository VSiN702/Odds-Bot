"""Discover live sports series and events on Kalshi.

Run this once to find out which series tickers to put in SERIES_TO_TRACK.
Kalshi naming changes over time, so don't hardcode this list — discover it.

Usage:
    python discover_series.py
"""
import os
import sys
from dotenv import load_dotenv

from kalshi_client import KalshiClient

load_dotenv()

KEY_ID = os.environ.get("KALSHI_KEY_ID")
PRIVATE_KEY_PATH = os.environ.get("KALSHI_PRIVATE_KEY_PATH")
USE_DEMO = os.environ.get("KALSHI_DEMO", "false").lower() == "true"

if not KEY_ID or not PRIVATE_KEY_PATH:
    print("Set KALSHI_KEY_ID and KALSHI_PRIVATE_KEY_PATH in .env first.")
    sys.exit(1)


def main():
    client = KalshiClient(KEY_ID, PRIVATE_KEY_PATH, demo=USE_DEMO)

    print(f"\n=== ALL SERIES (env={'DEMO' if USE_DEMO else 'PROD'}) ===\n")
    try:
        all_series = client.list_series()
    except Exception as e:
        print(f"Failed to list series: {e}")
        sys.exit(1)

    # Filter to sports-y series. Kalshi series have a 'category' field;
    # sports series are typically tagged "Sports". Also look at the ticker
    # prefix (KXNFL, KXNBA, KXMLB, KXNHL, KXTENNIS, KXGOLF, etc.).
    sports_series = [
        s for s in all_series
        if (s.get("category") or "").lower() == "sports"
        or any(
            (s.get("ticker") or "").upper().startswith(p)
            for p in ("KXNFL", "KXNBA", "KXMLB", "KXNHL",
                      "KXTEN", "KXGOLF", "KXSOC", "KXMMA", "KXCFB", "KXCBB")
        )
    ]

    print(f"Found {len(sports_series)} sports series:\n")
    for s in sorted(sports_series, key=lambda x: x.get("ticker", "")):
        ticker = s.get("ticker", "?")
        title = s.get("title", "")
        category = s.get("category", "")
        print(f"  {ticker:<20s} [{category}] {title}")

    # Optional: peek at open events for each, so you can see what's live
    print("\n=== OPEN EVENTS PER SERIES ===\n")
    for s in sports_series[:20]:  # cap the noise
        ticker = s.get("ticker")
        if not ticker:
            continue
        try:
            events = client.list_events(series_ticker=ticker)
        except Exception as e:
            print(f"  {ticker}: error - {e}")
            continue
        print(f"  {ticker}: {len(events)} open events")
        for e in events[:3]:
            print(f"      - {e.get('event_ticker')}: {e.get('title')}")


if __name__ == "__main__":
    main()
