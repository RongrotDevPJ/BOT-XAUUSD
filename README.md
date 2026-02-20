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

## Strategies
The bot includes three specialized trading strategies:

1.  **Triple Confluence (M5)**: A high-probability strategy using EMA 200, Bollinger Bands, and RSI. Optimized to capture momentum shifts at extreme value levels.
2.  **MACD + RSI (M15/M5)**: A trend-following strategy using MACD crossovers confirmed by RSI and Volume (ADX).
3.  **SMC - Order Blocks & FVG (M5)**: An advanced Smart Money Concepts strategy that identifies institutional supply/demand zones (Order Blocks) and Fair Value Gaps for sniper entries.

## Risk Management
- **Dynamic Lot Sizing**: Calculates lot size based on account balance or a fixed risk percentage per trade.
- **Auto-Protection**: Includes Break Even (BE), Trailing Stops, and Partial Take Profit (Partial TP).
- **Time Filters**: Automatic detection of high-volume sessions (London/NY) with dynamic server time sync.
- **Safety**: Daily profit targets to prevent over-trading.

