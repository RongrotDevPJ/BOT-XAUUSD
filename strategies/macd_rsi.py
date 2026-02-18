from .base import BaseStrategy
from config.settings import Config
from utils.indicators import Indicators
from datetime import datetime
import MetaTrader5 as mt5

class MACDRSIStrategy(BaseStrategy):
    def __init__(self, bot_instance):
        self.bot = bot_instance # Need access to bot for check_open_positions and other potential callbacks

    def analyze(self, df):
        if df is None: return "WAIT", "No Data", {}
        
        # Select Candle (Realtime vs Closed)
        if Config.USE_REALTIME_CANDLE:
             # Use CURRENT forming candle [index -1]
             row_index = -1
        else:
             # Use PREVIOUS closed candle [index -2] (Standard)
             row_index = -2

        prev_row = df.iloc[row_index]
        price = prev_row['close']
        
        ema_trend = prev_row['ema_trend']
        macd_line = prev_row['macd_line']
        macd_signal = prev_row['macd_signal']
        rsi = prev_row['rsi']
        atr = prev_row['atr']
        adx = prev_row['adx'] 
        
        signal = "WAIT"
        status_detail = "WAIT"
        
        # 0. Time Filter Check (Session)
        current_hour = datetime.now().hour
        
        # --- NEW: Multi-Timeframe (MTF) Trend ---
        mtf_trend = self.bot.get_mtf_trend() 
        buy_mtf_ok = (mtf_trend in ["UP", "READY"])
        sell_mtf_ok = (mtf_trend in ["DOWN", "READY"])

        is_trading_time = Config.TRADING_START_HOUR <= current_hour <= Config.TRADING_END_HOUR
        
        # Default initializations
        buy_ema = False
        
        extra_data = {
            "price": price,
            "macd_line": macd_line,
            "macd_signal": macd_signal,
            "ema_trend": ema_trend,
            "rsi": rsi,
            "atr": atr,
            "adx": adx,
            "mtf_trend": mtf_trend,
        }

        if is_trading_time:
            # Condition Checks
            
            # --- FRESH SIGNAL CHECK (Prevents re-entry after SL) ---
            prev_idx = row_index - 1 
            prev_candle = df.iloc[prev_idx]
            
            prev_macd_line = prev_candle['macd_line']
            prev_macd_signal = prev_candle['macd_signal']
            
            # BUY Checks
            buy_ema = price > ema_trend
            # MACD Crossover: Currently UP AND Previously DOWN/EQUAL
            buy_macd_cross = (macd_line > macd_signal) and (prev_macd_line <= prev_macd_signal)
            
            # SELL Checks (Mirror)
            sell_ema = price < ema_trend
            sell_macd_cross = (macd_line < macd_signal) and (prev_macd_line >= prev_macd_signal)
            
            # Conditions initialization for safety
            buy_rsi = False
            sell_rsi = False
            
            # Determine Logic based on Trend (EMA)
            adx_ok = (Config.ADX_THRESHOLD == 0) or (adx > Config.ADX_THRESHOLD)

            if buy_ema: # Potential Uptrend
                buy_rsi = rsi > Config.RSI_BUY_MIN and rsi < Config.RSI_OVERBOUGHT
                
                status_detail = (
                    f"🟢 UP | H1:{'✅' if buy_mtf_ok else '❌'} "
                    f"MACD:{'✅' if buy_macd_cross else '❌'} "
                    f"RSI:{'✅' if buy_rsi else '❌'} "
                    f"ADX:{'✅' if adx_ok else '⚠️'}"
                )
                
                # Logic: Trend (MACD) -> MUST align with H1 AND ADX
                if buy_mtf_ok and adx_ok:
                    if buy_macd_cross and buy_rsi:
                         if not self.bot.check_open_positions():
                            signal = "BUY"
                            status_detail += " [Trend Cross! 🚀]"
                elif not adx_ok:
                    status_detail += " [ADX Low]"
                else:
                    status_detail += " [H1 Trend Conflict ⚠️]"
            
            elif sell_ema: # Potential Downtrend
                sell_rsi = rsi < Config.RSI_SELL_MAX and rsi > Config.RSI_OVERSOLD
                
                status_detail = (
                    f"🔴 DOWN | H1:{'✅' if sell_mtf_ok else '❌'} "
                    f"MACD:{'✅' if sell_macd_cross else '❌'} "
                    f"RSI:{'✅' if sell_rsi else '❌'} "
                    f"ADX:{'✅' if adx_ok else '⚠️'}"
                )
                
                if sell_mtf_ok and adx_ok:
                    if sell_macd_cross and sell_rsi:
                        if not self.bot.check_open_positions():
                            signal = "SELL"
                            status_detail += " [Trend Cross! 📉]"
                elif not adx_ok:
                    status_detail += " [ADX Low]"
                else:
                    status_detail += " [H1 Trend Conflict ⚠️]"
            
            else:
                 status_detail = "⚪ RANGE | Price on EMA"

        else:
            signal = "SLEEP" 
            status_detail = "💤 Sleeping (Time)"

        return signal, status_detail, extra_data
