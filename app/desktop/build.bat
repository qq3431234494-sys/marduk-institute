@echo off
chcp 65001 >nul
echo ============================================
echo   MARDUK INSTITUTE - Windows Desktop Build
echo ============================================
echo.

set PROJECT_ROOT=%~dp0..\..
set DESKTOP_DIR=%~dp0

echo [1/5] Checking Python...
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python not found. Please install Python 3.10+
    pause
    exit /b 1
)

echo [2/5] Installing dependencies...
pip install -r "%DESKTOP_DIR%requirements.txt" --quiet
if errorlevel 1 (
    echo ERROR: Failed to install dependencies
    pause
    exit /b 1
)

echo [3/5] Cleaning previous build...
if exist "%PROJECT_ROOT%\build" rmdir /s /q "%PROJECT_ROOT%\build"
if exist "%PROJECT_ROOT%\dist" rmdir /s /q "%PROJECT_ROOT%\dist"
if exist "%DESKTOP_DIR%MardukInstitute.spec" del /q "%DESKTOP_DIR%MardukInstitute.spec"

echo [4/5] Building EXE with PyInstaller...
pyinstaller --noconfirm --onefile --windowed ^
    --name "MardukInstitute" ^
    --add-data "%PROJECT_ROOT%\templates;templates" ^
    --add-data "%PROJECT_ROOT%\static;static" ^
    --add-data "%PROJECT_ROOT%\app.py;." ^
    --add-data "%PROJECT_ROOT%\db.py;." ^
    --add-data "%PROJECT_ROOT%\config.py;." ^
    --add-data "%PROJECT_ROOT%\deepseek_client.py;." ^
    --hidden-import=PyPDF2 ^
    --hidden-import=docx ^
    --hidden-import=bcrypt ^
    --hidden-import=cryptography ^
    --hidden-import=cryptography.fernet ^
    --hidden-import=flask_limiter ^
    --hidden-import=PIL ^
    --hidden-import=webview ^
    --hidden-import=dotenv ^
    --hidden-import=jwt ^
    --hidden-import=lxml ^
    --hidden-import=blinker ^
    --hidden-import=limits ^
    --hidden-import=click ^
    --hidden-import=jinja2 ^
    --hidden-import=markupsafe ^
    --hidden-import=itsdangerous ^
    --hidden-import=werkzeug ^
    --hidden-import=werkzeug.security ^
    --hidden-import=sqlite3 ^
    --hidden-import=http.server ^
    --collect-all=pywebview ^
    "%DESKTOP_DIR%launcher.py"

if errorlevel 1 (
    echo ERROR: PyInstaller build failed
    pause
    exit /b 1
)

echo [5/5] Copying data directory...
if not exist "%PROJECT_ROOT%\dist\data\backups\files" (
    mkdir "%PROJECT_ROOT%\dist\data\backups\files"
)
if not exist "%PROJECT_ROOT%\dist\data\backups\payloads" (
    mkdir "%PROJECT_ROOT%\dist\data\backups\payloads"
)

if exist "%PROJECT_ROOT%\.env" (
    copy "%PROJECT_ROOT%\.env" "%PROJECT_ROOT%\dist\.env" >nul
) else (
    echo DEEPSEEK_API_KEY=> "%PROJECT_ROOT%\dist\.env"
)

echo.
echo ============================================
echo   BUILD COMPLETE!
echo.
echo   EXE: %PROJECT_ROOT%\dist\MardukInstitute.exe
echo.
echo   IMPORTANT:
echo   1. Place .env with your API key in the
echo      same folder as the EXE:
echo        DEEPSEEK_API_KEY=your_key_here
echo   2. The 'data' folder stores the database
echo      and must stay next to the EXE
echo ============================================
pause
