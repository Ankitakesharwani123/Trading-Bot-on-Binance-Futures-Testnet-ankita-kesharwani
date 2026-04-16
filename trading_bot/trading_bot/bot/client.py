"""
bot/client.py
Low-level Binance Futures Testnet REST client.

Responsibilities
----------------
- HMAC-SHA256 request signing
- Server-time sync (avoids timestamp drift errors)
- Raw GET / POST helpers with full DEBUG logging
- Converts Binance error payloads → BinanceClientError
- Wraps network failures → NetworkError
"""

from __future__ import annotations

import hashlib
import hmac
import time
from typing import Any
from urllib.parse import urlencode

import requests

from bot.logging_config import setup_logger

logger = setup_logger("trading_bot.client")

TESTNET_BASE = "https://testnet.binancefuture.com"
API_V1       = f"{TESTNET_BASE}/fapi/v1"
API_V2       = f"{TESTNET_BASE}/fapi/v2"
REQUEST_TIMEOUT = 10          # seconds


class BinanceClientError(Exception):
    """API returned a JSON error payload."""
    def __init__(self, code: int, message: str):
        self.code    = code
        self.message = message
        super().__init__(f"Binance API error {code}: {message}")


class NetworkError(IOError):
    """Network-level failure (timeout, DNS, connection refused, etc.)."""


