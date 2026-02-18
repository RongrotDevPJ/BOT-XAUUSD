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
echo [3] BOTH Strategies (2 Windows) 🔥
echo [4] Exit
echo.
set /p choice=Select Option (1-4): 

if "%choice%"=="1" goto MACD
if "%choice%"=="2" goto SMC
if "%choice%"=="3" goto BOTH
if "%choice%"=="4" goto EXIT

echo Invalid Choice. Try again.
pause
goto MENU

:MACD
start "Bot: MACD_RSI" cmd /k "python main.py --strategy MACD_RSI"
goto MENU

:SMC
start "Bot: SMC" cmd /k "python main.py --strategy OB_FVG_FIBO"
goto MENU

:BOTH
start "Bot: MACD_RSI" cmd /k "python main.py --strategy MACD_RSI"
timeout /t 2 >nul
start "Bot: SMC" cmd /k "python main.py --strategy OB_FVG_FIBO"
goto MENU

:EXIT
exit
