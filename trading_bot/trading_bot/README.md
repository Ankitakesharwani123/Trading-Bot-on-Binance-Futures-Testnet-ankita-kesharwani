# Binance Futures Testnet Trading Bot

A clean, production-structured Python CLI application for placing orders on the **Binance Futures Testnet (USDT-M)**.

---

## Project Structure

```
trading_bot/
├── bot/
│   ├── __init__.py
│   ├── client.py          # Binance REST client (signing, HTTP, error handling)
│   ├── orders.py          # Order placement logic + structured result type
│   ├── validators.py      # Input validation (all user params)
│   └── logging_config.py  # Rotating file + console logger
├── cli.py                 # CLI entry point (argparse)
├── logs/
│   └── trading_bot.log    # Auto-created on first run
├── requirements.txt
└── README.md
```

---

## Setup

### 1. Register a Binance Futures Testnet account

1. Visit [https://testnet.binancefuture.com](https://testnet.binancefuture.com)
2. Sign up / log in with a GitHub account
3. Under **API Key**, generate a new key pair
4. Note your **API Key** and **Secret Key**

### 2. Clone / unzip the project

```bash
git clone https://github.com/your-username/trading-bot.git
cd trading_bot
```

### 3. Create a virtual environment (recommended)

```bash
python3 -m venv .venv
source .venv/bin/activate        # macOS / Linux
.venv\Scripts\activate           # Windows
```

### 4. Install dependencies

```bash
pip install -r requirements.txt
```

### 5. Export credentials

```bash
export BINANCE_API_KEY=your_api_key_here
export BINANCE_API_SECRET=your_secret_key_here
```

> **Windows (PowerShell)**:
> ```powershell
> $env:BINANCE_API_KEY="your_api_key_here"
> $env:BINANCE_API_SECRET="your_secret_key_here"
> ```

---

## How to Run

All commands are run from the `trading_bot/` root directory.

### Place a Market order

```bash
python cli.py --symbol BTCUSDT --side BUY --type MARKET --quantity 0.001
```

### Place a Limit order

```bash
python cli.py --symbol ETHUSDT --side SELL --type LIMIT --quantity 0.1 --price 3500.00
```

### Place a Stop-Limit order (bonus)

```bash
python cli.py \
  --symbol BTCUSDT \
  --side BUY \
  --type STOP_LIMIT \
  --quantity 0.001 \
  --price 68000 \
  --stop-price 67500
```

### Pass credentials inline (not recommended on shared machines)

```bash
python cli.py \
  --api-key YOUR_KEY \
  --api-secret YOUR_SECRET \
  --symbol BTCUSDT --side BUY --type MARKET --quantity 0.001
```

### Full help

```bash
python cli.py --help
```

---

## Example Output

```
═══════════════════════════════════════════════
  ORDER REQUEST SUMMARY
═══════════════════════════════════════════════
  Symbol         BTCUSDT
  Side           BUY
  Type           MARKET
  Quantity       0.001
═══════════════════════════════════════════════

──────────────────────────────────────────────
  ORDER PLACED SUCCESSFULLY
──────────────────────────────────────────────
  Order ID               3728194
  Symbol                 BTCUSDT
  Side                   BUY
  Type                   MARKET
  Status                 FILLED
  Limit price            —
  Avg fill price         67423.50000
  Original qty           0.001
  Executed qty           0.001
──────────────────────────────────────────────
```

---

## Logging

Logs are written to `logs/trading_bot.log` (auto-created).

| Level   | Destination        | Contents                                      |
|---------|--------------------|-----------------------------------------------|
| DEBUG   | File only          | Full request params, HTTP status, raw JSON    |
| INFO    | File + console     | Order submit, response summary, time sync     |
| WARNING | File + console     | Validation errors, non-fatal issues           |
| ERROR   | File + console     | API errors, network failures, unexpected exceptions |

The file handler rotates at **5 MB** and keeps **3 backups**.

---

## Validation Rules

| Parameter    | Rule                                                      |
|--------------|-----------------------------------------------------------|
| `--symbol`   | Non-empty, alphanumeric, uppercased automatically         |
| `--side`     | Must be `BUY` or `SELL`                                   |
| `--type`     | Must be `MARKET`, `LIMIT`, or `STOP_LIMIT`                |
| `--quantity` | Positive float                                            |
| `--price`    | Required and > 0 for `LIMIT` and `STOP_LIMIT`             |
| `--stop-price` | Required and > 0 for `STOP_LIMIT` only                  |

---

## Assumptions

- The bot targets the **Binance Futures Testnet (USDT-M)** exclusively (`https://testnet.binancefuture.com`). Real-money trading is **not supported**.
- Time synchronisation is performed automatically at startup using the Binance server clock to prevent `timestamp` drift errors (common on VMs/WSL).
- `STOP_LIMIT` maps to Binance's `STOP` order type (limit price + stop trigger price).
- All prices and quantities are sent with 8 decimal places of precision.
- Credentials are read from environment variables by default to avoid accidental exposure in shell history.
- Python 3.10+ is required (uses `X | Y` union type hints).

---

## Dependencies

| Package    | Version  | Purpose                        |
|------------|----------|--------------------------------|
| `requests` | ≥ 2.31.0 | HTTP client for REST API calls |

No third-party Binance SDK is used — all API interaction is via direct REST calls with HMAC-SHA256 signing.
