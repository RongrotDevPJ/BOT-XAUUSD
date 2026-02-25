import pandas as pd
from datetime import datetime
import os
import csv
import sys

# Set default encoding for stdout to handle emojis
if sys.stdout.encoding != 'utf-8':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# Get absolute path to the data directory
base_dir = os.path.dirname(os.path.abspath(__file__))
csv_path = os.path.join(base_dir, 'data', 'trade_history.csv')

try:
    rows = []
    with open(csv_path, mode='r', encoding='utf-8') as f:
        reader = csv.reader(f)
        header = next(reader)
        for row in reader:
            if not row: continue
            
            # Normalize column count to 9
            # Format: Time, Ticket, Strategy, Type, Volume, Price, Profit, Comment, Status
            if len(row) == 7:
                # Time, Ticket, Type, Volume, Price, Profit, Comment
                row.insert(2, "Legacy") # Strategy
                row.append("Legacy")    # Status
            elif len(row) == 8:
                # Time, Ticket, Type, Volume, Price, Profit, Comment, Status
                row.insert(2, "Legacy") # Strategy
            elif len(row) > 9:
                # Some rows might have extra strategy column at index 2 already
                row = row[:9]
                
            rows.append(row)
            
    col_names = ['Time', 'Ticket', 'Strategy', 'Type', 'Volume', 'Price', 'Profit', 'Comment', 'Status']
    df = pd.DataFrame(rows, columns=col_names)
    
    # Clean numeric columns
    numeric_cols = ['Volume', 'Price', 'Profit']
    for col in numeric_cols:
        df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
    
    df['Time'] = pd.to_datetime(df['Time'], errors='coerce')
    df = df.dropna(subset=['Time'])
    
    # Split point: Feb 11, 2026 (New settings started)
    split_date = datetime(2026, 2, 11)
    
    df_before = df[df['Time'] < split_date]
    df_after = df[df['Time'] >= split_date]
    
    def get_stats(data, label):
        total = len(data)
        if total == 0:
            return f"\n=== {label} ===\nสถานะ: ไม่มีข้อมูลการเทรด"
        
        wins = data[data['Profit'] > 0]
        losses = data[data['Profit'] < 0] # Exclude zero for loss count
        breakevens = data[data['Profit'] == 0]
        
        win_rate = (len(wins) / total) * 100 if total > 0 else 0
        total_pl = data['Profit'].sum()
        avg_win = wins['Profit'].mean() if not wins.empty else 0
        avg_loss = losses['Profit'].mean() if not losses.empty else 0
        
        loss_sum = abs(losses['Profit'].sum())
        profit_factor = (wins['Profit'].sum() / loss_sum) if loss_sum != 0 else 0

        res = f"\n=== {label} ==="
        res += f"\nจำนวนรายการทั้งหมด: {total} (ชนะ: {len(wins)} | แพ้: {len(losses)} | เสมอ: {len(breakevens)})"
        res += f"\nอัตรา Win Rate:    {win_rate:.2f}%"
        res += f"\nกำไร/ขาดทุนสุทธิ:   ${total_pl:.2f}"
        res += f"\nเฉลี่ยกำไร (Win):    ${avg_win:.2f}"
        res += f"\nเฉลี่ยขาดทุน (Loss):  ${avg_loss:.2f}"
        res += f"\nProfit Factor:     {profit_factor:.2f}"
        
        res += "\n\n--- แยกประเภทตามสถานะ (Status) ---"
        status_counts = data['Status'].value_counts()
        for status, count in status_counts.items():
            status_pl = data[data['Status'] == status]['Profit'].sum()
            res += f"\n- {status}: {count} รายการ (P/L: ${status_pl:.2f})"
            
        return res

    print(get_stats(df_before, "สรุปผล ก่อน ปรับปรุง (9-10 ก.พ.)"))
    print(get_stats(df_after, "สรุปผล หลัง ปรับปรุง (11 ก.พ. - ปัจจุบัน)"))
    
    # Strategy Analysis (If available)
    if not df_after.empty:
        print("\n=== เจาะลึกรายกลยุทธ์ (หลังปรับปรุง) ===")
        strategies = df_after['Strategy'].unique()
        for strat in strategies:
            if strat == "Legacy" or not strat: continue
            strat_data = df_after[df_after['Strategy'] == strat]
            print(f"\nกลยุทธ์: {strat}")
            print(f"- จำนวนเทรด: {len(strat_data)}")
            print(f"- กำไรสุทธิ: ${strat_data['Profit'].sum():.2f}")

except Exception as e:
    print(f"Error: {e}") 
    import traceback
    traceback.print_exc()
