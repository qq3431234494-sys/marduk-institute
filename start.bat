@echo off
chcp 65001 >nul 2>&1
title MARDUK INSTITUTE - AI HR System

echo ==============================================
echo   MARDUK INSTITUTE - AI HR System
echo ==============================================
echo.

if not exist "venv\Scripts\python.exe" (
    echo [ERROR] Virtual environment not found.
    echo   Please run: pip install -r requirements.txt
    pause
    exit /b 1
)

cd /d "%~dp0"

if not exist ".env" (
    echo [WARNING] .env file not found.
    echo   Please copy .env.example to .env and set your API Key.
    echo.
)

venv\Scripts\python.exe -c "from dotenv import load_dotenv; load_dotenv(); import os; key=os.environ.get('DEEPSEEK_API_KEY',''); exit(0 if key and key.startswith('sk-') else 1)"
if errorlevel 1 (
    echo [WARNING] API Key not configured.
    echo   Please set DEEPSEEK_API_KEY=sk-your-key in .env file.
    echo.
) else (
    echo [OK] DeepSeek API Key configured.
    echo.
)

echo [INFO] Starting Flask server...
echo [INFO] URL: http://127.0.0.1:5000
echo ==============================================
echo.

venv\Scripts\python.exe app.py
