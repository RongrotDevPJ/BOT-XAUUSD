import pandas as pd

class IndicatorCalculator:
    @staticmethod
    def add_indicators(df):
        """Calculates indicators needed for the strategy using pure pandas (Python 3.14 compatible)"""
        # Ensure 'close' column is numeric
        df['close'] = pd.to_numeric(df['close'])
        df['high'] = pd.to_numeric(df['high'])
        df['low'] = pd.to_numeric(df['low'])

        # EMA Trend Filter (200)
        df['ema_trend'] = df['close'].ewm(span=200, adjust=False).mean()
        
        # EMA Exit Filter (20)
        df['ema_exit'] = df['close'].ewm(span=20, adjust=False).mean()
        
        # RSI (14) - Manual Implementation (Wilder's Smoothing)
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0))
        loss = (-delta.where(delta < 0, 0))
        avg_gain = gain.ewm(alpha=1/14, min_periods=14, adjust=False).mean()
        avg_loss = loss.ewm(alpha=1/14, min_periods=14, adjust=False).mean()
        rs = avg_gain / avg_loss
        df['rsi'] = 100 - (100 / (1 + rs))
        
        return df

    @staticmethod
    def get_swing_low(df, lookback):
        """Gets the lowest low in the lookback period"""
        return df['low'].tail(lookback).min()

    @staticmethod
    def get_swing_high(df, lookback):
        """Gets the highest high in the lookback period"""
        return df['high'].tail(lookback).max()
