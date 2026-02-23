import logging
import MetaTrader5 as mt5
from .indicators import IndicatorCalculator
from . import config

class TradingLogic:
    def __init__(self, executor):
        self.executor = executor
        self.indicators = IndicatorCalculator()

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
        status_msg = f"🔍 Analyzing Signal | RSI: {rsi_val:.2f} | Price: {close_price:.2f} | EMA200: {ema_trend:.2f}"
        
        # BUY LOGIC
        if rsi_val < config.RSI_OVERSOLD:
            if close_price > ema_trend:
                logging.info(f"{status_msg} 🟢 BUY SIGNAL DETECTED")
                return 'buy'
            else:
                logging.info(f"{status_msg} ⚠️ Buy Condition: RSI OK (<{config.RSI_OVERSOLD}), but Price is BELOW EMA200 (No Trend Up)")
        
        # SELL LOGIC
        elif rsi_val > config.RSI_OVERBOUGHT:
            if close_price < ema_trend:
                logging.info(f"{status_msg} 🔴 SELL SIGNAL DETECTED")
                return 'sell'
            else:
                logging.info(f"{status_msg} ⚠️ Sell Condition: RSI OK (>{config.RSI_OVERBOUGHT}), but Price is ABOVE EMA200 (No Trend Down)")
        
        return None

    def get_stop_loss(self, df, side, entry_price):
        """Calculates SL price based on config (Fixed Points or Swing Low)"""
        point = mt5.symbol_info(config.SYMBOL).point
        if side == 'buy':
            if config.USE_SWING_LOW_SL:
                sl_price = IndicatorCalculator.get_swing_low(df, config.SWING_LOOKBACK)
                if entry_price - sl_price < (config.STOP_LOSS_POINTS / 2 * point):
                    sl_price = entry_price - (config.STOP_LOSS_POINTS * point)
            else:
                sl_price = entry_price - (config.STOP_LOSS_POINTS * point)
            return sl_price
        elif side == 'sell':
            if config.USE_SWING_LOW_SL:
                sl_price = IndicatorCalculator.get_swing_high(df, config.SWING_LOOKBACK)
                if sl_price - entry_price < (config.STOP_LOSS_POINTS / 2 * point):
                    sl_price = entry_price + (config.STOP_LOSS_POINTS * point)
            else:
                sl_price = entry_price + (config.STOP_LOSS_POINTS * point)
            return sl_price
        return None
