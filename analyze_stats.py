import pandas as pd
from datetime import datetime
import os

# Get absolute path to the data directory
base_dir = os.path.dirname(os.path.abspath(__file__))
csv_path = os.path.join(base_dir, 'data', 'trade_history.csv')

try:
    # Handle CSV schema change (Mixed 7 and 8 columns) by specifying names
    col_names = ['Time', 'Ticket', 'Type', 'Volume', 'Price', 'Profit', 'Comment', 'Status']
    df = pd.read_csv(csv_path, 
                     names=col_names, 
                     header=None, # We'll skip header manually or filter it out
                     skiprows=1)  # Skip the original header row

    
    df['Time'] = pd.to_datetime(df['Time'])
    
    # Split point: Feb 11, 2026 (New settings started)
    split_date = datetime(2026, 2, 11)
    
    df_before = df[df['Time'] < split_date]
    df_after = df[df['Time'] >= split_date]
    
    
    def get_stats(data, label):
        total = len(data)
        if total == 0:
            return f"\n--- {label} ---\nNo trades."
        
        # Check if Status column exists
        has_status = 'Status' in data.columns
        
        wins = data[data['Profit'] > 0]
        losses = data[data['Profit'] <= 0]
        
        win_rate = (len(wins) / total) * 100
        total_pl = data['Profit'].sum()
        avg_win = wins['Profit'].mean() if not wins.empty else 0
        avg_loss = losses['Profit'].mean() if not losses.empty else 0
        
        # Max Drawdown (simplified as worst trade for now in this context)
        worst = data['Profit'].min()
        best = data['Profit'].max()
        profit_factor = abs(wins['Profit'].sum() / losses['Profit'].sum()) if not losses.empty and losses['Profit'].sum() != 0 else 0

        res = f"\n=== {label} ==="
        res += f"\nTotal Trades: {total} (Wins: {len(wins)} | Losses: {len(losses)})"
        res += f"\nWin Rate:    {win_rate:.2f}%"
        res += f"\nTotal P/L:   ${total_pl:.2f}"
        res += f"\nAvg Win:     ${avg_win:.2f}"
        res += f"\nAvg Loss:    ${avg_loss:.2f}"
        res += f"\nBest Trade:  ${best:.2f}"
        res += f"\nWorst Trade: ${worst:.2f}"
        res += f"\nProfit Factor: {profit_factor:.2f}"
        
        if has_status:
            res += "\n\n--- Status Breakdown ---"
            status_counts = data['Status'].value_counts()
            for status, count in status_counts.items():
                
                # Simple cleanup: Replace known emojis or print safely
                if isinstance(status, str):
                   clean_status = status.replace("🎯", "").replace("🛡️", "").replace("❌", "").replace("👤", "").replace("🤖", "").strip()
                else:
                   clean_status = "Unknown"
                
                # Calculate P/L for this status
                status_pl = data[data['Status'] == status]['Profit'].sum()
                res += f"\n- {clean_status}: {count} trades (P/L: ${status_pl:.2f})"
        else:
            res += "\n\n(No 'Status' data for this period)"
            
        return res

    print(get_stats(df_before, "BEFORE Optimization (Feb 9-10)"))
    print(get_stats(df_after, "AFTER Optimization (Feb 11 - Present)"))
    print("\n" + "="*30)
    
except Exception as e:
    print(f"Error: {e}") 
    import traceback
    traceback.print_exc()
