import os
import sys

def main():
    while True:
        os.system('cls' if os.name == 'nt' else 'clear')
        print("=========================================")
        print("   🤖 XAUUSD BOT LAUNCHER 🚀")
        print("=========================================")
        print("Please select a trading strategy:")
        print("1. MACD + RSI (Classic Trend & Momentum) 📊")
        print("2. OB + FVG + FIBO (Smart Money Concept) 🧠")
        print("0. Exit")
        print("=========================================")
        
        choice = input("Enter choice (1-2): ").strip()
        
        if choice == '1':
            print("\n🚀 Launching MACD/RSI Strategy...")
            os.system(f"{sys.executable} main.py --strategy MACD_RSI")
        elif choice == '2':
            print("\n🧠 Launching OB/FVG/FIBO Strategy...")
            os.system(f"{sys.executable} main.py --strategy OB_FVG_FIBO")
        elif choice == '0':
            print("Goodbye! 👋")
            break
        else:
            print("Invalid choice. Please try again.")
            input("Press Enter to continue...")

if __name__ == "__main__":
    main()
