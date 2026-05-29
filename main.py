"""Kalshi → Discord line-movement bot for VSiN.

Polls Kalshi markets at a regular interval, diffs prices against the last
snapshot, and posts a Discord embed when a market moves more than the
configured threshold.

Configure via environment variables — see .env.example.
"""
import logging
import os
import sys
import time

from dotenv import load_dotenv

from kalshi_client import KalshiClient
from discord_poster import post_line_movement

load_dotenv()

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
log = logging.getLogger("kalshi-bot")


def env(key: str, default: str = None, required: bool = False) -> str:
    val = os.getenv(key, default)
    if required and not val:
        log.error(f"Missing required env var: {key}")
        sys.exit(1)
    return val


# ---- config ----------------------------------------------------------------
KEY_ID = env("KALSHI_KEY_ID", required=True)
PRIVATE_KEY_PATH = env("KALSHI_PRIVATE_KEY_PATH", required=True)
USE_DEMO = env("KALSHI_DEMO", "false").lower() == "true"
DISCORD_WEBHOOK = env("DISCORD_WEBHOOK_URL", required=True)

POLL_INTERVAL_SEC = int(env("POLL_INTERVAL_SEC", "60"))
PRICE_MOVE_THRESHOLD = int(env("PRICE_MOVE_THRESHOLD_CENTS", "3"))
MIN_VOLUME_24H = int(env("MIN_VOLUME_24H", "1000"))

# Comma-separated list of Kalshi series tickers to track.
# Use the bootstrap script (see README) to discover what's currently live.
SERIES_TO_TRACK = [
    s.strip() for s in env("SERIES_TO_TRACK", "").split(",") if s.strip()
]


# ---- main loop -------------------------------------------------------------
def snapshot_market(m: dict) -> dict:
    return {
        "yes_ask": int(m.get("yes_ask") or 0),
        "yes_bid": int(m.get("yes_bid") or 0),
        "no_ask": int(m.get("no_ask") or 0),
        "no_bid": int(m.get("no_bid") or 0),
        "ts": time.time(),
    }


def poll_once(client: KalshiClient, last: dict) -> dict:
    """Run one polling cycle. Returns the updated snapshot dict."""
    new_snapshot = {}

    for series in SERIES_TO_TRACK:
        try:
            markets = client.list_markets(series_ticker=series)
        except Exception as e:
            log.error(f"list_markets({series}) failed: {e}")
            continue

        log.debug(f"{series}: {len(markets)} open markets")

        for m in markets:
            ticker = m.get("ticker")
            if not ticker:
                continue

            # Filter low-liquidity markets to cut noise
            vol = int(m.get("volume_24h") or m.get("volume") or 0)
            if vol < MIN_VOLUME_24H:
                continue

            curr = snapshot_market(m)
            new_snapshot[ticker] = curr

            prev = last.get(ticker)
            if not prev:
                continue  # first time seeing this ticker, baseline only

            move = abs(curr["yes_ask"] - prev["yes_ask"])
            if move >= PRICE_MOVE_THRESHOLD:
                log.info(
                    f"MOVE: {ticker} {prev['yes_ask']}¢ → {curr['yes_ask']}¢ "
                    f"({move}¢) vol={vol:,}"
                )
                try:
                    post_line_movement(
                        DISCORD_WEBHOOK, m, prev, curr, series_label=series
                    )
                except Exception as e:
                    log.error(f"post_line_movement({ticker}) failed: {e}")

    return new_snapshot


def main():
    if not SERIES_TO_TRACK:
        log.error("SERIES_TO_TRACK is empty. Set it in .env to one or more "
                  "Kalshi series tickers (e.g., KXNFLGAME,KXNBAGAME).")
        sys.exit(1)

    client = KalshiClient(KEY_ID, PRIVATE_KEY_PATH, demo=USE_DEMO)
    log.info(
        f"Starting Kalshi line-movement bot "
        f"(env={'DEMO' if USE_DEMO else 'PROD'}, "
        f"poll={POLL_INTERVAL_SEC}s, "
        f"threshold={PRICE_MOVE_THRESHOLD}¢, "
        f"min_vol={MIN_VOLUME_24H:,})"
    )
    log.info(f"Tracking series: {SERIES_TO_TRACK}")

    snapshot = {}
    while True:
        try:
            snapshot = poll_once(client, snapshot)
        except Exception:
            log.exception("Unexpected error in poll cycle")
        time.sleep(POLL_INTERVAL_SEC)


if __name__ == "__main__":
    main()
