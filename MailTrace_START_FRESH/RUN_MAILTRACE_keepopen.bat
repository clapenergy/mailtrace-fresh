@echo on
REM Keep-open launcher for MailTrace (Windows)
cd /d "%~dp0"
where py || (echo Python launcher not found.& pause & exit /b 1)
py -3.11 --version >nul 2>nul || (echo Python 3.11 not found.& pause & exit /b 1)
IF NOT EXIST .venv (echo Creating venv...& py -3.11 -m venv .venv)
call .venv\Scripts\activate
python -m pip install --upgrade pip
pip install -r requirements.txt
echo Starting MailTrace at http://localhost:5000 ...
python app.py
echo.
echo (If the app stopped or crashed, scroll up to read the error.)
pause
