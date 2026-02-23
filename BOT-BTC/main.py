import time
import logging
import os
import csv
from datetime import datetime
import MetaTrader5 as mt5
from .execution import MT5Executor
from .logic import TradingLogic
from .indicators import IndicatorCalculator
from . import config

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def send_notification(message):
    """Sends notification via Telegram and Line Notify"""
    logging.info(f"Notification: {message}")
    if config.TELEGRAM_BOT_TOKEN and config.TELEGRAM_CHAT_ID:
        try:
            import requests
            url = f"https://api.telegram.org/bot{config.TELEGRAM_BOT_TOKEN}/sendMessage"
            res = requests.post(url, data={"chat_id": config.TELEGRAM_CHAT_ID, "text": message}, timeout=10)
            res.raise_for_status()
        except Exception as e:
            logging.error(f"Telegram notification failed: {e}")
    if config.LINE_NOTIFY_TOKEN:
        try:
            import requests
            headers = {"Authorization": f"Bearer {config.LINE_NOTIFY_TOKEN}"}
            res = requests.post("https://notify-api.line.me/api/notify", headers=headers, data={"message": message}, timeout=10)
            res.raise_for_status()
        except Exception as e:
            logging.error(f"Line Notify failed: {e}")

def save_trade_log(ticket, type, price, rsi, ema):
    """Saves trade entry details to CSV for analysis"""
    try:
        file_path = "btc_trade_log.csv"
        file_exists = os.path.isfile(file_path)
        with open(file_path, mode='a', newline='') as file:
            writer = csv.writer(file)
            if not file_exists:
                writer.writerow(['Time', 'Ticket', 'Type', 'Price', 'RSI', 'EMA200'])
            writer.writerow([datetime.now().strftime('%Y-%m-%d %H:%M:%S'), ticket, type, price, rsi, ema])
    except PermissionError:
        logging.error(f"❌ Cannot save log: {file_path} is open in another program (Excel?).")
    except Exception as e:
        logging.error(f"Error saving log: {e}")

def get_daily_pnl():
    """Calculates total profit/loss for today from closed deals"""
    try:
        from datetime import datetime, time as dt_time
        today_start = datetime.combine(datetime.now(), dt_time.min)
        deals = mt5.history_deals_get(today_start, datetime.now())
        if deals is None:
            return 0.0
        
        total_pnl = sum([d.profit + d.commission + d.swap for d in deals if d.magic == config.MAGIC_NUMBER])
        return total_pnl
    except Exception as e:
        logging.error(f"Error calculating Daily PnL: {e}")
        return 0.0

