@echo off
title XAUUSD Trading Bot Launcher 🚀
cls

:MENU
echo ==========================================
echo    XAUUSD TRADING BOT - MENU
echo ==========================================
echo 1. Run MACD + RSI Strategy (Classic)
echo 2. Run SMC Strategy (Smart Money Concepts)
echo 3. Run Triple Confluence (EMA+BB+RSI) 🎯
echo 4. Run ALL 3 Strategies (Separate Windows) 🔥🔥🔥
echo 5. Install Dependencies (First Time Run)
echo 6. Exit
echo ==========================================
set /p choice=Select Option (1-6): 

if "%choice%"=="1" goto RUN_MACD
if "%choice%"=="2" goto RUN_SMC
if "%choice%"=="3" goto RUN_TRIPLE
if "%choice%"=="4" goto RUN_ALL
if "%choice%"=="5" goto INSTALL_DEPS
if "%choice%"=="6" exit

echo Invalid choice. Please try again.
pause
cls
goto MENU

:RUN_MACD
start "Bot: MACD_RSI" python main.py --strategy MACD_RSI
exit

:RUN_SMC
start "Bot: SMC (OB_FVG_FIBO)" python main.py --strategy OB_FVG_FIBO
exit

:RUN_TRIPLE
start "Bot: Triple Confluence" python main.py --strategy TRIPLE_CONFLUENCE
exit

:RUN_ALL
start "Bot: MACD_RSI" python main.py --strategy MACD_RSI
timeout /t 2 >nul
start "Bot: SMC" python main.py --strategy OB_FVG_FIBO
timeout /t 2 >nul
start "Bot: Triple Confluence" python main.py --strategy TRIPLE_CONFLUENCE
exit

:INSTALL_DEPS
echo Installing dependencies...
python -m pip install -r requirements.txt
echo Done!
pause
cls
goto MENU
