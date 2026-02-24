import MetaTrader5 as mt5
import pandas as pd
import logging
from . import config

# Missing constants in some MT5 versions
SYMBOL_FILLING_FOK = 1
SYMBOL_FILLING_IOC = 2
SYMBOL_FILLING_RETURN = 4

class MT5Executor:
    def __init__(self):
        self.connected = False
        self.filling_type = mt5.ORDER_FILLING_IOC # Default

    def connect(self):
        """Initializes connection to MT5 and detects filling mode with retry logic for IPC timeouts"""
        max_retries = 3
        for attempt in range(max_retries):
            # If not first attempt, try shutting down before re-initializing
            if attempt > 0:
                mt5.shutdown()
                import time
                time.sleep(2) # Wait for terminal to settle
                logging.warning(f"🔄 Re-connection attempt {attempt + 1}/{max_retries}...")

            if mt5.initialize():
                break
            else:
                error = mt5.last_error()
                logging.error(f"mt5.initialize() failed, error code = {error}")
                if attempt == max_retries - 1:
                    return False
        
        symbol_info = mt5.symbol_info(config.SYMBOL)
        if symbol_info is None:
            logging.error(f"{config.SYMBOL} not found.")
            mt5.shutdown()
            return False
            
        # Detect Filling Type (Crucial for different brokers)
        filling_mode = symbol_info.filling_mode
        if filling_mode & SYMBOL_FILLING_IOC:
            self.filling_type = mt5.ORDER_FILLING_IOC
        elif filling_mode & SYMBOL_FILLING_FOK:
            self.filling_type = mt5.ORDER_FILLING_FOK
        else:
            self.filling_type = mt5.ORDER_FILLING_RETURN



        if not symbol_info.visible:
            if not mt5.symbol_select(config.SYMBOL, True):
                logging.error(f"symbol_select({config.SYMBOL}) failed")
                mt5.shutdown()
                return False
        
        self.connected = True
        logging.info(f"✅ Connected to MT5: {config.SYMBOL} (Filling: {self.filling_type})")
        return True

    def fetch_ohlcv(self, symbol, timeframe, limit=100):
        """Fetches OHLCV data from MT5"""
        rates = mt5.copy_rates_from_pos(symbol, timeframe, 0, limit)
        if rates is None:
            logging.error(f"Failed to copy rates: {mt5.last_error()}")
            return None
            
        df = pd.DataFrame(rates)
        df['time'] = pd.to_datetime(df['time'], unit='s')
        return df

    def get_balance(self):
        """Gets account balance"""
        account_info = mt5.account_info()
        if account_info:
            return account_info.balance
        return 0

    def create_order(self, symbol, order_type, volume, price, sl=0.0, tp=0.0, comment=""):
        """Sends an order to MT5"""
        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": symbol,
            "volume": volume,
            "type": order_type,
            "price": price,
            "sl": sl,
            "tp": tp,
            "deviation": config.DEVIATION,
            "magic": config.MAGIC_NUMBER,
            "comment": comment,
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": self.filling_type,
        }
        
        # RETRY LOGIC for Requotes
        for attempt in range(3):
            result = mt5.order_send(request)
            if result is None:
                logging.error(f"❌ order_send() returned None. Check MT5 connection.")
                return None

            if result.retcode in [mt5.TRADE_RETCODE_REQUOTE, mt5.TRADE_RETCODE_PRICE_OFF]:
                logging.warning(f"⚠️ Requote/Price Off (Attempt {attempt+1}). Retrying...")
                # Update price for retry if it's a market order
                tick = mt5.symbol_info_tick(symbol)
                if tick:
                    request["price"] = tick.ask if order_type == mt5.ORDER_TYPE_BUY else tick.bid
                import time
                time.sleep(0.5)
                continue
            
            if result.retcode != mt5.TRADE_RETCODE_DONE:
                logging.error(f"❌ Order Failed: {result.comment} ({result.retcode})")
                return None
            return result
        
        return None

    def close_position(self, position):
        """Closes a specific MT5 position"""
        tick = mt5.symbol_info_tick(position.symbol)
        if tick is None:
            logging.error(f"Failed to get tick for closing {position.ticket}")
            return None

        order_type = mt5.ORDER_TYPE_SELL if position.type == mt5.ORDER_TYPE_BUY else mt5.ORDER_TYPE_BUY
        price = tick.bid if order_type == mt5.ORDER_TYPE_SELL else tick.ask
        
        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": position.symbol,
            "volume": position.volume,
            "type": order_type,
            "position": position.ticket,
            "price": price,
            "deviation": config.DEVIATION,
            "magic": config.MAGIC_NUMBER,
            "comment": "Close Position",
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": self.filling_type,
        }
        
        result = mt5.order_send(request)
        if result is None:
            logging.error(f"❌ close_position() returned None.")
            return None

        if result.retcode != mt5.TRADE_RETCODE_DONE:
            logging.error(f"❌ Close Failed: {result.comment} ({result.retcode})")
            return None
        return result

    def get_active_positions(self):
        """Fetches active positions by Magic Number"""
        positions = mt5.positions_get(symbol=config.SYMBOL)
        if positions:
            return [p for p in positions if p.magic == config.MAGIC_NUMBER]
        return []

    def modify_position(self, ticket, sl, tp=0.0):
        """Modifies SL/TP for an open position. Note: You must provide both SL and TP to avoid wiping them."""
        request = {
            "action": mt5.TRADE_ACTION_SLTP,
            "position": ticket,
            "sl": float(sl),
            "tp": float(tp),
        }
        # RETRY LOGIC for Modification
        for attempt in range(3):
            result = mt5.order_send(request)
            if result is None:
                logging.error("❌ modify_position() returned None.")
                return False
                
            if result.retcode in [mt5.TRADE_RETCODE_REQUOTE, mt5.TRADE_RETCODE_PRICE_OFF]:
                logging.warning(f"⚠️ Requote (Modify SL) Attempt {attempt+1}. Retrying...")
                import time
                time.sleep(0.5)
                continue

            if result.retcode != mt5.TRADE_RETCODE_DONE:
                logging.error(f"❌ Modify SL Failed: {result.comment} ({result.retcode})")
                return False
            return True
        return False

    def is_connected(self):
        """Checks if connected to MT5 and account info is available"""
        terminal_info = mt5.terminal_info()
        if terminal_info is None:
            return False
        return terminal_info.connected

    def check_margin(self, symbol, order_type, volume, price):
        """Checks if there's enough margin to open the position"""
        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": symbol,
            "volume": volume,
            "type": order_type,
            "price": price,
            "deviation": config.DEVIATION,
            "magic": config.MAGIC_NUMBER,
            "type_filling": self.filling_type,
            "type_time": mt5.ORDER_TIME_GTC
        }
        margin = mt5.order_check(request)
        if margin is None:
            return False, "Failed to check margin"
        
        free_margin = mt5.account_info().margin_free
        if margin.margin > free_margin:
            return False, f"Not enough money! Required: {margin.margin}, Free: {free_margin}"
        return True, "OK"
