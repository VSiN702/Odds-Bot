# Odds-Bot
This bot is to pull in odds from Kalshi and spot odds to distribute into a discord channel.
# Kalshi → VSiN Discord Line-Movement Bot

Polls Kalshi prediction-market prices and posts to a Discord channel when a
market's YES price moves more than a configurable threshold.

## Quick start

1. **Install deps**
   ```bash
   python -m venv .venv && source .venv/bin/activate
   pip install -r requirements.txt
   ```

2. **Drop your Kalshi private key** into the project as `kalshi_private_key.pem`
   (or wherever — set the path in `.env`). This is the `.key`/`.pem` file you
   downloaded when you created the API key. If you only have the Key ID and
   no private key file, you need to regenerate the key pair in Kalshi.

3. **Create the Discord webhook**
   - In your server, go to `#line-movement` → Edit Channel → Integrations →
     Webhooks → New Webhook → Copy Webhook URL
   - Name it something obvious like "Kalshi Line Mover"

4. **Configure environment**
   ```bash
   cp .env.example .env
   # Fill in KALSHI_KEY_ID, KALSHI_PRIVATE_KEY_PATH, DISCORD_WEBHOOK_URL
   # Start with KALSHI_DEMO=true while you're testing
   ```

5. **Discover what to track**
   ```bash
   python discover_series.py
   ```
   This lists every sports series currently on Kalshi. Pick the ones VSiN
   cares about (NFL games, NBA games, MLB, golf majors, tennis slams, etc.)
   and put them in `SERIES_TO_TRACK` in `.env` as a comma-separated list.

6. **Run**
   ```bash
   python main.py
   ```

## What gets posted

When a tracked market's YES price moves by `PRICE_MOVE_THRESHOLD_CENTS` or more
between poll cycles, the bot drops an embed in `#line-movement` showing:

- The market title (e.g. "Will the Chiefs beat the Bills?")
- YES price: `54¢ → 61¢ (+7¢)`
- NO price: `46¢ → 39¢ (-7¢)`
- American odds translation: `-117 → -156`
- 24h volume + open interest
- Color: green if YES moved up, red if down

## Tuning

| Variable | What it does | Sane default |
|----------|--------------|--------------|
| `POLL_INTERVAL_SEC` | How often to pull prices | 60 |
| `PRICE_MOVE_THRESHOLD_CENTS` | Min movement to fire a post | 3 |
| `MIN_VOLUME_24H` | Skip markets below this volume | 1000 |

If the channel gets too noisy, raise the threshold to 5¢ or the volume floor
to 5,000. If it's too quiet, lower them.

## Demo vs production

Kalshi runs a full demo environment at `demo-api.kalshi.co`. Set
`KALSHI_DEMO=true` to use it. You need separate API keys for demo (generate
them at `demo.kalshi.co`). Demo data is real market data but lower volume —
fine for verifying the bot works end-to-end without hitting prod rate limits.

## Deployment

This is a single long-running Python process. Options:

- **systemd service** on a small VPS (cheapest, simplest)
- **Docker container** alongside your other VSiN bots
- **AWS Lambda + EventBridge** — would require rewriting the loop into a
  one-shot invocation reading state from DynamoDB or S3

Pick whatever matches your Xpression bot deployment so you have one place
to manage VSiN's Discord automation.

## Next steps to consider

- **WebSocket** instead of polling for sub-second movement detection
  (`wss://api.elections.kalshi.com/trade-api/ws/v2`)
- **Per-sport channel routing** — post NFL movements to `#nfl-news`, NBA
  movements to `#nba-news`, etc., based on the series ticker
- **"Steam move" detection** — a separate alert for big moves under 1 minute
  with high volume, posted to a dedicated `#steam-moves` channel
- **Persistent state** — store snapshots in SQLite so restarts don't lose
  baselines
- **Health webhook** — ping a different channel if the bot dies or hits
  Kalshi auth errors
