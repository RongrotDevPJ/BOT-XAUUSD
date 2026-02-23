from .base import BaseStrategy
from config.settings import Config
from utils.indicators import Indicators
from datetime import datetime

class OBFVGFiboStrategy(BaseStrategy):
    def __init__(self, bot_instance):
        self.bot = bot_instance

    def analyze(self, df):
        if df is None: return "WAIT", "No Data", {}
        
        # Select Candle
        row_index = -1 if Config.USE_REALTIME_CANDLE else -2
        prev_row = df.iloc[row_index]
        price = prev_row['close']
        atr = prev_row['atr']
        rsi = prev_row['rsi']
        
        # --- TIME FILTER (KILL ZONES) ---
        server_time = self.bot.get_server_time()
        current_hour = server_time.hour
        is_kill_zone = Config.TRADING_START_HOUR <= current_hour <= Config.TRADING_END_HOUR
        
        if not is_kill_zone:
            return "WAIT", f"Outside Kill Zone ({Config.TRADING_START_HOUR}:00-{Config.TRADING_END_HOUR}:00) | Server Time: {server_time.strftime('%H:%M')}", {}
        
        # 1. Indicators & Patterns
        smc_lookback = self.bot.get_setting('SMC_LOOKBACK') if self.bot.get_setting('SMC_LOOKBACK') else Config.SMC_LOOKBACK
        max_sl_points = self.bot.get_setting('MAX_SL_POINTS')
        
        bull_ob, bear_ob = Indicators.calculate_order_blocks(
            df, 
            lookback=smc_lookback, 
            max_sl_points=max_sl_points
        )
        bull_fvg, bear_fvg = Indicators.calculate_fvg(df, lookback=20)
        
        # 2. Advanced SMC Utils
        swings = Indicators.identify_swing_points(df)
        mss = Indicators.check_mss(df, swings) 
        
        # Trend & IDM
        mtf_trend = self.bot.get_mtf_trend()
        ema_trend = prev_row['ema_trend'] 
        trend_dir = "UP" if price > ema_trend else "DOWN"
        
        if mss == "BULL_MSS": trend_dir = "UP"
        elif mss == "BEAR_MSS": trend_dir = "DOWN"
        
        has_idm_sweep = Indicators.check_inducement_sweep(df, swings, trend_dir)
        
        # Premium/Discount
        high, low = Indicators.get_swing_high_low(df, lookback=50)
        fibo_levels = {}
        is_discount = False
        is_premium = False
        mid_point = 0
        
        if high and low and high != low:
             fibo_levels = Indicators.calculate_fibonacci_levels(high, low, trend_dir)
             mid_point = (high + low) / 2
             is_discount = price < mid_point
             is_premium = price > mid_point
        
        signal = "WAIT"
        status_detail = "WAIT"
        
        # Match Checks
        is_ob_match = False
        is_fvg_match = False
        is_fibo_match = False
        match_type = "None"
        
        # Note: bull_ob/bear_ob are already filtered for MITIGATION in Indicators.py now.
        
        # --- Dynamic TP Targets (Liquidity Pools) ---
        # Buy Target = Recent Swing High
        # Sell Target = Recent Swing Low
        tp_target = 0.0
        
        if Config.ENABLE_DYNAMIC_TP_SMC:
            if trend_dir == "UP":
                 # Find nearest Swing High above price
                 recent_highs = [s['price'] for s in swings if s['type'] == 'HIGH' and s['price'] > price]
                 if recent_highs: tp_target = min(recent_highs) # Nearest Liquidity
                 else: tp_target = high # Fallback to Range High
            else:
                 # Find nearest Swing Low below price
                 recent_lows = [s['price'] for s in swings if s['type'] == 'LOW' and s['price'] < price]
                 if recent_lows: tp_target = max(recent_lows) # Nearest Liquidity
                 else: tp_target = low # Fallback to Range Low

        # --- BUY LOGIC ---
        if bull_ob:
            ob_high, ob_low = bull_ob
            support_valid = price >= (ob_low - atr*0.1) 
            is_near_zone = price <= (ob_high + atr*0.5)
            if support_valid and is_near_zone:
                is_ob_match = True
        
        for fvg_low, fvg_high in bull_fvg:
             gap_top = max(fvg_low, fvg_high)
             gap_bottom = min(fvg_low, fvg_high)
             if gap_bottom <= price <= gap_top:
                 is_fvg_match = True
                 break

        if fibo_levels and trend_dir == "UP":
            l618 = fibo_levels.get(0.618, 0)
            l786 = fibo_levels.get(0.786, 0)
            if l786 <= price <= (l618 + atr*0.2):
                is_fibo_match = True
        
        # Buyer Confirmation
        pattern = Indicators.check_candlestick_pattern(df, index=row_index)
        candlestick_conf = pattern in ["BULLISH_ENGULFING", "BULLISH_PINBAR"]
        smc_conf = has_idm_sweep or (mss == "BULL_MSS")
        
        calculated_sl = 0.0
        calculated_tp = 0.0

        if is_ob_match or is_fvg_match or is_fibo_match:
             match_type = "Setup Found"
             if is_ob_match: match_type = "OB"
             if is_fibo_match and is_ob_match: match_type = "Golden"
             
             if is_discount:
                  is_golden_zone = is_ob_match and is_fibo_match
                  
                  if (candlestick_conf and smc_conf) or (is_golden_zone and smc_conf):
                    if not self.bot.check_open_positions():
                        signal = "BUY"
                        if is_golden_zone and not candlestick_conf:
                            why = "Golden Setup"
                        else:
                            why = f"{pattern}"
                        status_detail = f"🚀 BUY | SMC | {why} | R:{rsi:.1f} | IDM/MSS Sync"
                        
                        # SL
                        if bull_ob: calculated_sl = bull_ob[1] - (atr * 0.5)
                        else: calculated_sl = price - (atr * 2)
                        
                        # TP
                        calculated_tp = tp_target if tp_target > 0 else (price + (price - calculated_sl) * Config.RISK_REWARD_RATIO)
                        
                  else:
                    missing = []
                    if not candlestick_conf: missing.append("Candle")
                    if not smc_conf: missing.append("IDM/MSS")
                    status_detail = f"WAIT [{match_type} in Discount | Need: {','.join(missing)}]"
             else:
                 status_detail = f"WAIT [{match_type} but in PREMIUM Zone ❌]"

         # --- SELL LOGIC ---
        is_sell_ob = False
        is_sell_fvg_match = False
        is_sell_fibo = False
        
        # Initialize variables for SELL logic to prevent UnboundLocalError
        calculated_sl = 0.0
        calculated_tp = 0.0

        if bear_ob:
            ob_high, ob_low = bear_ob
            resistance_valid = price <= (ob_high + atr*0.1)
            is_near_zone = price >= (ob_low - atr*0.5)
            if resistance_valid and is_near_zone:
                is_sell_ob = True
        
        for fvg_low, fvg_high in bear_fvg:
            gap_top = max(fvg_low, fvg_high)
            gap_bottom = min(fvg_low, fvg_high)
            if gap_bottom <= price <= gap_top:
                is_sell_fvg_match = True
                break
        
        if fibo_levels and trend_dir == "DOWN":
             l618 = fibo_levels.get(0.618, 99999)
             l786 = fibo_levels.get(0.786, 99999)
             if (l618 - atr*0.2) <= price <= l786:
                 is_sell_fibo = True

        if is_sell_ob or is_sell_fvg_match or is_sell_fibo:
             match_type = "Setup Found"
             if is_sell_ob: match_type = "OB"
             
             candlestick_conf = pattern in ["BEARISH_ENGULFING", "BEARISH_PINBAR"]
             smc_conf = has_idm_sweep or (mss == "BEAR_MSS")

             if is_premium:
                 is_golden_zone = is_sell_ob and is_sell_fibo
                 
                 if (candlestick_conf and smc_conf) or (is_golden_zone and smc_conf):
                      if not self.bot.check_open_positions():
                        signal = "SELL"
                        if is_golden_zone and not candlestick_conf:
                            why = "Golden Setup"
                        else:
                            why = f"{pattern}"
                        status_detail = f"📉 SELL | SMC | {why} | R:{rsi:.1f} | IDM/MSS Sync"
                        
                        if bear_ob: calculated_sl = bear_ob[0] + (atr * 0.5)
                        else: calculated_sl = price + (atr * 2)
                        
                        # Fix TP Calculation: Ensure positive distance
                        sl_dist = abs(calculated_sl - price)
                        calculated_tp = tp_target if tp_target > 0 else (price - (sl_dist * Config.RISK_REWARD_RATIO))

                 else:
                    missing = []
                    if not candlestick_conf: missing.append("Candle")
                    if not smc_conf: missing.append("IDM/MSS")
                    status_detail = f"WAIT [{match_type} in Premium | Need: {','.join(missing)}]"
             else:
                 status_detail = f"WAIT [{match_type} but in DISCOUNT Zone ❌]"

        if signal == "WAIT" and is_kill_zone:
            icon = "🟢" if is_discount else "🔴"
            status_detail = (
                f"⚪ SMC | {icon} {'DISC' if is_discount else 'PREM'} | "
                f"R:{rsi:.1f} | IDM:{'✅' if has_idm_sweep else '❌'} | "
                f"MSS:{mss if mss else 'None'}"
            )

        extra_data = {
           "price": price,
            "atr": atr,
            "fibo_levels": fibo_levels,
            "active_rsi_threshold": 50,
            "custom_sl": calculated_sl if 'calculated_sl' in locals() else 0.0,
            "custom_tp": calculated_tp if 'calculated_tp' in locals() else 0.0
        }
            
        return signal, status_detail, extra_data
