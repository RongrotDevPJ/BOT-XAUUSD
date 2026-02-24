import pandas as pd
import logging
from config.settings import Config

class Indicators:
    @staticmethod
    def calculate_ema(series, period):
        return series.ewm(span=period, adjust=False).mean()

    @staticmethod
    def calculate_macd(series, fast=12, slow=26, signal=9):
        ema_fast = series.ewm(span=fast, adjust=False).mean()
        ema_slow = series.ewm(span=slow, adjust=False).mean()
        macd_line = ema_fast - ema_slow
        signal_line = macd_line.ewm(span=signal, adjust=False).mean()
        return macd_line, signal_line

    @staticmethod
    def calculate_rsi(series, period=14):
        delta = series.diff()
        gain = (delta.where(delta > 0, 0)).ewm(alpha=1/period, adjust=False).mean()
        loss = (-delta.where(delta < 0, 0)).ewm(alpha=1/period, adjust=False).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return rsi

    @staticmethod
    def calculate_bollinger_bands(series, period, std_dev):
        sma = series.rolling(window=period).mean()
        std = series.rolling(window=period).std()
        upper_band = sma + (std * std_dev)
        lower_band = sma - (std * std_dev)
        return upper_band, sma, lower_band

    @staticmethod
    def calculate_atr(df, period=14):
        high_low = df['high'] - df['low']
        high_close = abs(df['high'] - df['close'].shift())
        low_close = abs(df['low'] - df['close'].shift())
        ranges = pd.concat([high_low, high_close, low_close], axis=1)
        true_range = ranges.max(axis=1)
        atr = true_range.rolling(window=period).mean()
        return atr

    @staticmethod
    def calculate_adx(df, period=14):
        """Calculates Average Directional Index (ADX)"""
        high = df['high']
        low = df['low']
        close = df['close']
        
        plus_dm = high.diff()
        minus_dm = low.diff()
        
        plus_dm[plus_dm < 0] = 0
        minus_dm[minus_dm > 0] = 0
        
        tr1 = pd.DataFrame(high - low)
        tr2 = pd.DataFrame(abs(high - close.shift(1)))
        tr3 = pd.DataFrame(abs(low - close.shift(1)))
        frames = [tr1, tr2, tr3]
        tr = pd.concat(frames, axis=1, join='outer').max(axis=1)
        atr = tr.rolling(period).mean()
        
        plus_di = 100 * (plus_dm.ewm(alpha=1/period).mean() / atr)
        minus_di = 100 * (abs(minus_dm).ewm(alpha=1/period).mean() / atr)
        dx = (abs(plus_di - minus_di) / abs(plus_di + minus_di)) * 100
        adx = ((dx.shift(1) * (period - 1)) + dx) / period
        adx_smooth = adx.ewm(alpha=1/period).mean()
        return adx_smooth

    @staticmethod
    def calculate_order_blocks(df, lookback=50, max_sl_points=500):
        """Identifies nearest valid UNMITIGATED Order Blocks"""
        bull_ob = None
        bear_ob = None
        
        try:
            # Iterate backwards to find the latest unmitigated blocks
            for i in range(len(df)-2, len(df)-lookback, -1):
                if i < 5: break
                
                curr = df.iloc[i]
                prev = df.iloc[i-1]
                
                # ATR for size context
                atr_val = df.iloc[i]['atr']
                if pd.isna(atr_val): continue
                
                body_size = abs(curr['close'] - curr['open'])
                is_impulse = body_size > (atr_val * 1.0) # Strong move
                
                # Bullsih OB Search
                if is_impulse and curr['close'] > curr['open']: # Bullish Impulse
                    if prev['close'] < prev['open']: # Prev was Bearish
                        ob_top = prev['high']
                        ob_bottom = prev['low']
                        
                        # Check Mitigation: Has price touched this zone deeply AFTER it was formed?
                        # Zone: ob_bottom to ob_top
                        is_mitigated = False
                        
                        # Check candles from i+1 to now
                        subsequent_candles = df.iloc[i+1:]
                        if not subsequent_candles.empty:
                            # If any candle closed below the OB Top (deep retest) -> Mitigated?
                            # Standard SMC: Wicks are okay (retest), but if body closes inside/below, it might be used up.
                            # Strict Mitigation: If price touched 50% of the block, count as mitigated.
                            ob_mid = (ob_top + ob_bottom) / 2
                            min_low_after = subsequent_candles['low'].min()
                            
                            # If price dipped below 50% of the OB, consider it mitigated/unsafe for a fresh entry
                            if min_low_after < ob_mid:
                                is_mitigated = True
                        
                        # Check if price is still respecting it (Support) - Current Price must be above
                        # Size Filter: Ignore OBs that are too wide (Risk of Capped SL inside zone)
                        # max_sl_points is in points (e.g. 400). 1 point ~ 0.01 (Gold)
                        max_width = max_sl_points * 0.01 
                        
                        if (ob_top - ob_bottom) > max_width:
                             is_mitigated = True # Treat as 'bad' OB
                        
                        if not is_mitigated and df.iloc[-1]['close'] > ob_bottom: 
                            bull_ob = (ob_top, ob_bottom)
                            if bull_ob: break 

            # Bearish OB Search
            for i in range(len(df)-2, len(df)-lookback, -1):
                if i < 5: break
                curr = df.iloc[i]
                prev = df.iloc[i-1]
                atr_val = df.iloc[i]['atr']
                if pd.isna(atr_val): continue
                
                body_size = abs(curr['close'] - curr['open'])
                is_impulse = body_size > (atr_val * 1.0)
                
                if is_impulse and curr['close'] < curr['open']: # Bearish Impulse
                    if prev['close'] > prev['open']: # Prev was Bullish
                        ob_top = prev['high']
                        ob_bottom = prev['low']
                        
                        # Mitigation Check
                        is_mitigated = False
                        subsequent_candles = df.iloc[i+1:]
                        if not subsequent_candles.empty:
                            ob_mid = (ob_top + ob_bottom) / 2
                            max_high_after = subsequent_candles['high'].max()
                            
                            # If price poked above 50% of the OB
                            if max_high_after > ob_mid:
                                is_mitigated = True
                        
                        # Size Filter
                        max_width = max_sl_points * 0.01
                        if (ob_top - ob_bottom) > max_width:
                             is_mitigated = True

                        if not is_mitigated and df.iloc[-1]['close'] < ob_top:
                            bear_ob = (ob_top, ob_bottom)
                            if bear_ob: break
                            
        except Exception as e:
            logging.error(f"SMC OB Calc Error: {e}")
            
        return bull_ob, bear_ob

    @staticmethod
    def calculate_fvg(df, lookback=10):
        """Identifies recent Fair Value Gaps"""
        bull_fvg = []
        bear_fvg = []
        
        try:
            # Check last 'lookback' candles
            for i in range(len(df)-2, len(df)-lookback, -1):
                # Need candle i, i-1, i-2 (current, prev, prev-prev) 
                # FVG is formed by Candle 1, 2, 3. 
                # Let's say i is candle 3 (latest completed)
                # i-1 is candle 2 (big move)
                # i-2 is candle 1 (start)
                
                # We need correct indexing. 
                # i is the potential "retest" candle, FVG was formed before.
                
                # Check for FVG formation at index j (Candle 2)
                j = i # Current candle in loop
                
                c3 = df.iloc[j]     # Candle 3
                c2 = df.iloc[j-1]   # Candle 2 (The Gap Candle)
                c1 = df.iloc[j-2]   # Candle 1
                
                # Bullish FVG: Candle 1 High < Candle 3 Low
                if c1['high'] < c3['low'] and c2['close'] > c2['open']:
                    # Validation: Big body on C2
                    if abs(c2['close'] - c2['open']) > df.iloc[j]['atr'] * 0.5:
                        bull_fvg.append((c1['high'], c3['low'])) # Zone
                
                # Bearish FVG: Candle 1 Low > Candle 3 High
                if c1['low'] > c3['high'] and c2['close'] < c2['open']:
                    if abs(c2['close'] - c2['open']) > df.iloc[j]['atr'] * 0.5:
                         bear_fvg.append((c3['high'], c1['low'])) # Zone

        except Exception as e:
            logging.error(f"FVG Calc Error: {e}")
            
        return bull_fvg, bear_fvg

    @staticmethod
    def get_swing_high_low(df, lookback=50):
        """Finds the highest high and lowest low in the lookback period"""
        try:
            recent_data = df.iloc[-lookback:]
            highest_high = recent_data['high'].max()
            lowest_low = recent_data['low'].min()
            return highest_high, lowest_low
        except Exception as e:
            logging.error(f"Swing High/Low Error: {e}")
            return None, None

    @staticmethod
    def get_swing_low(df, lookback):
        """Gets the lowest low in the lookback period (Tail)"""
        return df['low'].tail(lookback).min()

    @staticmethod
    def get_swing_high(df, lookback):
        """Gets the highest high in the lookback period (Tail)"""
        return df['high'].tail(lookback).max()

            
    @staticmethod
    def calculate_fibonacci_levels(high, low, trend="UP"):
        """Calculates Fibonacci levels based on trend direction"""
        diff = high - low
        levels = {}
        
        if trend == "UP":
            # Retracement from High downwards
            # Level 0 is High, 1 is Low? No.
            # Up Trend: Measure Low to High. Retracement goes down.
            # 0% = High, 100% = Low
            levels[0.0] = high
            levels[0.236] = high - (diff * 0.236)
            levels[0.382] = high - (diff * 0.382)
            levels[0.5] = high - (diff * 0.5)
            levels[0.618] = high - (diff * 0.618)
            levels[0.786] = high - (diff * 0.786)
            levels[1.0] = low
        else:
            # Down Trend: Measure High to Low. Retracement goes up.
            # 0% = Low, 100% = High
            levels[0.0] = low
            levels[0.236] = low + (diff * 0.236)
            levels[0.382] = low + (diff * 0.382)
            levels[0.5] = low + (diff * 0.5)
            levels[0.618] = low + (diff * 0.618)
            levels[0.786] = low + (diff * 0.786)
            levels[1.0] = high
            
        return levels

    @staticmethod
    def check_candlestick_pattern(df, index=-1):
        """Checks for Rejection Patterns (Engulfing, Pinbar)"""
        try:
            curr = df.iloc[index]
            prev = df.iloc[index-1]
            
            # Helper for candle properties
            def get_body(row): return abs(row['close'] - row['open'])
            def is_bull(row): return row['close'] > row['open']
            def is_bear(row): return row['close'] < row['open']
            
            curr_body = get_body(curr)
            prev_body = get_body(prev)
            
            # 1. Engulfing
            # Bullish Engulfing: Prev Bearish, Curr Bullish, Curr Body covers Prev Body
            is_bull_engulfing = (
                is_bear(prev) and 
                is_bull(curr) and 
                curr['close'] > prev['open'] and 
                curr['open'] < prev['close']
            )
            
            # Bearish Engulfing: Prev Bullish, Curr Bearish
            is_bear_engulfing = (
                is_bull(prev) and 
                is_bear(curr) and 
                curr['close'] < prev['open'] and 
                curr['open'] > prev['close']
            )
            
            if is_bull_engulfing: return "BULLISH_ENGULFING"
            if is_bear_engulfing: return "BEARISH_ENGULFING"
            
            # 2. Pinbar (Rejection Candle)
            # Long Wick, Small Body. Wick should be > 2/3 of total length
            total_len = curr['high'] - curr['low']
            if total_len == 0: return None
            
            ratio = curr_body / total_len
            
            # Bullish Pinbar (Hammer): Long Lower Wick
            lower_wick = min(curr['close'], curr['open']) - curr['low']
            if lower_wick > (total_len * 0.6): # 60% is wick
                return "BULLISH_PINBAR"
                
            # Bearish Pinbar (Shooting Star): Long Upper Wick
            upper_wick = curr['high'] - max(curr['close'], curr['open'])
            if upper_wick > (total_len * 0.6):
                return "BEARISH_PINBAR"
                
            return None
            
        except Exception as e:
            logging.error(f"Pattern Check Error: {e}")
            return None
            
    @staticmethod
    def check_liquidity_sweep(df, lookback=10):
        """Checks if current candle swept a recent High/Low (NON-REPAINT)"""
        try:
            # NON-REPAINT: Use the last CLOSED candle
            curr = df.iloc[-2]
            
            # Data Window: From -lookback-2 to -2 (Exclude current and completed)
            # Actually we just need to look back from the candle BEFORE the completed one
            data_window = df.iloc[-lookback-2:-2] 
            
            if data_window.empty: return None
            
            recent_low = data_window['low'].min()
            recent_high = data_window['high'].max()
            
            sweep_status = None
            
            # Bullish Sweep: Price dipped below recent Low but closed above it
            if curr['low'] < recent_low and curr['close'] > recent_low:
                sweep_status = "BULL_SWEEP"
            
            # Bearish Sweep: Price poked above recent High but closed below it
            if curr['high'] > recent_high and curr['close'] < recent_high:
                sweep_status = "BEAR_SWEEP"
                
            return sweep_status
            
        except Exception as e:
            return None

    @staticmethod
    def identify_swing_points(df, lookback=5):
        """
        Identifies recent Swing Highs and Swing Lows using a fractal pattern.
        Standard Fractal: 2 candles left, 1 middle, 2 candles right.
        Returns: list of (index, price, type='HIGH'/'LOW')
        """
        swings = []
        try:
            # We need at least 5 candles to form a fractal
            if len(df) < 5: return []
            
            # Iterate through valid range (leaving space for left/right neighbors)
            start_index = max(2, len(df) - 100)
            
            # NON-REPAINT FIX:
            # - We need to look back at least 2 candles (Right Neighbors)
            # - So the potential Swing Point is at index `i`
            # - The latest confirming candle is `i+2`
            # - We must ensure `i+2` is a COMPLETED candle (index <= len(df)-2)
            # - Current forming candle is at `len(df)-1`
            # - Last completed candle is `len(df)-2`
            # - So max `i` st. `i+2 <= len(df)-2` => `i <= len(df)-4`
            # But let's use `len(df)-3` to match `range` exclusives
            
            # Simplified: 
            # If we employ a "strict" 2-candle confirmation, the Swing High at index [i] is confirmed when candle [i+2] closes.
            # So we iterate up to `len(df) - 3` (exclusive of last 2 forming/recent)
            
            end_index = len(df) - 2 # This allows checking up to the last CLOSED candle
            
            for i in range(start_index, end_index):
                # Swing High: Middle High > Left 2 Highs AND Middle High > Right 2 Highs
                current_high = df.iloc[i]['high']
                if (current_high > df.iloc[i-1]['high'] and 
                    current_high > df.iloc[i-2]['high'] and 
                    current_high > df.iloc[i+1]['high'] and 
                    current_high > df.iloc[i+2]['high']):
                    swings.append({'index': i, 'price': current_high, 'type': 'HIGH'})
                    
                # Swing Low: Middle Low < Left 2 Lows AND Middle Low < Right 2 Lows
                current_low = df.iloc[i]['low']
                if (current_low < df.iloc[i-1]['low'] and 
                    current_low < df.iloc[i-2]['low'] and 
                    current_low < df.iloc[i+1]['low'] and 
                    current_low < df.iloc[i+2]['low']):
                    swings.append({'index': i, 'price': current_low, 'type': 'LOW'})
                    
            return swings
        except Exception as e:
            logging.error(f"Swing Point Error: {e}")
            return []

    @staticmethod
    def check_mss(df, swing_points):
        """
        Checks for Market Structure Shift (MSS) based on BODY CLOSE.
        - Bullish MSS: Price closes above the most recent major Swing High.
        - Bearish MSS: Price closes below the most recent major Swing Low.
        - NON-REPAINT: Uses df.iloc[-2] (Last Completed Candle)
        """
        try:
            if not swing_points or len(df) < 2: return None
            
            # NON-REPAINT: Use the last CLOSED candle
            last_candle = df.iloc[-2]
            
            # Filter swings by type
            swing_highs = [s for s in swing_points if s['type'] == 'HIGH']
            swing_lows = [s for s in swing_points if s['type'] == 'LOW']
            
            mss_status = None
            
            # Check Bullish MSS
            if swing_highs:
                last_swing_high = swing_highs[-1]
                if last_candle['close'] > last_swing_high['price']:
                    mss_status = "BULL_MSS"
            
            # Check Bearish MSS
            if swing_lows:
                last_swing_low = swing_lows[-1]
                if last_candle['close'] < last_swing_low['price']:
                    mss_status = "BEAR_MSS"
                    
            return mss_status
            
        except Exception as e:
            return None

    @staticmethod
    def check_inducement_sweep(df, swing_points, current_trend="UP"):
        """
        Checks if Inducement (IDM) has been swept.
        - Uptrend: Look for a recent Swing Low (IDM) to be swept.
        - Downtrend: Look for a recent Swing High (IDM) to be swept.
        - NON-REPAINT: Uses df.iloc[-2] (Last Completed Candle)
        """
        try:
            if not swing_points or len(df) < 2: return False
            
            # NON-REPAINT: Use the last CLOSED candle
            curr = df.iloc[-2]
            swept = False
            
            if current_trend == "UP":
                # In Up trend, we look for price to come back down to sweep a recent LOW
                recent_lows = [s for s in swing_points if s['type'] == 'LOW']
                if recent_lows:
                    last_idm = recent_lows[-1] 
                    if curr['low'] < last_idm['price']:
                         swept = True
            elif current_trend == "DOWN":
                # In Down trend, we look for price to come back up to sweep a recent HIGH
                recent_highs = [s for s in swing_points if s['type'] == 'HIGH']
                if recent_highs:
                    last_idm = recent_highs[-1]
                    if curr['high'] > last_idm['price']:
                        swept = True
                        
            return swept
                        
            return swept
        except Exception as e:
            return False

