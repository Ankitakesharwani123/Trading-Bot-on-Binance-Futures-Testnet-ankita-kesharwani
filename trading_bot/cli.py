#!/usr/bin/env python3
"""
cli.py
CLI entry point for the Binance Futures Testnet trading bot.

Usage examples
--------------
# Market BUY
python cli.py --symbol BTCUSDT --side BUY --type MARKET --quantity 0.001

# Limit SELL
python cli.py --symbol ETHUSDT --side SELL --type LIMIT --quantity 0.1 --price 3500.00

# Stop-Limit BUY
python cli.py --symbol BTCUSDT --side BUY --type STOP_LIMIT --quantity 0.001 \
              --price 68000 --stop-price 67500

# Pass credentials via env vars (recommended) or --api-key / --api-secret flags
export BINANCE_API_KEY=your_key
export BINANCE_API_SECRET=your_secret
"""

from __future__ import annotations

import argparse
import os
import sys
import textwrap

from bot.client import BinanceFuturesClient, BinanceClientError, NetworkError
from bot.logging_config import setup_logger
from bot.orders import place_order
from bot.validators import ValidationError, validate_order_params

logger = setup_logger("trading_bot.cli")


# ------------------------------------------------------------------ #
#  CLI argument parser                                                 #
# ------------------------------------------------------------------ #

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="trading_bot",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description=textwrap.dedent(
            """\
            Binance Futures Testnet — order placement CLI
            ─────────────────────────────────────────────
            Supported order types: MARKET, LIMIT, STOP_LIMIT

            Credentials can be supplied via:
              • environment variables  BINANCE_API_KEY / BINANCE_API_SECRET  (recommended)
              • --api-key / --api-secret flags  (avoid on shared machines)
            """
        ),
    )

    # ── Credentials ──────────────────────────────────────────────────
    creds = parser.add_argument_group("credentials")
    creds.add_argument(
        "--api-key",
        default=os.getenv("BINANCE_API_KEY", ""),
        metavar="KEY",
        help="Binance Testnet API key (default: $BINANCE_API_KEY)",
    )
    creds.add_argument(
        "--api-secret",
        default=os.getenv("BINANCE_API_SECRET", ""),
        metavar="SECRET",
        help="Binance Testnet API secret (default: $BINANCE_API_SECRET)",
    )

    # ── Order parameters ─────────────────────────────────────────────
    order = parser.add_argument_group("order parameters")
    order.add_argument("--symbol",     required=True, help="Trading symbol, e.g. BTCUSDT")
    order.add_argument("--side",       required=True, choices=["BUY", "SELL"],
                       type=str.upper, help="BUY or SELL")
    order.add_argument("--type",       required=True,
                       choices=["MARKET", "LIMIT", "STOP_LIMIT"],
                       type=str.upper, dest="order_type",
                       help="Order type")
    order.add_argument("--quantity",   required=True, type=float,
                       help="Order quantity")
    order.add_argument("--price",      type=float, default=None,
                       help="Limit price (required for LIMIT / STOP_LIMIT)")
    order.add_argument("--stop-price", type=float, default=None, dest="stop_price",
                       help="Stop trigger price (required for STOP_LIMIT)")

    return parser


# ------------------------------------------------------------------ #
#  Pretty-print helpers                                                #
# ------------------------------------------------------------------ #

def print_request_summary(params: dict) -> None:
    """Print the validated order request before sending."""
    print("\n" + "═" * 46)
    print("  ORDER REQUEST SUMMARY")
    print("═" * 46)
    width = 14
    print(f"  {'Symbol':<{width}} {params['symbol']}")
    print(f"  {'Side':<{width}} {params['side']}")
    print(f"  {'Type':<{width}} {params['order_type']}")
    print(f"  {'Quantity':<{width}} {params['quantity']}")
    if "price" in params:
        print(f"  {'Limit price':<{width}} {params['price']}")
    if "stop_price" in params:
        print(f"  {'Stop price':<{width}} {params['stop_price']}")
    print("═" * 46)


# ------------------------------------------------------------------ #
#  Main                                                                #
# ------------------------------------------------------------------ #

def main() -> None:
    parser = build_parser()
    args   = parser.parse_args()

    # ── Credential check ─────────────────────────────────────────────
    if not args.api_key or not args.api_secret:
        parser.error(
            "API credentials are required.\n"
            "Set BINANCE_API_KEY and BINANCE_API_SECRET environment variables,\n"
            "or pass --api-key / --api-secret."
        )

    # ── Input validation ─────────────────────────────────────────────
    logger.info(
        "CLI invoked | symbol=%s side=%s type=%s qty=%s price=%s stop_price=%s",
        args.symbol, args.side, args.order_type,
        args.quantity, args.price, args.stop_price,
    )

    try:
        params = validate_order_params(
            symbol     = args.symbol,
            side       = args.side,
            order_type = args.order_type,
            quantity   = args.quantity,
            price      = args.price,
            stop_price = args.stop_price,
        )
    except ValidationError as exc:
        logger.warning("Validation error: %s", exc)
        print(f"\n  ✗  Validation error: {exc}\n")
        sys.exit(1)

    print_request_summary(params)

    # ── Connect ──────────────────────────────────────────────────────
    try:
        client = BinanceFuturesClient(args.api_key, args.api_secret)
        logger.info("Client initialised successfully.")
    except (NetworkError, BinanceClientError) as exc:
        logger.error("Failed to initialise client: %s", exc)
        print(f"\n  ✗  Could not connect to Binance Testnet: {exc}\n")
        sys.exit(1)

    # ── Place order ──────────────────────────────────────────────────
    result = place_order(client, params)
    result.display()

    sys.exit(0 if result.success else 1)


if __name__ == "__main__":
    main()
