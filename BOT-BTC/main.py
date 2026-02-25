import time
import logging
import os
import csv
import pandas as pd
from datetime import datetime

import MetaTrader5 as mt5
from .execution import MT5Executor
from .logic import TradingLogic
from utils.indicators import Indicators

from . import config
from utils.news_manager import NewsManager


logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)-8s | %(message)s',
    datefmt='%H:%M:%S'
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

def save_entry_log(ticket, type, price, rsi, ema):
    """Saves trade entry details to CSV for analysis"""
    try:
        data_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data')
        if not os.path.exists(data_dir):
            os.makedirs(data_dir)
            
        file_path = os.path.join(data_dir, 'entry_log.csv')
        file_exists = os.path.isfile(file_path)
        with open(file_path, mode='a', newline='', encoding='utf-8-sig') as file:
            writer = csv.writer(file)
            if not file_exists:
                writer.writerow(['Time', 'Ticket', 'Strategy', 'Type', 'Price', 'Reason', 'Indicators'])
            
            writer.writerow([
                datetime.now().strftime('%Y-%m-%d %H:%M:%S'), 
                ticket, 
                "BTC_RSI_EMA", 
                type, 
                price, 
                "Signal Confirmed", 
                f"RSI:{rsi:.1f} EMA:{ema:.1f}"
            ])

    except Exception as e:
        logging.error(f"Error saving entry log: {e}")

