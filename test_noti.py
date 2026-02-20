import requests
import sys
import os

# Add current directory to path to import Config
sys.path.append(os.getcwd())

try:
    from config.settings import Config
    import MetaTrader5 as mt5 # Just to check if it's there
except ImportError as e:
    print(f"❌ Error importing dependencies: {e}")
    print("Please run 'run_bot.bat' and select option 5 to install requirements.")
    sys.exit(1)

def test_noti():
    print("--- Telegram Notification Test ---")
    
    if not Config.TELEGRAM_ENABLED:
        print("[-] Status: Telegram is DISABLED in config/settings.py")
        print("Please set TELEGRAM_ENABLED = True first.")
        return
    
    if not Config.TELEGRAM_TOKEN or not Config.TELEGRAM_CHAT_ID:
        print("[-] Status: Token or Chat ID is missing in config/settings.py")
        return

    print(f"[>] Target Chat ID: {Config.TELEGRAM_CHAT_ID}")
    print(f"[>] Using Token: {Config.TELEGRAM_TOKEN[:10]}... (truncated)")
    
    url = f"https://api.telegram.org/bot{Config.TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": Config.TELEGRAM_CHAT_ID,
        "text": "Telegram Notification Test\n\n- Connection Successful!\n- Your bot is ready for notifications.",
        "parse_mode": "Markdown"
    }
    
    try:
        print("[*] Sending request...")
        response = requests.post(url, json=payload, timeout=15)
        if response.status_code == 200:
            print("\n[SUCCESS] Message sent to Telegram! Please check your mobile.")
        else:
            print(f"\n[FAILED] Telegram API Error: {response.text}")
            print("Tip: Make sure you have clicked 'Start' in your Telegram bot.")
    except Exception as e:
        print(f"\n[ERROR] Could not connect to Telegram API: {e}")
        print("Tip: Check your internet connection.")

if __name__ == "__main__":
    test_noti()