def main():
    logging.info("🚀 Starting BTC Trading Bot (MT5 Edition)")
    
    executor = MT5Executor()
    if not executor.connect():
        return
        
    logic = TradingLogic(executor)
    last_candle_time = None
    iteration_count = 0
    last_heartbeat_time = 0 # Unix timestamp

    # --- STARTUP REPORT ---
    try:
        acc = mt5.account_info()
        sym = mt5.symbol_info(config.SYMBOL)
        if acc and sym:
            logging.info("="*40)
            logging.info(f"💰 Account: {acc.login} | Balance: {acc.balance} {acc.currency}")
            logging.info(f"📊 Symbol: {sym.name} | Digits: {sym.digits} | Min Lot: {sym.volume_min}")
            logging.info(f"🛡️ Risk: Lot={config.LOT_SIZE} | SL={config.STOP_LOSS_POINTS} pts")
            logging.info("="*40)
            if config.LOT_SIZE < sym.volume_min:
                logging.warning(f"⚠️ Warning: LOT_SIZE {config.LOT_SIZE} is less than Min Lot {sym.volume_min}!")
    except: pass
    
    while True:
        try:
            # 0. Auto-Reconnect logic
            if not executor.is_connected():
                logging.warning("⚠️ MT5 Disconnected! Re-initializing...")
                if executor.connect():
                    logging.info("✅ Re-connected to MT5.")
                else:
                    time.sleep(5)
                    continue

            # --- DAILY LOSS LIMIT ---
            daily_pnl = get_daily_pnl()
            limit = float(config.DAILY_LOSS_LIMIT)
            if daily_pnl <= -limit:
                logging.error(f"🛑 Emergency Stop: Daily Loss Limit Reached ({daily_pnl})")
                send_notification(f"🛑 Emergency Stop!\nDaily Loss Limit Reached: {daily_pnl}\nTrading suspended until tomorrow.")
                # Sleep until next day
                time.sleep(3600)
                continue

            # --- STATUS HEARTBEAT (TELEGRAM) ---
            now_ts = time.time()
            heartbeat_interval = getattr(config, 'HEARTBEAT_HOURS', 1) * 3600
            if now_ts - last_heartbeat_time >= heartbeat_interval:
                acc = mt5.account_info()
                balance = acc.balance if acc else 'N/A'
                msg = f"💓 Heartbeat Status\nBalance: {balance}\nDaily PnL: {daily_pnl:.2f}\nBot is running normally."
                send_notification(msg)
                last_heartbeat_time = now_ts

            # 1. Fetch Market Data
            df = executor.fetch_ohlcv(config.SYMBOL, config.TIMEFRAME, 300)
            if df is None:
                time.sleep(10)
                continue
                
            # 2. Calculate Indicators
            df = IndicatorCalculator.add_indicators(df)
            
            # --- FETCH CURRENT TICK ---
            tick = mt5.symbol_info_tick(config.SYMBOL)
            if tick is None:
                logging.error(f"Failed to get tick for {config.SYMBOL}")
                time.sleep(10)
                continue

            # --- CANDLE SYNC LOGIC ---
            current_candle_time = df.iloc[-1]['time']
            if config.WAIT_FOR_CANDLE_CLOSE:
                if last_candle_time is None:
                    last_candle_time = current_candle_time
                    logging.info(f"⏳ Syncing with candle: {current_candle_time}")
                    time.sleep(10)
                    continue
                
                if current_candle_time <= last_candle_time:
                    # Still on the same candle, skip entry check
                    # But we still want to run protecting logic below
                    pass 
                else:
                    # New candle opened! Signal check allowed
                    pass

            # 3. Handle Positions
            active_positions = executor.get_active_positions()
            in_position = len(active_positions) > 0
            
            last_row = df.iloc[-1]
            price = last_row['close']
            
            # 4. Signal Logic & Execution
            signal = logic.check_signal(df)
            
            # Use Tick Prices for execution
            is_new_candle = (current_candle_time > last_candle_time) if last_candle_time else True

            if signal and not in_position:
                if config.WAIT_FOR_CANDLE_CLOSE and not is_new_candle:
                    # Waiting for current candle to finish
                    pass
                else:
                    order_type = mt5.ORDER_TYPE_BUY if signal == 'buy' else mt5.ORDER_TYPE_SELL
                    price_exec = tick.ask if signal == 'buy' else tick.bid
                    sl_price = logic.get_stop_loss(df, signal, price_exec)
                    
                    # --- MARGIN CHECK ---
                    can_trade, reason = executor.check_margin(config.SYMBOL, order_type, config.LOT_SIZE, price_exec)
                    if not can_trade:
                        logging.error(f"❌ Margin Check Failed: {reason}")
                        send_notification(f"⚠️ บัญชีมีเงินไม่พอเปิดออเดอร์!\nต้องการ: {reason}")
                        time.sleep(3600)
                        continue

                    # --- SPREAD FILTER ---
                    spread = (tick.ask - tick.bid) / mt5.symbol_info(config.SYMBOL).point
                    if spread > config.MAX_SPREAD_POINTS:
                        logging.warning(f"⚠️ High Spread: {spread} points. Skipping entry.")
                        continue

                    side_str = "BUY" if signal == 'buy' else "SELL"
                    logging.info(f"🟢 Signal {side_str} | Price: {price_exec} | SL: {sl_price} | Spread: {spread}")
                    res = executor.create_order(config.SYMBOL, order_type, config.LOT_SIZE, price_exec, sl=sl_price)
                    if res:
                        last_candle_time = current_candle_time 
                        save_trade_log(res.order, side_str, price_exec, last_row['rsi'], last_row['ema_trend'])
                        send_notification(f"✅ {side_str} BTC SUCCESS\nPrice: {price_exec}\nSL: {sl_price}")
            
            elif in_position:
                for pos in active_positions:
                    # --- PROTECTIVE LOGIC (BE/TS) ---
                    sym_info = mt5.symbol_info(config.SYMBOL)
                    if sym_info is None: continue
                    point = sym_info.point
                    
                    # Calculate profit in points
                    if pos.type == mt5.ORDER_TYPE_BUY:
                        profit_points = (tick.bid - pos.price_open) / point
                    elif pos.type == mt5.ORDER_TYPE_SELL:
                        profit_points = (pos.price_open - tick.ask) / point
                    else: continue
                    
                    # 1. Break Even
                    if config.ENABLE_BREAK_EVEN and profit_points > config.BE_TRIGGER_POINTS:
                        if pos.type == mt5.ORDER_TYPE_BUY:
                            target_be = pos.price_open + (config.BE_LOCK_POINTS * point)
                            if pos.sl < target_be or pos.sl == 0:
                                logging.info(f"🛡️ Break Even Triggered (BUY) for {pos.ticket}")
                                executor.modify_position(pos.ticket, target_be, pos.tp)
                        elif pos.type == mt5.ORDER_TYPE_SELL:
                            target_be = pos.price_open - (config.BE_LOCK_POINTS * point)
                            if pos.sl > target_be or pos.sl == 0:
                                logging.info(f"🛡️ Break Even Triggered (SELL) for {pos.ticket}")
                                executor.modify_position(pos.ticket, target_be, pos.tp)
                    
                    # 2. Trailing Stop
                    if config.ENABLE_TRAILING_STOP and profit_points > config.TS_TRIGGER_POINTS:
                        if pos.type == mt5.ORDER_TYPE_BUY:
                            new_sl = tick.bid - (config.TS_TRIGGER_POINTS * point)
                            if pos.sl == 0 or (new_sl - pos.sl) / point > config.TS_STEP_POINTS:
                                logging.info(f"📈 Trailing Stop moving (BUY) for {pos.ticket}")
                                executor.modify_position(pos.ticket, new_sl, pos.tp)
                        elif pos.type == mt5.ORDER_TYPE_SELL:
                            new_sl = tick.ask + (config.TS_TRIGGER_POINTS * point)
                            if pos.sl == 0 or (pos.sl - new_sl) / point > config.TS_STEP_POINTS:
                                logging.info(f"📈 Trailing Stop moving (SELL) for {pos.ticket}")
                                executor.modify_position(pos.ticket, new_sl, pos.tp)

                    # Exit Condition (Long): RSI Overbought or price below EMA 20
                    # Exit Condition (Short): RSI Oversold or price above EMA 20
                    should_exit = False
                    if pos.type == mt5.ORDER_TYPE_BUY:
                        if last_row['rsi'] > config.RSI_OVERBOUGHT or last_row['close'] < last_row['ema_exit']:
                            should_exit = True
                    elif pos.type == mt5.ORDER_TYPE_SELL:
                        if last_row['rsi'] < config.RSI_OVERSOLD or last_row['close'] > last_row['ema_exit']:
                            should_exit = True

                    if should_exit:
                        logging.info(f"🔴 Signal EXIT for Ticket {pos.ticket} | Closing Position...")
                        res = executor.close_position(pos)
                        if res:
                            send_notification(f"✅ EXIT SUCCESS (Ticket {pos.ticket})\nPrice: {price}")

            # Heartbeat Logging (every 1 minute / 6 iterations)
            if iteration_count % 6 == 0:
                logging.info(f"💓 Heartbeat | RSI: {last_row['rsi']:.2f} | EMA200: {last_row['ema_trend']:.2f} | Price: {tick.bid}")
            iteration_count += 1

            time.sleep(10) # Check every 10 seconds
            
        except KeyboardInterrupt:
            logging.info("👋 Bot stopped by user. Shutting down...")
            mt5.shutdown()
            break
        except Exception as e:
            logging.error(f"Error: {e}")
            time.sleep(10)

if __name__ == "__main__":
    main()
