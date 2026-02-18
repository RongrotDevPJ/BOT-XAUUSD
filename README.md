# XAUUSD Trading Bot (Sniper Mode)

A standard-grade automated trading bot for Gold (XAUUSD) using Python and MetaTrader 5.
**tailored for small capital accounts (e.g., $10)** with strict risk management.

## ⚠️ High Risk Warning
This bot is configured for a **$10 Start Capital**.
- **Lot Size**: 0.01 (Minimum)
- **Stop Loss**: 500 Points (~$5 Loss)
- **Risk**: A single Stop Loss hit will wipe ~50% of your capital. Two consecutive losses = ~100% loss.
- **Recommendation**: Use a **Cent Account** used for testing, where $10 = 1000 USC.

## Prerequisites
1.  **MetaTrader 5 (MT5)** installed and logged in.
2.  **Algorithm Trading Allowed**: Tools > Options > Expert Advisors > Check "Allow algorithmic trading".
3.  **Python 3.9+**.

## Setup & Run

1.  **Install Libraries**:
    ```bash
    pip install -r requirements.txt
    ```
    *(If `pip` fails, try `python -m pip install -r requirements.txt`)*

2.  **Run Bot**:
    ```bash
    python main.py
    ```

3.  **Check Logs**:
    -   `trading_bot.log` file.
    -   Console output.

## Configuration (`config.py`)
-   `SYMBOL`: "XAUUSD"
-   `RISK_DIVISOR`: 50000 (Adjusts lot size scaling)
-   `MIN_LOT`: 0.01 (Floor for small accounts)
-   `FORBIDDEN_HOURS`: [4, 5] (Time filter for high spreads)

## Strategy
-   **Trend**: EMA 50 > EMA 200 (Buy) / EMA 50 < EMA 200 (Sell).
-   **Momentum**: RSI > 50 (Buy) / RSI < 50 (Sell).
-   **Execution**: 1 Trade at a time.
