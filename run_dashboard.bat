@echo off
echo ===========================================
echo       XAUUSD Bot Dashboard Launcher
echo ===========================================

echo 1. Checking Python...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python not found or not in PATH!
    echo Please install Python and add to PATH.
    pause
    exit /b
)

echo 2. Installing Dependencies (if missing)...
python -m pip install --upgrade streamlit plotly pandas MetaTrader5 schedule >nul 2>&1

echo 3. Launching Dashboard...
echo Open your browser to the URL shown below (usually http://localhost:8501)
python -m streamlit run dashboard.py

if %errorlevel% neq 0 (
    echo [ERROR] Dashboard failed to start.
    echo Please check the error message above.
)
pause
