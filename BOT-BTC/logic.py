import logging
import MetaTrader5 as mt5
from utils.indicators import Indicators

from . import config

class TradingLogic:
    def __init__(self, executor):
        self.executor = executor


    def check_signal(self, df):
        """
        Checks for Buy/Sell signals based on RSI + EMA Filter
        Logic: 
        - Buy: RSI < 30 and Price > EMA 200
        - Sell: RSI > 70 and Price < EMA 200
        """
        if df is None or len(df) < 200:
            return None

        # Use the LAST COMPLETED candle for more reliable signals
        # If df has current candle, use index -2
        last_row = df.iloc[-2] if len(df) >= 2 else df.iloc[-1]
        close_price = last_row['close']
        rsi_val = last_row['rsi']
        ema_trend = last_row['ema_trend']
        
        # --- DETAILED LOGGING FOR TRANSPARENCY ---
        trend_status = "UP 📈" if close_price > ema_trend else "DOWN 📉"
        status_msg = f"🔍 Signal check | RSI: {rsi_val:.2f} | Price: {close_price:.2f} | EMA200: {ema_trend:.2f} ({trend_status})"
        
        # BUY LOGIC
        if rsi_val < config.RSI_OVERSOLD:
            if close_price > ema_trend:
                logging.info(f"{status_msg} 🟢 BUY SIGNAL DETECTED")
                return 'buy'
            else:
                logging.info(f"{status_msg} ⚠️ Skip BUY: RSI is Oversold but Price is below EMA200 (Requires Uptrend)")
        
        # SELL LOGIC
        elif rsi_val > config.RSI_OVERBOUGHT:
            if close_price < ema_trend:
                logging.info(f"{status_msg} 🔴 SELL SIGNAL DETECTED")
                return 'sell'
            else:
                logging.info(f"{status_msg} ⚠️ Skip SELL: RSI is Overbought but Price is above EMA200 (Requires Downtrend)")
        
        return None

    def get_sl_tp(self, df, side, entry_price):
        """Calculates SL and TP prices based on config (Fixed Points or Swing Low)"""
        symbol_info = mt5.symbol_info(config.SYMBOL)
        if not symbol_info: return None, None
        
        point = symbol_info.point
        sl_points = config.STOP_LOSS_POINTS
        
        if side == 'buy':
            if config.USE_SWING_LOW_SL:
                sl_price = Indicators.get_swing_low(df, config.SWING_LOOKBACK)

                diff_pts = (entry_price - sl_price) / point
                
                # Check Min SL
                if diff_pts < (sl_points / 2):
                    sl_price = entry_price - (sl_points * point)
            else:
                sl_price = entry_price - (sl_points * point)
            
            # ✅ ENFORCE GLOBAL SL CAP
            risk_pts = (entry_price - sl_price) / point
            if risk_pts > config.MAX_SL_POINTS:
                sl_price = entry_price - (config.MAX_SL_POINTS * point)
                risk_pts = config.MAX_SL_POINTS

            # ✅ STRICT RR 1:2.5
            tp_price = entry_price + (risk_pts * point * config.RISK_REWARD_RATIO)
            return sl_price, tp_price

        elif side == 'sell':
            if config.USE_SWING_LOW_SL:
                sl_price = Indicators.get_swing_high(df, config.SWING_LOOKBACK)

                diff_pts = (sl_price - entry_price) / point
                
                # Check Min SL
                if diff_pts < (sl_points / 2):
                    sl_price = entry_price + (sl_points * point)
            else:
                sl_price = entry_price + (sl_points * point)
            
            # ✅ ENFORCE GLOBAL SL CAP
            risk_pts = (sl_price - entry_price) / point
            if risk_pts > config.MAX_SL_POINTS:
                sl_price = entry_price + (config.MAX_SL_POINTS * point)
                risk_pts = config.MAX_SL_POINTS

            # ✅ STRICT RR 1:2.5
            tp_price = entry_price - (risk_pts * point * config.RISK_REWARD_RATIO)
            return sl_price, tp_price
            
        return None, None

