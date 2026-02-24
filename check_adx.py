import MetaTrader5 as mt5
import pandas as pd
import os
import sys

# Add project root to path
sys.path.append(os.getcwd())

from config.settings import Config
from utils.indicators import Indicators

def check_adx():
    if not mt5.initialize():
        print("❌ MT5 Initialization failed")
        return

    symbol = "XAUUSD"
    # Try different common XAUUSD names
    if not mt5.symbol_select(symbol, True):
        symbol = "GOLD"
        if not mt5.symbol_select(symbol, True):
            print("❌ Symbol XAUUSD or GOLD not found")
            mt5.shutdown()
            return

    print(f"--- ADX Snapshot for {symbol} ---")
    
    # Fetch data (Standard M5 as per config)
    timeframe = mt5.TIMEFRAME_M5
    rates = mt5.copy_rates_from_pos(symbol, timeframe, 0, 100)
    
    if rates is None:
        print("❌ Failed to fetch rates")
        mt5.shutdown()
        return
        
    df = pd.DataFrame(rates)
    df['time'] = pd.to_datetime(df['time'], unit='s')
    
    # Calculate ADX
    adx_period = 14
    df['adx'] = Indicators.calculate_adx(df, adx_period)
    
    if df.empty or 'adx' not in df.columns:
        print("❌ Failed to calculate ADX")
    else:
        current_adx = df.iloc[-1]['adx']
        threshold = 25 # Standard
        
        status = "✅ STRONG TREND" if current_adx > threshold else "❌ LOW TREND / SIDEWAY"
        
        print(f"Time: {df.iloc[-1]['time']}")
        print(f"Current price: {df.iloc[-1]['close']}")
        print(f"Current ADX: {current_adx:.2f}")
        print(f"Threshold: {threshold}")
        print(f"Status: {status}")

    mt5.shutdown()

if __name__ == "__main__":
    check_adx()
