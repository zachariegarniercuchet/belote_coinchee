@echo off
setlocal
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo Local Python environment not found. Set it up once with:
    echo   python -m venv .venv
    echo   .venv\Scripts\python.exe -m pip install -r requirements.txt
    echo The setup needs internet; normal launches do not download anything.
    pause
    exit /b 1
)

echo Keep this window open while playing. Press Ctrl+C to stop the server.
".venv\Scripts\python.exe" -B -u server.py
exit /b %errorlevel%
