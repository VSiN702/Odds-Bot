"""Kalshi v2 API client with RSA-PSS signed requests."""
import base64
import time
import logging
from typing import Optional

import requests
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding

log = logging.getLogger(__name__)


class KalshiClient:
    """Minimal client for Kalshi REST API v2.

    Auth: every request signs (timestamp_ms + method + path) with the
    private key using RSA-PSS / SHA256 and sends:
        KALSHI-ACCESS-KEY:        <key_id>
        KALSHI-ACCESS-TIMESTAMP:  <unix_ms>
        KALSHI-ACCESS-SIGNATURE:  <base64 signature>

    The signed `path` must include the /trade-api/v2 prefix and must NOT
    include the query string.
    """

    PROD_HOST = "https://api.elections.kalshi.com"
    DEMO_HOST = "https://demo-api.kalshi.co"
    API_PREFIX = "/trade-api/v2"

    def __init__(self, key_id: str, private_key_path: str, demo: bool = False):
        self.key_id = key_id
        self.host = self.DEMO_HOST if demo else self.PROD_HOST
        with open(private_key_path, "rb") as f:
            self.private_key = serialization.load_pem_private_key(
                f.read(), password=None
            )
        self.session = requests.Session()

    # ---- auth helpers ---------------------------------------------------

    def _sign(self, method: str, path: str, timestamp_ms: str) -> str:
        message = (timestamp_ms + method + path).encode("utf-8")
        signature = self.private_key.sign(
            message,
            padding.PSS(
                mgf=padding.MGF1(hashes.SHA256()),
                salt_length=padding.PSS.DIGEST_LENGTH,
            ),
            hashes.SHA256(),
        )
        return base64.b64encode(signature).decode("utf-8")

    def _headers(self, method: str, path: str) -> dict:
        ts = str(int(time.time() * 1000))
        return {
            "KALSHI-ACCESS-KEY": self.key_id,
            "KALSHI-ACCESS-TIMESTAMP": ts,
            "KALSHI-ACCESS-SIGNATURE": self._sign(method, path, ts),
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    # ---- request --------------------------------------------------------

    def _get(self, endpoint: str, params: Optional[dict] = None) -> dict:
        path = f"{self.API_PREFIX}{endpoint}"
        url = f"{self.host}{path}"
        # Sign the path WITHOUT query string; pass params separately to requests
        headers = self._headers("GET", path)
        resp = self.session.get(url, headers=headers, params=params, timeout=15)
        if resp.status_code == 429:
            log.warning("Rate limited; sleeping 5s")
            time.sleep(5)
            resp = self.session.get(url, headers=headers, params=params, timeout=15)
        resp.raise_for_status()
        return resp.json()

    # ---- public-ish endpoints we actually use ---------------------------

    def list_series(self, category: Optional[str] = None) -> list:
        """List series. Useful to discover sport tickers (e.g., KXNFLGAME)."""
        params = {}
        if category:
            params["category"] = category
        return self._get("/series", params=params).get("series", [])

    def list_events(self, series_ticker: str, status: str = "open") -> list:
        """List events under a series."""
        params = {"series_ticker": series_ticker, "status": status, "limit": 200}
        return self._get("/events", params=params).get("events", [])

    def list_markets(
        self,
        series_ticker: Optional[str] = None,
        event_ticker: Optional[str] = None,
        status: str = "open",
    ) -> list:
        """List markets, paginated. Filter by series or event."""
        params = {"status": status, "limit": 200}
        if series_ticker:
            params["series_ticker"] = series_ticker
        if event_ticker:
            params["event_ticker"] = event_ticker

        markets = []
        cursor = None
        while True:
            if cursor:
                params["cursor"] = cursor
            data = self._get("/markets", params=params)
            markets.extend(data.get("markets", []))
            cursor = data.get("cursor")
            if not cursor:
                break
        return markets

    def get_market(self, ticker: str) -> dict:
        return self._get(f"/markets/{ticker}").get("market", {})