def sync_trade_history():
    """Syncs BTC closed trades from MT5 history to the main unified CSV"""
    try:
        from datetime import datetime, timedelta
        now = datetime.now()
        # Look back 30 days
        today_start = datetime(now.year, now.month, now.day) - timedelta(days=30)
        deals = mt5.history_deals_get(today_start, now + timedelta(hours=1))
        
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
                        if row and len(row) > 1:
                            try:
                                existing_tickets.add(int(row[1]))
                            except ValueError:
                                continue
            except Exception as e:
                logging.error(f"Read CSV Error: {e}")

        new_deals = []
        for deal in deals:
            if deal.symbol == config.SYMBOL and deal.entry == mt5.DEAL_ENTRY_OUT and deal.ticket not in existing_tickets:
                if deal.magic == config.MAGIC_NUMBER:
                    new_deals.append(deal)

        if new_deals:
            with open(filename, mode='a', newline='', encoding='utf-8') as file:
                writer = csv.writer(file)
                if not file_exists:
                    writer.writerow(['Time', 'Ticket', 'Strategy', 'Type', 'Volume', 'Price', 'Profit', 'Comment', 'Status'])
                
                for deal in new_deals:
                    deal_time = datetime.fromtimestamp(deal.time).strftime('%Y-%m-%d %H:%M:%S')
                    deal_type = "BUY" if deal.type == 0 else "SELL"
                    
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

                    total_profit = deal.profit + deal.swap + deal.commission
                    send_notification(
                        f"🏁 BTC ORDER CLOSED\n"
                        f"Ticket: {deal.ticket}\n"
                        f"Type: {deal_type}\n"
                        f"Profit: ${total_profit:.2f}\n"
                        f"Status: {status}"
                    )
                    
                    writer.writerow([
                        deal_time, 
                        deal.ticket, 
                        "BTC_RSI_EMA", 
                        deal_type, 
                        deal.volume, 
                        deal.price, 
                        round(total_profit, 2), 
                        deal.comment,
                        status
                    ])
                    logging.info(f"📝 History Synced: BTC Ticket {deal.ticket} ({status}) | P/L: ${total_profit:.2f}")

    except Exception as e:
        logging.error(f"Sync History Error: {e}")

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
        
    # --- CALCULATE SERVER TIME OFFSET ---
    # Ensures we are synced with Broker's clock for News & Candles
    server_time_offset = 0
    try:
        symbol_info = mt5.symbol_info_tick(config.SYMBOL)
        if symbol_info:
            server_time = symbol_info.time
            local_time = int(time.time())
            server_time_offset = round((server_time - local_time) / 3600)
            logging.info(f"🕒 Server Time Offset: {server_time_offset} hours")
    except Exception as e:
        logging.warning(f"Failed to calculate time offset: {e}")

    logic = TradingLogic(executor)
    news_manager = NewsManager() # Initialize once
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
    except Exception as e:
        logging.debug(f"Startup report error: {e}")

    while True:
        try:
            # 0. Auto-Reconnect logic (Enhanced)
            terminal_info = mt5.terminal_info()
            if terminal_info is None or not terminal_info.connected:

                logging.warning("⚠️ Connection lost, attempting to reconnect...")
                reconnect_attempts = 0
                while reconnect_attempts < 5:
                    if executor.connect():
                        logging.info("✅ Rebalanced & Reconnected successfully")
                        break
                    reconnect_attempts += 1
                    wait_time = min(pow(2, reconnect_attempts), 30)
                    logging.info(f"Retry {reconnect_attempts} in {wait_time}s...")
                    time.sleep(wait_time)
                
                if not mt5.terminal_info().connected:
                    logging.error("Failed to recover. Waiting 60s...")
                    time.sleep(60)
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
            df['close'] = pd.to_numeric(df['close'])
            df['high'] = pd.to_numeric(df['high'])
            df['low'] = pd.to_numeric(df['low'])
            
            df['ema_trend'] = Indicators.calculate_ema(df['close'], config.EMA_TREND_PERIOD)
            df['ema_exit'] = Indicators.calculate_ema(df['close'], config.EMA_EXIT_PERIOD)
            df['rsi'] = Indicators.calculate_rsi(df['close'], config.RSI_PERIOD)

            
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
            
            # --- NEWS FILTER CHECK ---
            is_news, news_title = news_manager.is_news_time(avoid_minutes=30)

            
            # Use Tick Prices for execution
            is_new_candle = (current_candle_time > last_candle_time) if last_candle_time else True

            if signal and not in_position:
                if is_news:
                    logging.warning(f"⚠️ Skipping trade due to HIGH IMPACT NEWS: {news_title}")
                elif config.WAIT_FOR_CANDLE_CLOSE and not is_new_candle:
                    # Waiting for current candle to finish
                    pass
                else:
                    order_type = mt5.ORDER_TYPE_BUY if signal == 'buy' else mt5.ORDER_TYPE_SELL
                    price_exec = tick.ask if signal == 'buy' else tick.bid
                    sl_price, tp_price = logic.get_sl_tp(df, signal, price_exec)
                    
                    # --- MARGIN CHECK ---
                    can_trade, reason = executor.check_margin(config.SYMBOL, order_type, config.LOT_SIZE, price_exec)
                    if not can_trade:
                        logging.error(f"❌ Margin Check Failed: {reason}")
                        acc_info = mt5.account_info()
                        balance = acc_info.balance if acc_info else "N/A"
                        send_notification(f"⚠️ เงินไม่พอเปิดออเดอร์!\nBalance: {balance}\nRequired: {reason}")
                        # Sleep for a bit to avoid terminal spamming
                        time.sleep(300)
                        continue
 
                    # --- SPREAD FILTER ---
                    spread = (tick.ask - tick.bid) / mt5.symbol_info(config.SYMBOL).point
                    if spread > config.MAX_SPREAD_POINTS:
                        logging.warning(f"⚠️ High Spread: {spread} points. Skipping entry.")
                        continue

                    side_str = "BUY" if signal == 'buy' else "SELL"
                    logging.info(f"🟢 Signal {side_str} | Price: {price_exec} | SL: {sl_price} | TP: {tp_price} | News: {news_title}")
                    res = executor.create_order(config.SYMBOL, order_type, config.LOT_SIZE, price_exec, sl=sl_price, tp=tp_price)
                    if res:
                        last_candle_time = current_candle_time 
                        save_entry_log(res.order, side_str, price_exec, last_row['rsi'], last_row['ema_trend'])
                        send_notification(f"✅ {side_str} BTC SUCCESS\nPrice: {price_exec}\nSL: {sl_price}\nTP: {tp_price}")

            
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
                    
                    # --- NEW PROFIT PROTECTION LOGIC (2 STAGES) ---
                    tp_dist_pts = abs(pos.tp - pos.price_open) / point if pos.tp != 0 else config.STOP_LOSS_POINTS * config.RISK_REWARD_RATIO
                    
                    # Stage 1: Break Even (40% of TP)
                    if config.ENABLE_BREAK_EVEN:
                        be_trigger_pts = tp_dist_pts * config.BE_PERCENT
                        if profit_points >= be_trigger_pts:
                            target_be = pos.price_open + (config.BE_LOCK_POINTS * point) if pos.type == mt5.ORDER_TYPE_BUY else pos.price_open - (config.BE_LOCK_POINTS * point)
                            
                            # Move SL only if it improves the position
                            if pos.type == mt5.ORDER_TYPE_BUY:
                                if pos.sl < (target_be - point):
                                    logging.info(f"🛡️ Stage 1: BE Set (+100) for BTC Ticket {pos.ticket}")
                                    executor.modify_position(pos.ticket, target_be, pos.tp)
                            else: # SELL
                                if pos.sl > (target_be + point) or pos.sl == 0:
                                    logging.info(f"🛡️ Stage 1: BE Set (+100) for BTC Ticket {pos.ticket}")
                                    executor.modify_position(pos.ticket, target_be, pos.tp)

                    # Stage 2: Profit Lock (65% of TP)
                    if config.ENABLE_PROFIT_LOCK:
                        pl_trigger_pts = tp_dist_pts * config.PROFIT_LOCK_PERCENT
                        if profit_points >= pl_trigger_pts:
                            # Target SL is 50% of original TP distance
                            target_lock = pos.price_open + (tp_dist_pts * config.PROFIT_LOCK_LEVEL * point) if pos.type == mt5.ORDER_TYPE_BUY else pos.price_open - (tp_dist_pts * config.PROFIT_LOCK_LEVEL * point)
                            
                            # Move SL only if it improves the position
                            if pos.type == mt5.ORDER_TYPE_BUY:
                                if pos.sl < (target_lock - point):
                                    logging.info(f"🔒 Stage 2: Profit Lock (50%) for BTC Ticket {pos.ticket}")
                                    executor.modify_position(pos.ticket, target_lock, pos.tp)
                            else: # SELL
                                if pos.sl > (target_lock + point) or pos.sl == 0:
                                    logging.info(f"🔒 Stage 2: Profit Lock (50%) for BTC Ticket {pos.ticket}")
                                    executor.modify_position(pos.ticket, target_lock, pos.tp)

                    # 3. Partial Take Profit
                    if config.ENABLE_PARTIAL_TP:
                        # Calculate risk in points (initial SL distance)
                        risk_pts = abs(pos.price_open - pos.sl) / point if pos.sl > 0 else config.STOP_LOSS_POINTS
                        target_pts = risk_pts * config.PARTIAL_TP_RR
                        
                        # Only partial close if profit reaches target RR and volume is still original
                        # (We check comment or volume to ensure we don't partial close multiple times)
                        if profit_points >= target_pts and pos.volume >= config.LOT_SIZE:
                            # Verify if we can actually split this lot
                            if pos.volume >= (sym_info.volume_min * 2):
                                partial_vol = round(pos.volume * config.PARTIAL_TP_RATIO, 2)
                                logging.info(f"💰 Partial TP Triggered for {pos.ticket} | Closing {partial_vol} lots")
                                res_p = executor.close_position(pos, volume=partial_vol)
                                if res_p:
                                    send_notification(f"💰 PARTIAL TP SUCCESS (Ticket {pos.ticket})\nClosed: {partial_vol}\nRemaining: {pos.volume - partial_vol}")
                            else:
                                # Lot too small to split, skip but log once
                                logging.debug(f"Skip Partial TP for {pos.ticket}: Volume {pos.volume} too small to split.")

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


            # Sync history and Heartbeat Logging
            sync_trade_history()
            if iteration_count % 6 == 0:
                logging.info(f"💓 Heartbeat | RSI: {last_row['rsi']:.1f} | EMA200: {last_row['ema_trend']:.1f} | Price: {tick.bid:.2f}")
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
