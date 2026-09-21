@echo off
rem Start JKC Supermarket on this computer.
rem
rem DJANGO_DEBUG=1 is for local use only: it makes Django serve the static
rem files itself and skip the HTTPS redirect. Never set it on the live site.
setlocal
cd /d "%~dp0"
set DJANGO_DEBUG=1

if not exist ".venv\Scripts\python.exe" (
    echo No virtual environment yet - creating one and installing the packages...
    python -m venv .venv || goto :error
    .venv\Scripts\python.exe -m pip install --upgrade pip
    .venv\Scripts\python.exe -m pip install -r requirements.txt || goto :error
    echo.
)

echo Applying any new database migrations...
.venv\Scripts\python.exe manage.py migrate || goto :error

echo.
echo   The shop:          http://127.0.0.1:8000/
echo   Admin dashboard:   http://127.0.0.1:8000/founder/     (staff login)
echo   Django admin:      http://127.0.0.1:8000/admin/
echo.
echo   Press Ctrl+C to stop the server.
echo.
.venv\Scripts\python.exe manage.py runserver
goto :eof

:error
echo.
echo Something above failed. Fix it, then run this file again.
pause
