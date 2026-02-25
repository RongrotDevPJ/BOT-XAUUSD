import csv
import os

def fix_trade_history():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    csv_path = os.path.join(base_dir, 'data', 'trade_history.csv')
    backup_path = os.path.join(base_dir, 'data', 'trade_history_backup.csv')
    
    if not os.path.exists(csv_path):
        print("CSV not found.")
        return

    # Backup first
    import shutil
    shutil.copy2(csv_path, backup_path)
    print(f"Backup created at {backup_path}")

    rows = []
    header = ['Time', 'Ticket', 'Strategy', 'Type', 'Volume', 'Price', 'Profit', 'Comment', 'Status']
    
    with open(csv_path, mode='r', encoding='utf-8') as f:
        reader = csv.reader(f)
        orig_header = next(reader, None)
        for row in reader:
            if not row: continue
            
            # Normalize to 9 columns
            if len(row) == 7: # Legacy 7 cols
                # Time, Ticket, Type, Volume, Price, Profit, Comment
                new_row = [row[0], row[1], "Legacy", row[2], row[3], row[4], row[5], row[6], "UNKNOWN"]
            elif len(row) == 8: # Legacy 8 cols
                # Time, Ticket, Type, Volume, Price, Profit, Comment, Status
                new_row = [row[0], row[1], "Legacy", row[2], row[3], row[4], row[5], row[6], row[7]]
            elif len(row) == 9:
                new_row = row
            else:
                # Truncate or pad
                new_row = row[:9] + [""] * (9 - len(row))
            
            # Infer/Fix strategy
            try:
                price = float(new_row[5])
                # If strategy column looks like a comment (contains SL/TP info)
                if "[" in new_row[2] and "]" in new_row[2]:
                    strat_val = new_row[2]
                    # Restore comment if missing
                    if not new_row[7] or new_row[7] == "Legacy":
                        new_row[7] = strat_val
                    # Set strategy based on price
                    new_row[2] = "BTCUSD" if price > 3000 else "XAUUSD"
                
                # Double check by price for "Legacy" labeled ones
                if new_row[2] == "Legacy":
                    new_row[2] = "BTCUSD" if price > 3000 else "XAUUSD"
            except:
                pass
                
            rows.append(new_row)

    with open(csv_path, mode='w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(header)
        writer.writerows(rows)
    
    print(f"Successfully fixed {len(rows)} rows in trade_history.csv")

if __name__ == "__main__":
    fix_trade_history()
