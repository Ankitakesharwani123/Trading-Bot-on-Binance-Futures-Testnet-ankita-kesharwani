"""
bot/orders.py
Order-placement business logic — sits between CLI and the raw client.

Responsibilities
----------------
- Accepts already-validated params from the CLI layer
- Calls BinanceFuturesClient.place_order()
- Formats and returns a structured OrderResult for display
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from bot.client import BinanceFuturesClient, BinanceClientError, NetworkError
from bot.logging_config import setup_logger

logger = setup_logger("trading_bot.orders")


@dataclass
class OrderResult:
    """Parsed, display-ready representation of a placed order."""
    success:      bool
    order_id:     str  = ""
    symbol:       str  = ""
    side:         str  = ""
    order_type:   str  = ""
    status:       str  = ""
    price:        str  = ""
    avg_price:    str  = ""
    orig_qty:     str  = ""
    executed_qty: str  = ""
    raw:          dict = field(default_factory=dict)
    error:        str  = ""

    def display(self) -> None:
        """Print a formatted summary to stdout."""
        if not self.success:
            print(f"\n  ✗  Order FAILED: {self.error}\n")
            return

        width = 22
        rows: list[tuple[str, Any]] = [
            ("Order ID",          self.order_id),
            ("Symbol",            self.symbol),
            ("Side",              self.side),
            ("Type",              self.order_type),
            ("Status",            self.status),
            ("Limit price",       self.price or "—"),
            ("Avg fill price",    self.avg_price or "—"),
            ("Original qty",      self.orig_qty),
            ("Executed qty",      self.executed_qty),
        ]
        print("\n" + "─" * 46)
        print("  ORDER PLACED SUCCESSFULLY")
        print("─" * 46)
        for label, value in rows:
            print(f"  {label:<{width}} {value}")
        print("─" * 46 + "\n")


def place_order(client: BinanceFuturesClient, params: dict) -> OrderResult:
    """
    Place an order using *params* (already validated dict from CLI layer).
    Returns an OrderResult — never raises.
    """
    logger.info(
        "Submitting order | symbol=%s side=%s type=%s qty=%s",
        params["symbol"], params["side"], params["order_type"], params["quantity"],
    )

    try:
        raw = client.place_order(
            symbol     = params["symbol"],
            side       = params["side"],
            order_type = params["order_type"],
            quantity   = params["quantity"],
            price      = params.get("price"),
            stop_price = params.get("stop_price"),
        )
    except BinanceClientError as exc:
        logger.error("Order rejected by API | code=%s msg=%s", exc.code, exc.message)
        return OrderResult(success=False, error=f"[{exc.code}] {exc.message}")
    except NetworkError as exc:
        logger.error("Network failure placing order | %s", exc)
        return OrderResult(success=False, error=f"Network error: {exc}")
    except Exception as exc:                       # unexpected — log full traceback
        logger.exception("Unexpected error placing order")
        return OrderResult(success=False, error=str(exc))

    result = OrderResult(
        success      = True,
        order_id     = str(raw.get("orderId",     "")),
        symbol       = str(raw.get("symbol",      "")),
        side         = str(raw.get("side",        "")),
        order_type   = str(raw.get("type",        "")),
        status       = str(raw.get("status",      "")),
        price        = str(raw.get("price",       "")),
        avg_price    = str(raw.get("avgPrice",    "")),
        orig_qty     = str(raw.get("origQty",     "")),
        executed_qty = str(raw.get("executedQty", "")),
        raw          = raw,
    )
    logger.info(
        "Order accepted | id=%s status=%s executedQty=%s avgPrice=%s",
        result.order_id, result.status, result.executed_qty, result.avg_price,
    )
    return result
