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
        
        signal = "WAIT"
        status_detail = "WAIT"
        extra_data = {
            "price": price_close,
            "ema_trend": ema_200,
            "rsi": rsi,
            "bb_lower": bb_lower,
            "bb_upper": bb_upper
        }

        # --- FINAL DECISION (Triple Confluence) ---
        
        # 1. Trend Filter (EMA)
        is_uptrend = price_close > ema_200
        is_downtrend = price_close < ema_200
        
        # 2. Value Filter (Bollinger Bands)
        # Buy: Low touched/broke Lower Band
        touched_lower = prev['low'] <= bb_lower
        # Sell: High touched/broke Upper Band
        touched_upper = prev['high'] >= bb_upper
        
        # 3. Momentum Filter (RSI)
        is_oversold = rsi < Config.RSI_OVERSOLD   # < 30
        is_overbought = rsi > Config.RSI_OVERBOUGHT # > 70
        
        # Check Trading Hours
        current_hour = datetime.datetime.now().hour
        is_trading_time = Config.TRADING_START_HOUR <= current_hour <= Config.TRADING_END_HOUR
        
        if not is_trading_time:
             return "SLEEP", "💤 Sleeping (Time)", extra_data

        # --- ENTRY SIGNAL ---
        # ต้องครบ 3 เงื่อนไขเท่านั้น
        if is_uptrend and touched_lower and is_oversold:
            status_detail = f"EMA Uptrend + BB Lower Touch + RSI Oversold ({rsi:.1f})"
            if not self.bot.check_open_positions():
                signal = "BUY"
                status_detail += " [GO! 🚀]"
                
        elif is_downtrend and touched_upper and is_overbought:
             status_detail = f"EMA Downtrend + BB Upper Touch + RSI Overbought ({rsi:.1f})"
             if not self.bot.check_open_positions():
                signal = "SELL"
                status_detail += " [GO! 📉]"
        else:
            # Status for monitoring
            if is_uptrend: trend_str = "UP"
            elif is_downtrend: trend_str = "DOWN"
            else: trend_str = "FLAT"
            
            status_detail = f"⚪ WAIT | Trend:{trend_str} RSI:{rsi:.1f}"

        return signal, status_detail, extra_data
