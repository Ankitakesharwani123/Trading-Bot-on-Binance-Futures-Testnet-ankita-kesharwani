"""
bot/validators.py
Input validation for order parameters.
All public functions raise ValidationError on bad input.
"""

from __future__ import annotations

VALID_SIDES = {"BUY", "SELL"}
VALID_ORDER_TYPES = {"MARKET", "LIMIT", "STOP_LIMIT"}


class ValidationError(ValueError):
    """Raised when user-supplied order parameters fail validation."""


def validate_symbol(symbol: str) -> str:
    s = symbol.strip().upper()
    if not s:
        raise ValidationError("Symbol must not be empty.")
    if not s.isalnum():
        raise ValidationError(f"Symbol '{s}' contains invalid characters (alphanumeric only).")
    return s


def validate_side(side: str) -> str:
    s = side.strip().upper()
    if s not in VALID_SIDES:
        raise ValidationError(f"Invalid side '{s}'. Choose from: {', '.join(sorted(VALID_SIDES))}.")
    return s


def validate_order_type(order_type: str) -> str:
    t = order_type.strip().upper()
    if t not in VALID_ORDER_TYPES:
        raise ValidationError(
            f"Invalid order type '{t}'. Choose from: {', '.join(sorted(VALID_ORDER_TYPES))}."
        )
    return t


def validate_quantity(quantity: float | str) -> float:
    try:
        qty = float(quantity)
    except (TypeError, ValueError):
        raise ValidationError(f"Quantity '{quantity}' is not a valid number.")
    if qty <= 0:
        raise ValidationError(f"Quantity must be > 0, got {qty}.")
    return qty


def validate_price(price: float | str | None, order_type: str) -> float | None:
    """Required and > 0 for LIMIT / STOP_LIMIT; ignored for MARKET."""
    if order_type == "MARKET":
        return None
    if price is None:
        raise ValidationError(f"--price is required for {order_type} orders.")
    try:
        p = float(price)
    except (TypeError, ValueError):
        raise ValidationError(f"Price '{price}' is not a valid number.")
    if p <= 0:
        raise ValidationError(f"Price must be > 0, got {p}.")
    return p


def validate_stop_price(stop_price: float | str | None, order_type: str) -> float | None:
    """Required and > 0 for STOP_LIMIT only."""
    if order_type != "STOP_LIMIT":
        return None
    if stop_price is None:
        raise ValidationError("--stop-price is required for STOP_LIMIT orders.")
    try:
        sp = float(stop_price)
    except (TypeError, ValueError):
        raise ValidationError(f"Stop price '{stop_price}' is not a valid number.")
    if sp <= 0:
        raise ValidationError(f"Stop price must be > 0, got {sp}.")
    return sp


def validate_order_params(
    symbol: str,
    side: str,
    order_type: str,
    quantity: float | str,
    price: float | str | None = None,
    stop_price: float | str | None = None,
) -> dict:
    """
    Run all validations and return a cleaned dict.
    Raises ValidationError on the first failure found.
    """
    cleaned_type = validate_order_type(order_type)
    result = {
        "symbol":     validate_symbol(symbol),
        "side":       validate_side(side),
        "order_type": cleaned_type,
        "quantity":   validate_quantity(quantity),
    }
    p  = validate_price(price, cleaned_type)
    sp = validate_stop_price(stop_price, cleaned_type)
    if p  is not None: result["price"]      = p
    if sp is not None: result["stop_price"] = sp
    return result
