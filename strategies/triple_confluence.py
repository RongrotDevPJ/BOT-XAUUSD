from .base import BaseStrategy
from config.settings import Config
from utils.indicators import Indicators
import datetime

class TripleConfluenceStrategy(BaseStrategy):
    """
    🏆 Triple Confluence Strategy (3 ประสาน)
    1. Trend: EMA 200
    2. Value: Bollinger Bands (20, 2)
    3. Momentum: RSI (14)
    """
    def __init__(self, bot_instance):
        self.bot = bot_instance

    def analyze(self, df):
        if df is None: return "WAIT", "No Data", {}

        # Select Candle based on Config
        row_index = -1 if Config.USE_REALTIME_CANDLE else -2 
        
        prev = df.iloc[row_index]
        price_close = prev['close']
        
        # Indicators
        ema_200 = prev['ema_trend']  # Ensure EMA_TREND is 200 in settings
        bb_upper = prev['bb_upper']
        bb_lower = prev['bb_lower']
        rsi = prev['rsi']
        
        # Candlestick Pattern check on the signal candle
        pattern = Indicators.check_candlestick_pattern(df, row_index)
        
        signal = "WAIT"
        status_detail = "WAIT"
        extra_data = {
            "price": price_close,
            "ema_trend": ema_200,
            "rsi": rsi,
            "bb_lower": bb_lower,
            "bb_upper": bb_upper,
            "pattern": pattern if pattern else "None"
        }

        # --- FINAL DECISION (Triple Confluence) ---
        
        # 1. Trend Filter (EMA)
        is_uptrend = price_close > ema_200
        is_downtrend = price_close < ema_200
        
        # 2. & 3. Value and Momentum (Bollinger Bands Check)
        lookback_window = df.iloc[row_index-4 : row_index+1] # Last 5 relative to row_index
        touched_lower = any(lookback_window['low'] <= lookback_window['bb_lower'])
        touched_upper = any(lookback_window['high'] >= lookback_window['bb_upper'])

        
        # Check Trading Hours
        server_time = self.bot.get_server_time()
        current_hour = server_time.hour
        is_trading_time = Config.TRADING_START_HOUR <= current_hour <= Config.TRADING_END_HOUR
        
        if not is_trading_time:
             return "SLEEP", f"💤 Sleeping (Time) | Server Time: {server_time.strftime('%H:%M')}", extra_data

        # 2. & 3. Value and Momentum (RSI Momentum Filter)
        # Instead of strict OS/OB recovery, we check if RSI confirms the bounce direction
        # Buy: RSI > 40 (Not too weak, confirming momentum up)
        # Sell: RSI < 60 (Not too strong, confirming momentum down)
        rsi_bullish = rsi > 40
        rsi_bearish = rsi < 60

        # --- NEW: Multi-Timeframe (MTF) Trend Filter ---
        mtf_trend = self.bot.get_mtf_trend()
        buy_mtf_ok = (mtf_trend in ["UP", "READY", "Unknown"])
        sell_mtf_ok = (mtf_trend in ["DOWN", "READY", "Unknown"])

        # --- ENTRY SIGNAL ---
        # ต้องครบ 3 เงื่อนไขหลัก + MTF Filter + Candlestick Pattern
        if is_uptrend and touched_lower and rsi_bullish:
            has_bull_pattern = pattern in ["BULLISH_PINBAR", "BULLISH_ENGULFING"]
            
            if not buy_mtf_ok:
                status_detail = f"WAIT [TRPL | Up + BB Low | RSI:{rsi:.1f} | Filtered by MTF: {mtf_trend} ❌]"
            elif not has_bull_pattern:
                status_detail = f"WAIT [TRPL | Up + BB Low | RSI:{rsi:.1f} | Waiting for Pattern 🏮]"
            elif not self.bot.check_open_positions():
                signal = "BUY"
                status_detail = f"🚀 BUY | TRPL | Up + BB Low | {pattern} | RSI:{rsi:.1f} | MTF:OK"
                
        elif is_downtrend and touched_upper and rsi_bearish:
             has_bear_pattern = pattern in ["BEARISH_PINBAR", "BEARISH_ENGULFING"]
             
             if not sell_mtf_ok:
                 status_detail = f"WAIT [TRPL | Down + BB Up | RSI:{rsi:.1f} | Filtered by MTF: {mtf_trend} ❌]"
             elif not has_bear_pattern:
                 status_detail = f"WAIT [TRPL | Down + BB Up | RSI:{rsi:.1f} | Waiting for Pattern 🏮]"
             elif not self.bot.check_open_positions():
                signal = "SELL"
                status_detail = f"📉 SELL | TRPL | Down + BB Up | {pattern} | RSI:{rsi:.1f} | MTF:OK"

        else:
            # Status for monitoring
            trend_str = "UP" if is_uptrend else ("DOWN" if is_downtrend else "FLAT")
            bb_str = "Lower" if touched_lower else ("Upper" if touched_upper else "Mid")
            
            status_detail = f"⚪ TRPL | T:{trend_str} | BB:{bb_str} | RSI:{rsi:.1f}"

        return signal, status_detail, extra_data
