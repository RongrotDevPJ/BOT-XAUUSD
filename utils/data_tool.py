import MetaTrader5 as mt5
import pandas as pd
from datetime import datetime, timedelta
import logging
import sys
import os

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.settings import Config

# Setup Basic Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def connect_mt5():
    if not mt5.initialize():
        logging.error("Init failed")
        return False
    return True

def export_trade_history(days=365):
    """Exports Account Trade History (Profit/Loss)"""
    try:
        if not connect_mt5(): return

        # defined lookback period
        to_date = datetime.now() + timedelta(hours=1) # Buffer for server time
        from_date = to_date - timedelta(days=days)
        
        logging.info(f"⏳ Fetching Trade History from {from_date.date()}...")
        
        # Get history (Fetch all, filter in Python for robustness)
        deals = mt5.history_deals_get(from_date, to_date)
        
        if deals:
            data = []
            for deal in deals:
                # Filter by symbol type and Entry OUT
                if deal.symbol == Config.SYMBOL and deal.entry == mt5.DEAL_ENTRY_OUT:
                    data.append({
                        'time': datetime.fromtimestamp(deal.time),
                        'ticket': deal.ticket,
                        'type': "BUY" if deal.type == 0 else "SELL",
                        'volume': deal.volume,
                        'price': deal.price,
                        'commission': deal.commission,
                        'swap': deal.swap,
                        'profit': deal.profit,
                        'comment': deal.comment
                    })
            
            df = pd.DataFrame(data)
            
            # Ensure data dir exists
            data_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data')
            if not os.path.exists(data_dir):
                os.makedirs(data_dir)
                
            filename = os.path.join(data_dir, 'export_trade_history.csv')
            df.to_csv(filename, index=False)
            logging.info(f"✅ Trade History saved to: {filename} ({len(df)} trades)")
            return df
        else:
            logging.warning("❌ No history found.")
            return None

    except Exception as e:
        logging.error(f"Error export_trade_history: {e}")

def export_market_data(days=30):
    """Exports Candle Data (OHLC) for Backtesting"""
    try:
        if not connect_mt5(): return
        
        # Calculate number of candles (Approx for M15)
        # 1 day = 96 candles (M15)
        count = days * 96 
        
        logging.info(f"⏳ Fetching Market Data ({days} days)...")
        
        rates = mt5.copy_rates_from_pos(Config.SYMBOL, Config.TIMEFRAME, 0, count)
        
        if rates is not None:
            df = pd.DataFrame(rates)
            df['time'] = pd.to_datetime(df['time'], unit='s')
            
            # Select columns for backtest
            df = df[['time', 'open', 'high', 'low', 'close', 'tick_volume', 'spread']]
            
            # Ensure data dir exists
            data_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data')
            if not os.path.exists(data_dir):
                os.makedirs(data_dir)
            
            filename = os.path.join(data_dir, 'export_market_data.csv')
            df.to_csv(filename, index=False)
            logging.info(f"✅ Market Data saved to: {filename} ({len(df)} candles)")
            return df
        else:
            logging.warning("❌ No market data found.")
            return None

    except Exception as e:
        logging.error(f"Error export_market_data: {e}")

if __name__ == "__main__":
    print("--- MT5 Data Exporter ---")
    print("1. Export Trade History (Profit/Loss)")
    print("2. Export Market Data (Price for Backtest)")
    print("3. Export Both")
    
    choice = input("Select (1-3): ")
    
    if choice == '1':
        export_trade_history(days=365) # 1 Year
    elif choice == '2':
        export_market_data(days=60)    # 2 Months
    elif choice == '3':
        export_trade_history()
        export_market_data()
    
    mt5.shutdown()
