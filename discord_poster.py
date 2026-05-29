"""Post line movement events to a Discord channel via webhook."""
import logging
from typing import Optional

import requests

log = logging.getLogger(__name__)

# Color = green if probability went up (more YES), red if it went down.
COLOR_UP = 0x2ECC71
COLOR_DOWN = 0xE74C3C
COLOR_NEUTRAL = 0x95A5A6


def cents_to_american(price_cents: int) -> str:
    """Convert a Kalshi cent price (1-99) to American odds."""
    if price_cents <= 0 or price_cents >= 100:
        return "N/A"
    p = price_cents / 100.0
    if p >= 0.5:
        return f"-{round((p / (1 - p)) * 100)}"
    return f"+{round(((1 - p) / p) * 100)}"


def _delta_str(prev: int, curr: int) -> str:
    delta = curr - prev
    sign = "+" if delta > 0 else ""
    return f"{sign}{delta}"


def _format_volume(v) -> str:
    if v is None:
        return "N/A"
    try:
        return f"{int(v):,}"
    except (TypeError, ValueError):
        return "N/A"


def post_line_movement(
    webhook_url: str,
    market: dict,
    prev: dict,
    curr: dict,
    series_label: Optional[str] = None,
) -> None:
    """Post a formatted Discord embed for a line movement on a market."""
    title = market.get("title") or market.get("ticker", "Unknown market")
    sub = market.get("yes_sub_title") or market.get("subtitle") or ""

    delta = curr["yes_ask"] - prev["yes_ask"]
    color = COLOR_UP if delta > 0 else (COLOR_DOWN if delta < 0 else COLOR_NEUTRAL)
    arrow = "📈" if delta > 0 else ("📉" if delta < 0 else "↔️")

    fields = [
        {
            "name": "YES price",
            "value": (
                f"`{prev['yes_ask']}¢ → {curr['yes_ask']}¢` "
                f"({_delta_str(prev['yes_ask'], curr['yes_ask'])}¢)"
            ),
            "inline": True,
        },
        {
            "name": "NO price",
            "value": (
                f"`{prev['no_ask']}¢ → {curr['no_ask']}¢` "
                f"({_delta_str(prev['no_ask'], curr['no_ask'])}¢)"
            ),
            "inline": True,
        },
        {
            "name": "American odds (YES)",
            "value": (
                f"{cents_to_american(prev['yes_ask'])} → "
                f"{cents_to_american(curr['yes_ask'])}"
            ),
            "inline": False,
        },
        {
            "name": "24h volume",
            "value": _format_volume(market.get("volume_24h") or market.get("volume")),
            "inline": True,
        },
        {
            "name": "Open interest",
            "value": _format_volume(market.get("open_interest")),
            "inline": True,
        },
    ]

    embed = {
        "title": f"{arrow} {title}",
        "description": sub or None,
        "color": color,
        "fields": fields,
        "footer": {
            "text": f"Kalshi · {market.get('ticker', '')}"
                    + (f" · {series_label}" if series_label else "")
        },
    }
    # Strip None values Discord won't accept
    embed = {k: v for k, v in embed.items() if v is not None}

    resp = requests.post(webhook_url, json={"embeds": [embed]}, timeout=10)
    if resp.status_code >= 300:
        log.error(f"Discord webhook failed: {resp.status_code} {resp.text}")
    resp.raise_for_status()
