@echo off
title XAUUSD Bot Launcher
cls

:MENU
cls
echo =========================================
echo    XAUUSD BOT LAUNCHER (Multi-Window) 🚀
echo =========================================
echo.
echo [1] MACD + RSI Strategy 📊
echo [2] SMC (OB + FVG + FIBO) Strategy 🧠
echo [3] Triple Confluence (EMA + BB + RSI) 🎯
echo [4] RUN ALL 3 STRATEGIES (High Risk) 🔥🔥🔥
echo [5] Exit
echo.
set /p choice=Select Option (1-5): 

if "%choice%"=="1" goto MACD
if "%choice%"=="2" goto SMC
if "%choice%"=="3" goto TRIPLE
if "%choice%"=="4" goto ALL_THREE
if "%choice%"=="5" goto EXIT

echo Invalid Choice. Try again.
pause
goto MENU

:MACD
start "Bot: MACD_RSI" cmd /k "python main.py --strategy MACD_RSI"
goto MENU

:SMC
start "Bot: SMC" cmd /k "python main.py --strategy OB_FVG_FIBO"
goto MENU

:TRIPLE
start "Bot: Triple Confluence" cmd /k "python main.py --strategy TRIPLE_CONFLUENCE"
goto MENU

:ALL_THREE
start "Bot: MACD_RSI" cmd /k "python main.py --strategy MACD_RSI"
timeout /t 2 >nul
start "Bot: SMC" cmd /k "python main.py --strategy OB_FVG_FIBO"
timeout /t 2 >nul
start "Bot: Triple Confluence" cmd /k "python main.py --strategy TRIPLE_CONFLUENCE"
goto MENU

:EXIT
exit
