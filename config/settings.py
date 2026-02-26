import MetaTrader5 as mt5
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class Config:
    #Directory: c:\Users\t-rongrot.but\Documents\Bot Trading XAUUSD\
    
    # =========================================
    # 🔧 1. SETTINGS: GENERAL (ตั้งค่าทั่วไป)
    # =========================================
    # --- Filter: Trading Filters ---
    MAX_SPREAD_POINTS = 50      # ❗ กรอง Spread ไม่ให้เกิน 50 จุด (กันช่วงข่าว/ตลาดเปิด)
    SYMBOL = "XAUUSD"

    TIMEFRAME = mt5.TIMEFRAME_M15  # 🚀 Timeframe: M15 (Gives more reliable signals with less noise)
    MAGIC_NUM = 888888             # 🎱 Lucky Magic Number (Triple Confluence)
    DEVIATION = 20                 # ค่าความคลาดเคลื่อนที่ยอมรับได้ (Slippage)
    USE_REALTIME_CANDLE = False     # 🚀 True = เทรดแท่งปัจจุบัน (ไวแต่เสี่ยง Repaint), False = รอจบแท่ง (ชัวร์กว่า)


    # =========================================
    # 💰 2. SETTINGS: MONEY MANAGEMENT (บริหารเงินทุน)
    # =========================================
    # สูตร: Balance / RISK_DIVISOR = Lot Size
    # ตัวอย่าง: ทุน $1,000
    # - 50000  = 0.02 Lot (Safe) 🐢
    # - 10000  = 0.10 Lot (Risk) 🐇
    # - 5000   = 0.20 Lot (Sniper) 🦅
    # RISK_DIVISOR = 5000 
    
    # 🌟 NEW: Risk-Based MM (% Per Trade)
    ENABLE_RISK_PER_TRADE = False   # ❌ ปิดการคำนวณแบบ % เพื่อใช้ RISK_DIVISOR ตามที่คุณต้องการ
    RISK_DIVISOR = 5000             # 💰 ปรับลดความเสี่ยงเป็น หาร 5000 (ปลอดภัยขึ้นสำหรับ XAUUSD)
    RISK_PERCENT = 1.0              # 🛡️ 1% Risk per trade
    MAX_LOT_SIZE = 10.0             # Safety Cap
    MIN_LOT = 0.01          # ออกขั้นต่ำสุด

    # =========================================
    # 🎯 3. SETTINGS: TARGETS & LIMITS (เป้าหมาย)
    # =========================================
    STOP_LOSS_POINTS = 650      # 🛡️ FXIED SL: 650 Points ($5) for Safety
    TAKE_PROFIT_POINTS = 1625   # 🎯 FIXED TP: 1625 Points (RR 1:2.5)
    
    # 📱 Telegram Notifications
    TELEGRAM_ENABLED = True     # Set to True to enable
    TELEGRAM_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN', '')          # API Token from @BotFather
    TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID', '')        # Chat ID from @userinfobot

    # 🚫 Economic Calendar / News Filter
    NEWS_FILTER_ENABLED = True  # Set to True to enable
    NEWS_AVOID_MINUTES = 30      # Avoid trading 30 mins before/after news
    
    # --- Auto Risk Management (ATR Based) ---
    ENABLE_AUTO_RISK = True     # ✅ Enabled ATR SL (More dynamic)
    ATR_SL_MULT = 1.6           # 🔧 M5: เพิ่มเป็๋น 1.6 เพื่อลดการสะบัดชน SL (Breathing room)
    ATR_TP_MULT = 4.0           # 🎯 TP = ATR * 4.0 (รักษา RR 1:2.5 ตามแผน)

    DAILY_PROFIT_TARGET = 500.0 # เป้าหมายกำไรรายวัน ($) -> ถ้าถึงแล้วหยุดเทรด

    # --- Swing High/Low Strategy ---
    USE_SWING_SL = False        # ❌ Disable Swing SL (Use Fixed 500pts for controlled risk)
    SWING_LOOKBACK = 20         # ย้อนหลังกี่แท่งเพื่อหา Swing High/Low
    RISK_REWARD_RATIO = 2.5     # TP ต้องเป็น 2.5 เท่าของ SL (RR 1:2.5) 📈 🎯
    MAX_SL_POINTS = 1000        # 🛡️ M15: ขยาย Max SL เป็น 1000 จุด (ครอบคลุมระยะสะบัด ควบคุม Risk ผ่าน Lot แทน)

    # =========================================
    # 🛡️ 4. SETTINGS: PROFIT PROTECTION (ล็อกกำไร)
    # =========================================
    # Stage 1: Break Even (50% of TP)
    ENABLE_BREAK_EVEN = True    # เปิดใช้ระบบขยับ SL บังทุน
    BREAK_EVEN_PERCENT = 0.5    # 🎯 บังทุนเมื่อกำไรถึง 50% ของระยะ TP (เพิ่มระยะหายใจตอนย่อ)
    BREAK_EVEN_LOCK = 100       # ล็อคกำไรที่ 100 จุด (Entry + 100)

    # Stage 2: Profit Lock (65% of TP)
    ENABLE_PROFIT_LOCK = True   # เปิดใช้ระบบล็อคกำไร 50%
    PROFIT_LOCK_PERCENT = 0.65  # 🎯 ล็อคกำไรเมื่อกำไรถึง 65% ของระยะ TP
    PROFIT_LOCK_LEVEL = 0.5     # ขยับ SL มาที่ 50% ของระยะ TP

    
    # --- Trailing Stop (Dynamic SL) ---
    TRAILING_STOP_TRIGGER = 200 # เริ่มทำงานเมื่อกำไรถึง X จุด
    TRAILING_STOP_LOCK = 150    # ตีตัวออกห่างจากราคาปัจจุบัน X จุด (Trailing Distance)
    TRAILING_STOP_STEP = 50     # ขยับ SL ทุกๆ 50 จุด (ป้องกัน MT5 ส่งคำสั่งถี่เกินไป)

    # --- Dynamic TP Extension ---
    ENABLE_DYNAMIC_TP = True
    TP_EXTENSION_TRIGGER = 200  # ถ้าเข้าใกล้เป้าหมาย 200 จุด ให้ยืด TP ออกไป
    TP_EXTENSION_DISTANCE = 500 # ยืด TP ออกไปอีก 500 จุด

    # --- NEW: Partial Take Profit (แบ่งปิดกำไร) ---
    ENABLE_PARTIAL_TP = True    # ✅ Enable Partial TP (0.10 -> Close 0.05)
    PARTIAL_TP_RR = 1.0         # 🎯 แบ่งปิดเมื่อกำไร = 1 เท่าของความเสี่ยง (RR 1:1)
    PARTIAL_TP_RATIO = 0.5      # 💰 แบ่งปิด 50% ของ Lot (เช่น 0.10 -> ปิด 0.05) (TP1 -> TP2)

    # =========================================
    # 🧩 7. STRATEGY SPECIFIC OVERRIDES
    # =========================================
    # Overrides default settings based on strategy selection
    
    MACD_CONFIG = {
        'TIMEFRAME': mt5.TIMEFRAME_M15,
        'STOP_LOSS_POINTS': 400,
        'TAKE_PROFIT_POINTS': 1000,
        'ATR_SL_MULT': 1.5,
        'ATR_TP_MULT': 3.75, # 1.5 * 2.5
        'MAX_SL_POINTS': 500,
    }
    
    SMC_CONFIG = {
        'TIMEFRAME': mt5.TIMEFRAME_M5,
        'STOP_LOSS_POINTS': 300,
        'TAKE_PROFIT_POINTS': 750,
        'ATR_SL_MULT': 1.2,
        'ATR_TP_MULT': 3.0, # 1.2 * 2.5
        'MAX_SL_POINTS': 500,
    }

    # =========================================
    # 📈 5. SETTINGS: STRATEGY (เทคนิคกราฟ)
    # =========================================
    # --- 5. Strategy Parameters (RSI + MACD) ---
    MAX_EMA_DISTANCE = 0   # 0 = ปิดใช้งาน EMA Distance
    # EMA Trend Filter
    EMA_TREND = 200        # EMA 200 Trend Filter
    
    # --- 6. SMC (Smart Money Concepts) ---
    SMC_LOOKBACK = 100            # จำนวนแท่งย้อนหลังที่เช็คหา OB
    OB_MITIGATION_THRESHOLD = 150 # ระยะห่าง (Points) ที่ยอมรับว่า "Retest" (ราคาเข้ามาใกล้ OB)
    OB_GUARD_THRESHOLD = 100      # ⛔ ห้ามเข้าออเดอร์ถ้าใกล้แนวต้าน/รับ ฝั่งตรงข้ามเกิน X จุด (กันติดดอย)
    
    # Dynamic ATR Thresholds (Professional)
    USE_DYNAMIC_THRESHOLD = True   # เปิดระบบปรับระยะอัตโนมัติตามความแรงตลาด
    OB_RETEST_ATR_MULT = 0.5       # ระยะ Retest = ATR * 0.5 (เช่น ATR=300 => Retest=150)
    OB_GUARD_ATR_MULT = 0.5        # ระยะ Guard = ATR * 0.5 (เพิ่มระยะปลอดภัย)
    
    # MTF (Multi-Timeframe) Filter
    ENABLE_MTF_FILTER = True      # เปิดระบบเช็คเทรนด์ภาพใหญ่
    MTF_TIMEFRAME = mt5.TIMEFRAME_H1 # เช็คเทรนด์ H1 (1 ชั่วโมง)
    MTF_EMA_PERIOD = 200          # ใช้ EMA 200 เป็นเงื่อนไขใน H1ด้วย
    
    # ADX (Trend Strength) - Removed from Logic but kept in config just in case
    ADX_PERIOD = 14
    ADX_THRESHOLD = 25     # 0 = ปิด ADX (ไม่กรองความแรงเทรนด์ เอาแค่ EMA+RSI)
    
    # MACD Confirmation (Optional)
    USE_MACD_CONFIRMATION = False # ❌ M5: SMC Pure Action is faster and more precise.
    
    # MACD Settings
    MACD_FAST = 12
    MACD_SLOW = 26
    MACD_SIGNAL = 9
    
    # RSI (Relative Strength Index)
    RSI_PERIOD = 14
    RSI_BUY_MIN = 50       # Buy: RSI > 50 (แรงซื้อเริ่มมา) 
    RSI_SELL_MAX = 50      # Sell: RSI < 50 (แรงขายเริ่มมา)
    RSI_SNIPER_BUY_MIN = 42 # 🎯 Sniper Buy: RSI > 42 (เข้าไวขึ้นเมื่อแตะ OB)
    RSI_SNIPER_SELL_MAX = 58 # 🎯 Sniper Sell: RSI < 58 (เข้าไวขึ้นเมื่อแตะ OB)
    RSI_OVERBOUGHT = 65    # Adjusted from 70 for more entries
    RSI_OVERSOLD = 35      # Adjusted from 30 for more entries
    
    # Bollinger Bands
    BB_PERIOD = 20         # เส้นกลาง SMA 20
    BB_STD = 2.0           # Standard Deviation 2.0
    
    # ATR (Average True Range)
    ATR_PERIOD = 14        # ดูความผันผวน 14 แท่งย้อนหลัง

    # =========================================
    # ⏳ 6. SETTINGS: TIME FILTER (ช่วงเวลาห้ามเทรด)
    # =========================================
    # --- 6. Time Filter (Session Trading) ---
    # Kill Zones: 13:00 - 23:00 (Focus on volume)
    TRADING_START_HOUR = 00  # Start 13:00 (London Open)
    TRADING_END_HOUR = 23    # Stop 23:00 (NY Session)

    
    # --- SMC Advanced Settings ---
    ENABLE_DYNAMIC_TP_SMC = True # ✅ Use Swing High/Low as TP (Target Liquidity)