class BinanceFuturesClient:
    """
    Thin, stateless wrapper around the Binance Futures Testnet REST API.
    Instantiate once, reuse freely — the underlying requests.Session is
    kept open for connection pooling.
    """

    def __init__(self, api_key: str, api_secret: str):
        if not api_key or not api_secret:
            raise ValueError("api_key and api_secret must not be empty.")

        self._api_key    = api_key
        self._api_secret = api_secret.encode("utf-8")
        self._session    = requests.Session()
        self._session.headers.update({"X-MBX-APIKEY": self._api_key})
        self._time_offset: int = 0

        self._sync_time()

    # ------------------------------------------------------------------ #
    #  Public helpers                                                      #
    # ------------------------------------------------------------------ #

    def get_exchange_info(self) -> dict:
        """Return futures exchange metadata (symbols, lot-size filters …)."""
        return self._get_public(f"{API_V1}/exchangeInfo")

    def get_ticker_price(self, symbol: str) -> dict:
        """Latest price ticker for *symbol*."""
        return self._get_public(f"{API_V1}/ticker/price", params={"symbol": symbol})

    def get_account_balance(self) -> list[dict]:
        """Signed request — returns futures account balance list."""
        return self._get_signed(f"{API_V2}/balance")

    def place_order(
        self,
        symbol:        str,
        side:          str,          # "BUY" | "SELL"
        order_type:    str,          # "MARKET" | "LIMIT" | "STOP_LIMIT"
        quantity:      float,
        price:         float | None = None,
        stop_price:    float | None = None,
        time_in_force: str          = "GTC",
        recv_window:   int          = 5000,
    ) -> dict:
        """
        Place a futures order and return the full Binance response dict.

        STOP_LIMIT is mapped to Binance's STOP order type (limit price +
        stop trigger price, with timeInForce).
        """
        params: dict[str, Any] = {
            "symbol":     symbol,
            "side":       side,
            "quantity":   f"{quantity:.8f}",
            "recvWindow": recv_window,
        }

        if order_type == "MARKET":
            params["type"] = "MARKET"

        elif order_type == "LIMIT":
            params["type"]        = "LIMIT"
            params["price"]       = f"{price:.8f}"
            params["timeInForce"] = time_in_force

        elif order_type == "STOP_LIMIT":
            params["type"]        = "STOP"
            params["price"]       = f"{price:.8f}"
            params["stopPrice"]   = f"{stop_price:.8f}"
            params["timeInForce"] = time_in_force

        else:
            raise ValueError(f"Unknown order_type: {order_type!r}")

        logger.info("Placing order | %s", params)
        response = self._post_signed(f"{API_V1}/order", data=params)
        logger.info("Order response | %s", response)
        return response

    def cancel_order(self, symbol: str, order_id: int) -> dict:
        """Cancel an open order by order ID."""
        return self._delete_signed(
            f"{API_V1}/order",
            params={"symbol": symbol, "orderId": order_id},
        )

    def get_open_orders(self, symbol: str | None = None) -> list[dict]:
        """Return open orders, optionally filtered by symbol."""
        params = {}
        if symbol:
            params["symbol"] = symbol
        return self._get_signed(f"{API_V1}/openOrders", params=params)

    # ------------------------------------------------------------------ #
    #  Internal helpers                                                    #
    # ------------------------------------------------------------------ #

    def _sync_time(self) -> None:
        """
        Compute a local clock offset against the Binance server clock.
        Called once at construction — silently retries once on failure.
        """
        try:
            data = self._get_public(f"{API_V1}/time")
            server_ms = data["serverTime"]
            local_ms  = int(time.time() * 1000)
            self._time_offset = server_ms - local_ms
            logger.debug("Time sync OK | offset=%d ms", self._time_offset)
        except Exception as exc:
            logger.warning("Time sync failed (using local clock): %s", exc)
            self._time_offset = 0

    def _timestamp(self) -> int:
        return int(time.time() * 1000) + self._time_offset

    def _sign(self, query_string: str) -> str:
        return hmac.new(
            self._api_secret,
            query_string.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()

    # ---- HTTP verbs ---- #

    def _get_public(self, url: str, params: dict | None = None) -> Any:
        logger.debug("GET (public) %s params=%s", url, params)
        return self._request("GET", url, params=params)

    def _get_signed(self, url: str, params: dict | None = None) -> Any:
        params = dict(params or {})
        params["timestamp"] = self._timestamp()
        params["signature"] = self._sign(urlencode(params))
        logger.debug("GET (signed) %s params=%s", url, {k: v for k, v in params.items() if k != "signature"})
        return self._request("GET", url, params=params)

    def _post_signed(self, url: str, data: dict | None = None) -> Any:
        data = dict(data or {})
        data["timestamp"] = self._timestamp()
        data["signature"] = self._sign(urlencode(data))
        logger.debug("POST (signed) %s data=%s", url, {k: v for k, v in data.items() if k != "signature"})
        return self._request("POST", url, data=data)

    def _delete_signed(self, url: str, params: dict | None = None) -> Any:
        params = dict(params or {})
        params["timestamp"] = self._timestamp()
        params["signature"] = self._sign(urlencode(params))
        logger.debug("DELETE (signed) %s params=%s", url, {k: v for k, v in params.items() if k != "signature"})
        return self._request("DELETE", url, params=params)

    def _request(self, method: str, url: str, **kwargs) -> Any:
        try:
            resp = self._session.request(method, url, timeout=REQUEST_TIMEOUT, **kwargs)
        except requests.exceptions.Timeout as exc:
            logger.error("Request timed out: %s %s", method, url)
            raise NetworkError(f"Request timed out: {url}") from exc
        except requests.exceptions.ConnectionError as exc:
            logger.error("Connection error: %s %s — %s", method, url, exc)
            raise NetworkError(f"Connection failed: {url}") from exc
        except requests.exceptions.RequestException as exc:
            logger.error("Unexpected request error: %s", exc)
            raise NetworkError(str(exc)) from exc

        logger.debug("HTTP %s ← %s %s", resp.status_code, method, url)

        try:
            body = resp.json()
        except ValueError:
            logger.error("Non-JSON response (%s): %s", resp.status_code, resp.text[:200])
            resp.raise_for_status()
            return {}

        if isinstance(body, dict) and "code" in body and body["code"] != 200:
            code    = body.get("code", -1)
            message = body.get("msg", "Unknown error")
            logger.error("API error %s: %s", code, message)
            raise BinanceClientError(code, message)

        return body
