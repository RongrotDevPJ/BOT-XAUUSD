@echo off
title Multi-Bot Master Launcher 🚀
cls
echo ==========================================
echo    STARTING ALL 4 TRADING BOTS...
echo ==========================================
echo.

echo [1/4] Starting XAUUSD: Triple Confluence (Sniper) 🎯
start "XAU-Triple" python main.py --strategy TRIPLE_CONFLUENCE
timeout /t 2 /nobreak >nul

echo [2/4] Starting XAUUSD: SMC (OB/FVG/Fibo) 🛡️
start "XAU-SMC" python main.py --strategy OB_FVG_FIBO
timeout /t 2 /nobreak >nul

echo [3/4] Starting XAUUSD: MACD + RSI 📊
start "XAU-MACD" python main.py --strategy MACD_RSI
timeout /t 2 /nobreak >nul

echo [4/4] Starting BTC: Scalper Bot ₿
start "BTC-Bot" python -m BOT-BTC.main

echo.
echo ==========================================
echo ✅ All 4 bots have been launched successfully!
echo Each bot is running in its own window.
echo ==========================================
pause
