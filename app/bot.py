import MetaTrader5 as mt5
import pandas as pd
import time
from datetime import datetime, timedelta
import logging
import csv
import os
import sys
import shutil
import requests

# Ensure project root is in path
# sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))) # Redundant if running from root


from config.settings import Config
from utils.indicators import Indicators
from strategies.macd_rsi import MACDRSIStrategy
from strategies.ob_fvg_fibo import OBFVGFiboStrategy
from strategies.triple_confluence import TripleConfluenceStrategy
from utils.news_manager import NewsManager

class XAUUSDBot:
    def __init__(self, strategy_name="TRIPLE_CONFLUENCE"):
        self.symbol = Config.SYMBOL
        self.connected = False
        self.last_error_time = 0
        self.strategy_name = strategy_name
        self.server_time_offset = 0 # Calculated offset in hours
        
        # Initialize Magic Number (Offset to prevent conflict)

        self.magic_number = Config.MAGIC_NUM
        if strategy_name == "OB_FVG_FIBO":
            self.magic_number += 100 # SMC Strategy
        elif strategy_name != "TRIPLE_CONFLUENCE":
            self.magic_number += 200 # MACD Strategy (or others)
        
        # Initialize Strategy & Config Overrides
        self.config_overrides = {}
        if strategy_name == "OB_FVG_FIBO":
            self.strategy = OBFVGFiboStrategy(self)
            self.config_overrides = getattr(Config, 'SMC_CONFIG', {})
            logging.info(f"⚙️ Loaded SMC Config: Timeframe={self.config_overrides.get('TIMEFRAME')}")
        elif strategy_name == "TRIPLE_CONFLUENCE":
             self.strategy = TripleConfluenceStrategy(self)
             # No specific config override needed as we updated main settings
             logging.info(f"⚙️ Loaded Triple Confluence Config (Sniper Mode)")
        else:
            self.strategy = MACDRSIStrategy(self)
            self.config_overrides = getattr(Config, 'MACD_CONFIG', {})
            logging.info(f"⚙️ Loaded MACD Config: Timeframe={self.config_overrides.get('TIMEFRAME')}")
            
        # Track partially closed tickets to prevent double triggers
        self.partially_closed_tickets = set()
        self.last_trade_candle_time = None # 🛡️ Candle Guard
            
        # Connect
        self.news_manager = NewsManager()
        if not self.connect_mt5():
            sys.exit(1)
            
    def get_setting(self, key):
        """Get setting with strategy override priority"""
        return self.config_overrides.get(key, getattr(Config, key))

    def connect_mt5(self):
        """Initializes connection to MT5"""
        try:
            if not mt5.initialize():
                logging.error(f"Initialize failed, error code = {mt5.last_error()}")
                self.connected = False
                return False
            
            # Check Symbol
            symbol_info = mt5.symbol_info(self.symbol)
            if symbol_info is None:
                logging.error(f"{self.symbol} not found, can not check symbol")
                mt5.shutdown()
                return False
                
            if not symbol_info.visible:
                logging.info(f"{self.symbol} is not visible, trying to switch on")
                if not mt5.symbol_select(self.symbol, True):
                    logging.error(f"symbol_select({self.symbol}) failed, exit")
                    mt5.shutdown()
                    return False
            
            self.connected = True
            
            # --- CALCULATE SERVER TIME OFFSET ---
            # Get current server time and local time to find difference
            server_time = mt5.symbol_info_tick(self.symbol).time
            if server_time > 0:
                server_dt = datetime.fromtimestamp(server_time)
                local_dt = datetime.now()
                # Round to nearest hour
                diff_seconds = (server_dt - local_dt).total_seconds()
                self.server_time_offset = round(diff_seconds / 3600)
                logging.info(f"🕒 Calculated Server Time Offset: {self.server_time_offset} hours")
            
            logging.info(f"✅ Connected to MT5: {self.symbol}")
            return True
            
        except Exception as e:
            logging.error(f"Connection Exception: {e}")
            self.connected = False
            return False

    def get_server_time(self):
        """Returns current MT5 server time as datetime object"""
        try:
            tick = mt5.symbol_info_tick(self.symbol)
            if tick:
                return datetime.fromtimestamp(tick.time)
            return datetime.now() + timedelta(hours=self.server_time_offset)
        except:
            return datetime.now() + timedelta(hours=self.server_time_offset)
            
    def send_telegram_message(self, message):
        """Sends a notification to Telegram if enabled."""
        if not Config.TELEGRAM_ENABLED or not Config.TELEGRAM_TOKEN or not Config.TELEGRAM_CHAT_ID:
            return
            
        try:
            url = f"https://api.telegram.org/bot{Config.TELEGRAM_TOKEN}/sendMessage"
            payload = {
                "chat_id": Config.TELEGRAM_CHAT_ID,
                "text": message,
                "parse_mode": "HTML"
            }
            response = requests.post(url, json=payload, timeout=10)
            if response.status_code != 200:
                logging.error(f"❌ Telegram Error: {response.text}")
        except Exception as e:
            logging.error(f"❌ Failed to send Telegram: {e}")
            return False

    def get_market_data(self, timeframe=None):
        """Fetches and prepares market data for indicator calculation"""
        if timeframe is None:
            timeframe = self.get_setting('TIMEFRAME')
            
        try:
            # 1. Fetch Rates
            rates = mt5.copy_rates_from_pos(self.symbol, timeframe, 0, Config.SMC_LOOKBACK + 500)
            
            if rates is None:
                logging.warning("❌ Failed to get data")
                return None
                
            df = pd.DataFrame(rates)
            df['time'] = pd.to_datetime(df['time'], unit='s')
            
            # Calculate Common Indicators using Utils
            # 1. EMA Trend
            df['ema_trend'] = Indicators.calculate_ema(df['close'], Config.EMA_TREND)
            
            # 2. MACD
            macd, signal = Indicators.calculate_macd(
                df['close'], 
                Config.MACD_FAST, 
                Config.MACD_SLOW, 
                Config.MACD_SIGNAL
            )
            df['macd_line'] = macd
            df['macd_signal'] = signal
            
            # 3. RSI
            df['rsi'] = Indicators.calculate_rsi(df['close'], Config.RSI_PERIOD)
            
            # 5. Bollinger Bands
            bb_upper, bb_middle, bb_lower = Indicators.calculate_bollinger_bands(
                df['close'], Config.BB_PERIOD, Config.BB_STD
            )
            df['bb_upper'] = bb_upper
            df['bb_middle'] = bb_middle
            df['bb_lower'] = bb_lower
            
            # 6. ATR
            df['atr'] = Indicators.calculate_atr(df, Config.ATR_PERIOD)

            # 7. ADX
            df['adx'] = Indicators.calculate_adx(df, Config.ADX_PERIOD)
            
            return df
        except Exception as e:
            logging.error(f"Data Fetch Error: {e}")
            return None

    def get_dynamic_lot_size(self, sl_points=0):
        """Calculates lot size based on Risk Management Settings"""
        try:
            account_info = mt5.account_info()
            if account_info is None:
                logging.warning("Could not get account info, defaulting to MIN_LOT")
                return Config.MIN_LOT
            
            balance = account_info.balance
            
            # 🌟 NEW: Risk-Based Calculation
            if getattr(Config, 'ENABLE_RISK_PER_TRADE', False) and sl_points > 0:
                risk_per_trade = Config.RISK_PERCENT 
                risk_amount = balance * (risk_per_trade / 100.0)
                
                symbol_info = mt5.symbol_info(self.symbol)
                if not symbol_info: return Config.MIN_LOT
                
                # Calculate value per point for 1 lot
                # TickValue is usually for 1 lot per TickSize
                # Profit = (Price_Diff) * (TickValue / TickSize) * Volume
                # Risk = (SL_Points * Point) * (TickValue / TickSize) * Volume
                # Volume = Risk / (SL_Points * Point * (TickValue / TickSize))
                
                tick_value = symbol_info.trade_tick_value
                tick_size = symbol_info.trade_tick_size
                point = symbol_info.point
                
                if tick_size == 0: tick_size = point # Prevent div by zero
                
                value_per_point_1lot = point * (tick_value / tick_size)
                
                if value_per_point_1lot == 0:
                    # Fallback for XAUUSD standard: 1 point (0.01) = $1 per 1.0 lot
                    # 100 points = $100
                    value_per_point_1lot = 1.0 
                    
                lot_size = risk_amount / (sl_points * value_per_point_1lot)
                
            else:
                # Formula: Balance / RISK_DIVISOR
                divisor = getattr(Config, 'RISK_DIVISOR', 10000)
                lot_size = balance / divisor
            
            # Enforce Limits
            max_lot = getattr(Config, 'MAX_LOT_SIZE', 10.0)
            lot_size = min(lot_size, max_lot)
            lot_size = max(lot_size, Config.MIN_LOT)
            
            # Round to 2 decimal places
            lot_size = round(lot_size, 2)
            
            return lot_size
        except Exception as e:
            logging.error(f"Lot Size Error: {e}")
            return Config.MIN_LOT

    def check_open_positions(self):
        """Checks if there are any open positions for this symbol AND strategy"""
        try:
            positions = mt5.positions_get(symbol=self.symbol)
            if positions:
                # Filter by Magic Number
                my_positions = [p for p in positions if p.magic == self.magic_number]
                if my_positions:
                    return True
            return False
        except Exception as e:
            logging.error(f"Position Check Error: {e}")
            return True # Fail safe

    def get_mtf_trend(self):
        """Checks H1 (Higher Timeframe) Trend using EMA 200"""
        if not Config.ENABLE_MTF_FILTER:
            return "READY"
            
        try:
            # Fetch H1 data
            df_mtf = self.get_market_data(timeframe=Config.MTF_TIMEFRAME)
            
            if df_mtf is None or len(df_mtf) < Config.MTF_EMA_PERIOD:
                return "Unknown"
            
            # Calculate EMA 200 for H1 (Already done in get_market_data if EMA_TREND matches)
            if Config.MTF_EMA_PERIOD == Config.EMA_TREND:
                ema_h1 = df_mtf['ema_trend']
            else:
                ema_h1 = Indicators.calculate_ema(df_mtf['close'], Config.MTF_EMA_PERIOD)
            
            price_h1 = df_mtf.iloc[-1]['close']
            ema_val = ema_h1.iloc[-1]
            
            if price_h1 > ema_val:
                return "UP"
            elif price_h1 < ema_val:
                return "DOWN"
            else:
                return "RANGE"
                
        except Exception as e:
            logging.error(f"MTF Trend Error: {e}")
            return "Error"

    def close_order(self, ticket):
        """Closes an order by ticket"""
        try:
            # Check if position exists
            positions = mt5.positions_get(ticket=ticket)
            if not positions:
                return False
                
            pos = positions[0]
            
            # Close Logic (Opposite Deal)
            action = mt5.TRADE_ACTION_DEAL
            type_close = mt5.ORDER_TYPE_SELL if pos.type == mt5.ORDER_TYPE_BUY else mt5.ORDER_TYPE_BUY
            price = mt5.symbol_info_tick(self.symbol).bid if type_close == mt5.ORDER_TYPE_SELL else mt5.symbol_info_tick(self.symbol).ask
            
            request = {
                "action": action,
                "position": ticket,
                "symbol": self.symbol,
                "volume": pos.volume,
                "type": type_close,
                "price": price,
                "deviation": Config.DEVIATION,
                "magic": self.magic_number,
                "comment": "Close Reverse",
                "type_time": mt5.ORDER_TIME_GTC,
                "type_filling": mt5.ORDER_FILLING_IOC,
            }
            
            result = mt5.order_send(request)
            if result.retcode != mt5.TRADE_RETCODE_DONE:
                 logging.error(f"❌ Close Failed: {result.comment}")
                 return False
            else:
                 logging.info(f"✅ Order Closed: {ticket}")
                 return True
                 
        except Exception as e:
            logging.error(f"Close Order Error: {e}")
            return False

    def close_partial(self, ticket, volume):
        """Closes a partial volume of an order"""
        try:
            positions = mt5.positions_get(ticket=ticket)
            if not positions: return False
            pos = positions[0]
            
            action = mt5.TRADE_ACTION_DEAL
            type_close = mt5.ORDER_TYPE_SELL if pos.type == mt5.ORDER_TYPE_BUY else mt5.ORDER_TYPE_BUY
            price = mt5.symbol_info_tick(self.symbol).bid if type_close == mt5.ORDER_TYPE_SELL else mt5.symbol_info_tick(self.symbol).ask
            
            request = {
                "action": action,
                "position": ticket,
                "symbol": self.symbol,
                "volume": volume, # Partial Volume
                "type": type_close,
                "price": price,
                "deviation": Config.DEVIATION,
                "magic": self.magic_number,
                "comment": "Partial TP 💰",
                "type_time": mt5.ORDER_TIME_GTC,
                "type_filling": mt5.ORDER_FILLING_IOC,
            }
            
            result = mt5.order_send(request)
            if result.retcode == mt5.TRADE_RETCODE_DONE:
                logging.info(f"✅ Partial Closed! Ticket: {ticket} | Closed Volume: {volume}")
                self.send_telegram_message(
                    f"💰 <b>PARTIAL PROFIT</b>\n"
                    f"Ticket: <code>{ticket}</code>\n"
                    f"Closed: <code>{volume} lots</code>\n"
                    f"Remaining: <code>{result.volume} lots</code>"
                )
                return True
            else:
                 logging.error(f"❌ Partial Close Failed: {result.comment}")
                 return False
        except Exception as e:
            logging.error(f"Partial Close Error: {e}")
            return False

    def execute_trade(self, signal, reason="", indicators={}, atr=0.0, custom_sl=0.0, candle_time=None):
        """Sends Buy/Sell orders to MT5 (Dynamic ATR SL/TP or Custom SL)"""
        try:
            symbol_info = mt5.symbol_info(self.symbol)
            if symbol_info is None: return
            
            spread = symbol_info.spread
            if spread > Config.MAX_SPREAD_POINTS:
                logging.warning(f"⚠️ High Spread Detected! ({spread} pts > {Config.MAX_SPREAD_POINTS} pts). Trade Ignored.")
                return

            # 0. ERROR COOLDOWN (Anti-Spam)
            if time.time() - self.last_error_time < 60:
                return
            
            # --- REVERSE LOGIC START ---
            # Check for opposite positions and close them
            positions = mt5.positions_get(symbol=self.symbol)
            if positions:
                my_positions = [p for p in positions if p.magic == self.magic_number]
                for pos in my_positions:
                    # If Signal BUY -> Close SELL
                    if signal == "BUY" and pos.type == mt5.ORDER_TYPE_SELL:
                        logging.info(f"🔄 Reversing Signal! Closing SELL {pos.ticket}...")
                        self.close_order(pos.ticket)
                    
                    # If Signal SELL -> Close BUY
                    elif signal == "SELL" and pos.type == mt5.ORDER_TYPE_BUY:
                        logging.info(f"🔄 Reversing Signal! Closing BUY {pos.ticket}...")
                        self.close_order(pos.ticket)
            # --- REVERSE LOGIC END ---

            # 1. FINAL CHECK for existing positions (After potential closure)
            if self.check_open_positions():
                logging.warning(f"⚠️ Signal {signal} ignored: Position already exists.")
                return 

            # 2. Prepare Order Specs
            symbol_info = mt5.symbol_info(self.symbol)
            if symbol_info is None: return
            
            point = symbol_info.point
            
            # Initialize Variables
            sl = 0.0
            tp = 0.0
            price = 0.0
            order_type = None
            risk = 0.0 # Price Change amount
            
            if signal == "BUY":
                order_type = mt5.ORDER_TYPE_BUY
                price = mt5.symbol_info_tick(self.symbol).ask
                
                # SL Calculation
                if custom_sl > 0:
                    sl = custom_sl
                    # Safety check: SL must be below price
                    if sl >= price:
                        logging.warning("⚠️ Custom SL is above/at Buy Price. Defaulting to standard SL.")
                        sl = price - (self.get_setting('STOP_LOSS_POINTS') * point)
                
                elif Config.USE_SWING_SL:
                   rates = mt5.copy_rates_from_pos(self.symbol, self.get_setting('TIMEFRAME'), 0, Config.SWING_LOOKBACK + 5)
                   if rates is not None:
                       swing_low = min([x['low'] for x in rates[:-1]]) 
                       sl = swing_low
                   else:
                       sl = price - (self.get_setting('STOP_LOSS_POINTS') * point)
                elif Config.ENABLE_AUTO_RISK and atr > 0:
                    sl = price - (atr * self.get_setting('ATR_SL_MULT'))
                else:
                    sl = price - (self.get_setting('STOP_LOSS_POINTS') * point)

                # Validate Risk & Cap
                risk = price - sl
                
                min_risk = 100 * point 
                if risk < min_risk:
                    risk = min_risk
                    sl = price - risk
                
                max_risk = self.get_setting('MAX_SL_POINTS') * point
                if risk > max_risk:
                    if custom_sl == 0: 
                        sl = price - max_risk
                        risk = max_risk 

                tp = price + (risk * Config.RISK_REWARD_RATIO)
                
            elif signal == "SELL":
                order_type = mt5.ORDER_TYPE_SELL
                price = mt5.symbol_info_tick(self.symbol).bid
                
                 # SL Calculation
                if custom_sl > 0:
                    sl = custom_sl
                    # Safety: SL must be above price
                    if sl <= price:
                        logging.warning("⚠️ Custom SL is below/at Sell Price. Defaulting to standard SL.")
                        sl = price + (self.get_setting('STOP_LOSS_POINTS') * point)
                
                elif Config.USE_SWING_SL:
                   rates = mt5.copy_rates_from_pos(self.symbol, self.get_setting('TIMEFRAME'), 0, Config.SWING_LOOKBACK + 5)
                   if rates is not None:
                       swing_high = max([x['high'] for x in rates[:-1]])
                       sl = swing_high
                   else:
                       sl = price + (self.get_setting('STOP_LOSS_POINTS') * point)
                elif Config.ENABLE_AUTO_RISK and atr > 0:
                    sl = price + (atr * self.get_setting('ATR_SL_MULT'))
                else:
                    sl = price + (self.get_setting('STOP_LOSS_POINTS') * point)

                 # Validate Risk & Cap
                risk = sl - price
                
                min_risk = 100 * point
                if risk < min_risk:
                    risk = min_risk
                    sl = price + risk
                    
                max_risk = self.get_setting('MAX_SL_POINTS') * point
                if risk > max_risk:
                     if custom_sl == 0:
                        sl = price + max_risk
                        risk = max_risk

                tp = price - (risk * Config.RISK_REWARD_RATIO)
            
            else:
                return # Unknown Signal

            # 3. CALCULATE LOT SIZE (Dynamic Risk)
            # Convert risk (price difference) to points
            sl_dist_points = risk / point
            volume = self.get_dynamic_lot_size(sl_points=sl_dist_points)

            action = mt5.TRADE_ACTION_DEAL
            type_time = mt5.ORDER_TIME_GTC
            type_filling = mt5.ORDER_FILLING_IOC 
            
            request = {
                "action": action,
                "symbol": self.symbol,
                "volume": volume,
                "type": order_type,
                "price": price,
                "sl": sl,
                "tp": tp,
                "deviation": Config.DEVIATION,
                "magic": self.magic_number,
                "comment": "Bot " + self.strategy_name,
                "type_time": type_time,
                "type_filling": type_filling,
            }

            result = mt5.order_send(request)
            
            if result.retcode != mt5.TRADE_RETCODE_DONE:
                if result.retcode == 10027:
                    logging.error(f"❌ Order Failed: [10027] AutoTrading disabled by client! (กรุณากดปุ่ม 'Algo Trading' ใน MT5)")
                else:
                    logging.error(f"❌ Order Failed: {result.comment} (Retcode: {result.retcode})")
                
                self.last_error_time = time.time()
                logging.info(f"⏳ Cooldown activated: Waiting 60s before retry...")
            else:
                # ✅ SUCCESS LOGGING
                ind_str = " | ".join([f"{k}:{v}" for k,v in indicators.items()])
                log_msg = (
                    f"\n✅ Order Executed: {signal} | Ticket: {result.order}\n"
                    f"   Price: {price} | Lot: {volume} | SL: {sl:.2f} | TP: {tp:.2f}\n"
                    f"   Reason: {reason}\n"
                    f"   Indicators: {ind_str}"
                )
                logging.info(log_msg)
                
                # Save to specific Entry Log
                self.save_entry_log(result.order, signal, price, reason, indicators)
                self.last_trade_candle_time = candle_time # 🛡️ Mark candle as traded

                # Telegram Notification
                self.send_telegram_message(
                    f"🚀 <b>ORDER PLACED</b>\n"
                    f"Type: <code>{signal}</code>\n"
                    f"Price: <code>{price}</code>\n"
                    f"Lot: <code>{volume}</code>\n"
                    f"SL: <code>{sl:.2f}</code> | TP: <code>{tp:.2f}</code>\n"
                    f"Reason: <i>{reason}</i>"
                )
                
        except Exception as e:
            logging.error(f"Execution Error: {e}")
            self.last_error_time = time.time() 

    def save_entry_log(self, ticket, signal, price, reason, indicators):
        """Saves detailed entry log to CSV"""
        try:
            data_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data')
            if not os.path.exists(data_dir):
                os.makedirs(data_dir)

            filename = os.path.join(data_dir, 'entry_log.csv')
            file_exists = os.path.isfile(filename)
            
            # Format Indicators as JSON-like string
            ind_str = str(indicators).replace(",", " |").replace("{", "").replace("}", "").replace("'", "")
            
            with open(filename, mode='a', newline='', encoding='utf-8-sig') as file:
                writer = csv.writer(file)
                if not file_exists:
                    writer.writerow(['Time', 'Ticket', 'Strategy', 'Type', 'Price', 'Reason', 'Indicators'])
                
                writer.writerow([
                    datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    ticket,
                    self.strategy_name,
                    signal,
                    price,
                    reason,
                    ind_str
                ])
        except Exception as e:
            logging.error(f"Save Entry Log Error: {e}") 

    def modify_order(self, ticket, sl_price, tp_price):
        """Helper to modify SL/TP of an order"""
        try:
            request = {
                "action": mt5.TRADE_ACTION_SLTP,
                "position": ticket,
                "sl": sl_price,
                "tp": tp_price,
                "magic": self.magic_number,
            }
            result = mt5.order_send(request)
            
            if result.retcode == mt5.TRADE_RETCODE_DONE:
                logging.info(f"\n✨ Order Modified! Ticket: {ticket} -> SL: {sl_price:.2f} | TP: {tp_price:.2f}")
                self.send_telegram_message(
                    f"✨ <b>ORDER MODIFIED</b>\n"
                    f"Ticket: <code>{ticket}</code>\n"
                    f"New SL: <code>{sl_price:.2f}</code>\n"
                    f"New TP: <code>{tp_price:.2f}</code>"
                )
                # Optional: Only notify on significant changes like Break Even
                # Check BE triggers from check_trailing_stop vs current call to notify
                return True
            elif result.retcode == mt5.TRADE_RETCODE_NO_CHANGES:
                return True 
            else:
                logging.warning(f"Failed to modify Order: {result.comment} ({result.retcode})")
                return False
        except Exception as e:
            logging.error(f"Modify Order Error: {e}")
            return False

    def check_trailing_stop(self):
        """Checks and updates Trailing Stop for open positions (My Magic Only)"""
        try:
            positions = mt5.positions_get(symbol=self.symbol)
            if not positions: return

            for pos in positions:
                if pos.magic != self.magic_number: continue # Skip other strategies
                
                ticket = pos.ticket
                order_type = pos.type
                price_open = pos.price_open
                price_current = pos.price_current
                sl = pos.sl
                tp = pos.tp 
                point = mt5.symbol_info(self.symbol).point

                # 1. Break Even (BE) Logic
                if Config.ENABLE_BREAK_EVEN:
                    # 🎯 Calculate dynamic BE trigger (e.g., 40% of TP distance)
                    tp_dist_pts = abs(tp - price_open) / point if tp != 0 else Config.BREAK_EVEN_TRIGGER
                    be_trigger_pts = tp_dist_pts * Config.BREAK_EVEN_PERCENT

                    if order_type == 0: # BUY
                        if (price_current - price_open) / point > be_trigger_pts:
                            target_be = price_open + (Config.BREAK_EVEN_LOCK * point)
                            if sl < (target_be - point): 
                                if self.modify_order(ticket, target_be, tp):
                                    logging.info(f"⚡ Break Even Set! Ticket: {ticket} (Triggered at {be_trigger_pts:.0f} pts)")
                                    self.send_telegram_message(f"⚡ <b>BREAK EVEN SET</b>\nTicket: <code>{ticket}</code>\nSL moved to: <code>{target_be:.2f}</code>")
                                continue 
                                
                    elif order_type == 1: # SELL
                        if (price_open - price_current) / point > be_trigger_pts:
                            target_be = price_open - (Config.BREAK_EVEN_LOCK * point)
                            if sl > (target_be + point) or sl == 0:
                                if self.modify_order(ticket, target_be, tp):
                                    logging.info(f"⚡ Break Even Set! Ticket: {ticket} (Triggered at {be_trigger_pts:.0f} pts)")
                                    self.send_telegram_message(f"⚡ <b>BREAK EVEN SET</b>\nTicket: <code>{ticket}</code>\nSL moved to: <code>{target_be:.2f}</code>")
                                continue

                if Config.ENABLE_PARTIAL_TP and ticket not in self.partially_closed_tickets:
                    current_profit_points = 0
                    if order_type == 0: current_profit_points = (price_current - price_open) / point
                    else: current_profit_points = (price_open - price_current) / point
                    
                    # 🎯 Partial Close Trigger at 1:1 RR (Distance equal to SL)
                    sl_dist_pts = abs(sl - price_open) / point if sl != 0 else Config.STOP_LOSS_POINTS
                    trigger_points = max(sl_dist_pts, 100) # Min 100pts safety
                    
                    if current_profit_points >= trigger_points:
                         if pos.volume >= (Config.MIN_LOT * 2): 
                             vol_to_close = round(pos.volume * Config.PARTIAL_TP_RATIO, 2)
                             if vol_to_close >= Config.MIN_LOT:
                                 logging.info(f"💰 Partial TP Trigger (1:1 RR)! Profit: {current_profit_points:.0f}pts. Closing {vol_to_close} lots...")
                                 if self.close_partial(ticket, vol_to_close):
                                     self.partially_closed_tickets.add(ticket)
                                     # After Partial, ALWAYS set Break Even to protect capital
                                     target_be = price_open + (Config.BREAK_EVEN_LOCK * point) if order_type == 0 else price_open - (Config.BREAK_EVEN_LOCK * point)
                                     if self.modify_order(ticket, target_be, tp):
                                         self.send_telegram_message(f"💰 <b>PARTIAL TP (1:1 RR)</b>\nTicket: <code>{ticket}</code>\nClosed: <code>{vol_to_close}</code> lots\nSL moved to BE.")
                                     continue 

                # 2. Trailing Stop Logic (Dynamic)
                # BUY Order
                if order_type == 0:
                    profit_points = (price_current - price_open) / point
                    if profit_points > Config.TRAILING_STOP_TRIGGER:
                        trailing_dist = Config.TRAILING_STOP_LOCK * point
                        target_sl = price_current - trailing_dist
                        
                        if sl < target_sl and (target_sl - sl) >= (Config.TRAILING_STOP_STEP * point):
                            if self.modify_order(ticket, target_sl, tp):
                                self.send_telegram_message(f"📈 <b>TRAILING SL MOVED (BUY)</b>\nTicket: <code>{ticket}</code>\nNew SL: <code>{target_sl:.2f}</code>")

                    if Config.ENABLE_DYNAMIC_TP:
                        dist_to_tp = (tp - price_current) / point
                        if dist_to_tp <= Config.TP_EXTENSION_TRIGGER and dist_to_tp > 0:
                            new_tp = tp + (Config.TP_EXTENSION_DISTANCE * point)
                            if self.modify_order(ticket, sl, new_tp):
                                logging.info(f"🚀 TP Extended! Ticket: {ticket} | Old TP: {tp} -> New TP: {new_tp}")
                                self.send_telegram_message(f"🚀 <b>TP EXTENDED (BUY)</b>\nTicket: <code>{ticket}</code>\nNew TP: <code>{new_tp:.2f}</code>")

                # SELL Order
                elif order_type == 1:
                    profit_points = (price_open - price_current) / point
                    if profit_points > Config.TRAILING_STOP_TRIGGER:
                        trailing_dist = Config.TRAILING_STOP_LOCK * point
                        target_sl = price_current + trailing_dist
                        
                        if (sl > target_sl or sl == 0) and (sl == 0 or (sl - target_sl) >= (Config.TRAILING_STOP_STEP * point)):
                            if self.modify_order(ticket, target_sl, tp):
                                self.send_telegram_message(f"📉 <b>TRAILING SL MOVED (SELL)</b>\nTicket: <code>{ticket}</code>\nNew SL: <code>{target_sl:.2f}</code>")

                    if Config.ENABLE_DYNAMIC_TP:
                        dist_to_tp = (price_current - tp) / point
                        if dist_to_tp <= Config.TP_EXTENSION_TRIGGER and dist_to_tp > 0:
                            new_tp = tp - (Config.TP_EXTENSION_DISTANCE * point)
                            if self.modify_order(ticket, sl, new_tp):
                                logging.info(f"🚀 TP Extended! Ticket: {ticket} | Old TP: {tp} -> New TP: {new_tp}")
                                self.send_telegram_message(f"🚀 <b>TP EXTENDED (SELL)</b>\nTicket: <code>{ticket}</code>\nNew TP: <code>{new_tp:.2f}</code>")
                            
        except Exception as e:
            logging.error(f"Trailing Stop Error: {e}")

    def get_daily_profit(self):
        """Calculates total profit for the current day (My Strategy Only)"""
        try:
            now = datetime.now()
            # Use dynamic offset for server time window
            server_now = now + timedelta(hours=self.server_time_offset)
            today_start = datetime(server_now.year, server_now.month, server_now.day) - timedelta(hours=self.server_time_offset)
            
            deals = mt5.history_deals_get(today_start, now, group=self.symbol)
            
            total_profit = 0.0
            if deals:
                for deal in deals:
                    # Filter by Magic Number
                    if deal.magic == self.magic_number:
                        if deal.entry in [mt5.DEAL_ENTRY_OUT, mt5.DEAL_ENTRY_INOUT]:
                            total_profit += deal.profit + deal.swap + deal.commission
            
            return total_profit
        except Exception as e:
            logging.error(f"Daily Profit Calc Error: {e}")
            return 0.0

    def get_active_orders_summary(self):
        """Returns a summary string of active orders for this strategy"""
        try:
            positions = mt5.positions_get(symbol=self.symbol)
            if not positions:
                return "No Active Orders"
            
            # Filter by Magic Number
            my_positions = [p for p in positions if p.magic == self.magic_number]
            
            if not my_positions:
                return "No Active Orders"
            
            summary = []
            total_profit = 0.0
            
            for pos in my_positions:
                type_str = "BUY" if pos.type == 0 else "SELL"
                comm = getattr(pos, 'commission', 0.0)
                swap = getattr(pos, 'swap', 0.0)
                profit = pos.profit + swap + comm
                summary.append(f"[{pos.ticket} {type_str} {pos.volume} @ {pos.price_open:.2f} (P/L: ${profit:.2f})]")
                total_profit += profit
            
            return f"Orders: {len(my_positions)} | Total P/L: ${total_profit:.2f} | " + " ".join(summary)
        except Exception as e:
            return "Orders: Error"
            
    def save_trade_history(self):
        """Saves closed trades to CSV file (Backlog) - Prevents Duplicates"""
        try:
            now = datetime.now() 
            # Use dynamic offset (look back 1 day with buffer)
            today_start = datetime(now.year, now.month, now.day) - timedelta(days=1)
            deals = mt5.history_deals_get(today_start, now + timedelta(hours=1)) # Buffer for safety
            
            if not deals:
                return

            data_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data')
            if not os.path.exists(data_dir):
                os.makedirs(data_dir)

            filename = os.path.join(data_dir, 'trade_history.csv')
            file_exists = os.path.isfile(filename)
            existing_tickets = set()

            if file_exists:
                try:
                    with open(filename, mode='r', encoding='utf-8') as r_file:
                        reader = csv.reader(r_file)
                        next(reader, None) 
                        for row in reader:
                            if row:
                                existing_tickets.add(int(row[1])) 
                except Exception as e:
                    logging.error(f"Read CSV Error: {e}")

            new_deals = []
            for deal in deals:
                if deal.symbol == self.symbol and deal.entry == mt5.DEAL_ENTRY_OUT and deal.ticket not in existing_tickets:
                    # Filter: Only save MY deals (to prevent double logging race condition)
                    if deal.magic == self.magic_number:
                        new_deals.append(deal)

            if new_deals:
                with open(filename, mode='a', newline='', encoding='utf-8') as file:
                    writer = csv.writer(file)
                    
                    if not file_exists:
                        writer.writerow(['Time', 'Ticket', 'Strategy', 'Type', 'Volume', 'Price', 'Profit', 'Comment', 'Status'])
                    
                    for deal in new_deals:
                        deal_time = datetime.fromtimestamp(deal.time).strftime('%Y-%m-%d %H:%M:%S')
                        deal_type = "BUY" if deal.type == 0 else "SELL"
                        
                        # Extract Strategy from Comment (Format: "Bot STRATEGY_NAME")
                        strategy_used = "Unknown"
                        if deal.comment and deal.comment.startswith("Bot "):
                            strategy_used = deal.comment.replace("Bot ", "").strip()
                        elif deal.comment:
                             strategy_used = deal.comment
                        
                        status = "UNKNOWN"
                        if deal.reason == mt5.DEAL_REASON_TP:
                            status = "TP Hit 🎯"
                        elif deal.reason == mt5.DEAL_REASON_SL:
                            if deal.profit >= 0:
                                status = "Trailing SL/BE 🛡️"
                            else:
                                status = "SL Hit 🔴"
                        elif deal.reason == mt5.DEAL_REASON_CLIENT:
                            status = "Manual Close 👤"
                        elif deal.reason == mt5.DEAL_REASON_EXPERT:
                            status = "Bot Close 🤖"

                        # Telegram Notification for Closed Deal
                        self.send_telegram_message(
                            f"🏁 <b>ORDER CLOSED</b>\n"
                            f"Ticket: <code>{deal.ticket}</code>\n"
                            f"Type: <code>{deal_type}</code>\n"
                            f"Profit: <code>${deal.profit + deal.swap + deal.commission:.2f}</code>\n"
                            f"Status: <b>{status}</b>"
                        )
                        
                        writer.writerow([
                            deal_time, 
                            deal.ticket, 
                            strategy_used,
                            deal_type, 
                            deal.volume, 
                            deal.price, 
                            deal.profit, 
                            deal.comment,
                            status
                        ])
                        logging.info(f"\n📝 History Saved: Ticket {deal.ticket} ({status}) | P/L: ${deal.profit:.2f} | Strat: {strategy_used}")

        except Exception as e:
            logging.error(f"Save History Error: {e}")

    def run(self):
        """Main Loop"""
        if not self.connect_mt5():
            return

        # Header (Static)
        print(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - INFO - ✅ Connected to MT5: {self.symbol}")
        print(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - INFO - 🤖 Bot Started [Strategy: {self.strategy_name}]")
        print(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - INFO - ⚡ Mode: {'Realtime (Risk Repaint) 🚀' if Config.USE_REALTIME_CANDLE else 'Closed Candle (Safe) 🛡️'}")
        print(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - INFO - Press Ctrl+C to stop")
        
        last_log_time = 0.0
        
        while True:
            try:
                # 0. Auto-Reconnect
                terminal_info = mt5.terminal_info()
                if terminal_info is None or not terminal_info.connected:
                    logging.warning("Connection lost, attempting to reconnect...")
                    reconnect_attempts = 0
                    while reconnect_attempts < 5:
                        if self.connect_mt5():
                            logging.info("Reconnected successfully")
                            break
                        reconnect_attempts += 1
                        wait_time = min(pow(2, reconnect_attempts), 30)
                        logging.info(f"Reconnect attempt {reconnect_attempts} failed. Retrying in {wait_time}s...")
                        time.sleep(wait_time)
                    
                    if not self.connected:
                        logging.error("Failed to reconnect after multiple attempts. Waiting 60s...")
                        time.sleep(60)
                        continue

                # 1. Daily Target Check
                daily_profit = self.get_daily_profit()
                if daily_profit >= Config.DAILY_PROFIT_TARGET:
                     msg = f"💰 Daily Target Reached! (${daily_profit:.2f} / ${Config.DAILY_PROFIT_TARGET})"
                     logging.info(msg)
                     self.send_telegram_message(f"🏆 <b>GOAL REACHED</b>\n{msg}\n<i>Sleeping until tomorrow...</i>")
                     logging.info("Sleeping until tomorrow...")
                     time.sleep(3600) 
                     continue

                # 2. Time Filter (Done in strategy but we check here for global sleep? Strategy handles it.)
                # Strategy logic handles forbidden hours/sleep mode signal.

                # 3. Trailing Stop & History Log
                self.check_trailing_stop()
                self.save_trade_history()
                
                # Cleanup partially_closed_tickets
                if self.partially_closed_tickets:
                    open_pos = mt5.positions_get(symbol=self.symbol)
                    if open_pos:
                        current_tickets = {p.ticket for p in open_pos}
                        self.partially_closed_tickets = {t for t in self.partially_closed_tickets if t in current_tickets}
                    else:
                        self.partially_closed_tickets.clear()

                # 4. Get Data & Signal
                # --- NEWS FILTER ---
                if Config.NEWS_FILTER_ENABLED:
                    is_news, news_title = self.news_manager.is_news_time(Config.NEWS_AVOID_MINUTES)
                    if is_news:
                        logging.warning(f"🚫 PAUSED: High Impact News ({news_title}) - Skipping Analysis")
                        time.sleep(60)
                        continue

                df = self.get_market_data()
                if df is not None:
                    signal, status_detail, extra_data = self.strategy.analyze(df)
                    
                    price = extra_data.get('price', 0)
                    atr = extra_data.get('atr', 0)
                    custom_sl = extra_data.get('custom_sl', 0.0)
                    
                    # 🖥️ DISPLAY LOGIC
                    current_time = time.time()
                    if current_time - last_log_time >= 60: # Log every minute
                        print(f"[{datetime.now().strftime('%H:%M')}] {status_detail} | Price: {price}")
                        last_log_time = current_time

                    if signal in ["BUY", "SELL"]:
                        # 🛡️ ONE TRADE PER CANDLE GUARD
                        current_candle_time = df.iloc[-1]['time']
                        if self.last_trade_candle_time == current_candle_time:
                            # Already traded this candle, skip re-entry
                            pass
                        else:
                            # Prepare Indicators for Log (Filter out large objects like filtered arrays)
                            log_indicators = {k: v for k, v in extra_data.items() if isinstance(v, (int, float, str))}
                            
                            self.execute_trade(
                                signal=signal, 
                                reason=status_detail, 
                                indicators=log_indicators,
                                atr=atr, 
                                custom_sl=custom_sl,
                                candle_time=current_candle_time
                            )
                        # Get Active Orders
                        orders_summary = self.get_active_orders_summary()
                        if orders_summary == "No Active Orders":
                            ord_str = "|| No Orders"
                        else:
                            parts = orders_summary.split('|')
                            if len(parts) > 2:
                                    ord_str = f"|| {parts[0].strip()} | {parts[1].strip()}"
                            else:
                                    ord_str = f"|| {orders_summary}"

                        # Single Line Construction
                        line = f"{datetime.now().strftime('%H:%M:%S')} {status_detail} {ord_str}"
                        
                        terminal_width = shutil.get_terminal_size().columns
                        max_len = max(50, terminal_width - 5) 
                        
                        if len(line) > max_len:
                            line = line[:max_len-3] + "..."
                            
                        blank_line = " " * (terminal_width - 1)
                        sys.stdout.write(f"\r{blank_line}\r{line}")
                        sys.stdout.flush()

                        if signal in ["BUY", "SELL"]:
                             # Removed redundant execution
                             last_log_time = 0                   
                time.sleep(1 if Config.USE_REALTIME_CANDLE else 15)
                
            except KeyboardInterrupt:
                print("\n🛑 Bot stopped by user")
                mt5.shutdown()
                break
            except Exception as e:
                logging.error(f"\nMain Loop Error: {e}")
                time.sleep(5)
