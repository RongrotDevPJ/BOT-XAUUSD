import MetaTrader5 as mt5
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# BTC Bot Configuration (MT5 Edition)

# --- MT5 Settings ---
SYMBOL = "BTCUSD"           # Change to your broker's BTC symbol
TIMEFRAME = mt5.TIMEFRAME_M15 # or mt5.TIMEFRAME_H1
MAGIC_NUMBER = 999999       # Unique ID for this bot's orders
DEVIATION = 20              # Slippage points

# --- Strategy Parameters ---
EMA_TREND_PERIOD = 200
EMA_EXIT_PERIOD = 20
RSI_PERIOD = 14
RSI_OVERSOLD = 30
RSI_OVERBOUGHT = 70

# --- Risk Management ---
LOT_SIZE = 0.01             # Fixed lot for small account ($16)
STOP_LOSS_POINTS = 500      # 🛡️ FXIED SL points (e.g., $5.00 if 0.01 lot)
MAX_SL_POINTS = 1000        # ⚠️ Hard Cap for SL (Adjusted for BTC volatility)
RISK_REWARD_RATIO = 2.5     # 🏆 THE GOLDEN RULE
USE_SWING_LOW_SL = False    # Set to False to use fixed SL for $16 account
SWING_LOOKBACK = 10         


# --- Protection (BE & TS) ---
ENABLE_BREAK_EVEN = True    
BE_TRIGGER_POINTS = 300     # Move SL to BE when profit reaches 300 points
BE_LOCK_POINTS = 50         # Lock 50 points profit

ENABLE_TRAILING_STOP = True
TS_TRIGGER_POINTS = 500     # Start trailing after 500 points profit
TS_STEP_POINTS = 100        # Move SL every 100 points profit

DAILY_LOSS_LIMIT = 2.0      # 🛑 Stop trading if lost more than $2 today
HEARTBEAT_HOURS = 1         # 💓 Send status report every 1 hour

# --- Execution Controls ---
WAIT_FOR_CANDLE_CLOSE = True # ⏳ Prevent False Signals
MAX_SPREAD_POINTS = 1000     # ⚠️ Don't enter if spread is too wide

# --- Notifications ---
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN', '')     # ใส่ Token จาก @BotFather
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID', '')       # ใส่ ID จาก @userinfobot
LINE_NOTIFY_TOKEN = os.getenv('LINE_NOTIFY_TOKEN', '')      # ใส่ Token จาก LINE Notify
