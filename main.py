import logging
import sys
import os
import argparse

# Ensure project root is in path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# ==========================================
# LOGGING SETUP MOVED TO MAIN
# ==========================================
# Ensure logs dir exists
if not os.path.exists('logs'):
    os.makedirs('logs')

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='XAUUSD Trading Bot')
    parser.add_argument('--strategy', type=str, default='TRIPLE_CONFLUENCE', 
                        help='Strategy to run: TRIPLE_CONFLUENCE (Sniper), MACD_RSI or OB_FVG_FIBO')
    
    args = parser.parse_args()
    
    # Dynamic Log Filename
    log_filename = f'logs/trading_{args.strategy}.log'
    
    logging.basicConfig(
        filename=log_filename, 
        level=logging.INFO, 
        format='%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S',
        force=True, # Force reconfiguration
        encoding='utf-8' # 🔧 FIX: Force UTF-8 for emojis
    )

    # Setup Console Handler
    if sys.stdout.encoding != 'utf-8':
        sys.stdout.reconfigure(encoding='utf-8')

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    console_handler.setFormatter(formatter)
    logging.getLogger().addHandler(console_handler)
    
    try:
        from app.bot import XAUUSDBot
        # Instantiate and Run with selected strategy
        logging.info(f"Starting Bot with Strategy: {args.strategy}")
        bot = XAUUSDBot(strategy_name=args.strategy)
        bot.run()
    except Exception as e:
        logging.critical(f"Fatal Error: {e}")
