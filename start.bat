@echo off
echo Starting Zimbabwe Supermarket...
echo.
rem Local development mode: serves static files and skips the HTTPS redirect.
rem Never set this on the production server.
set DJANGO_DEBUG=1
echo Installing dependencies...
pip install Django==4.2.7
pip install Pillow
echo.
echo Running migrations...
python manage.py migrate
echo.
echo Populating sample data...
python manage.py populate_data
echo.
echo Starting development server...
echo.
echo The application will be available at: http://127.0.0.1:8000
echo Admin panel: http://127.0.0.1:8000/admin
echo.
echo Press Ctrl+C to stop the server
echo.
python manage.py runserver
pause

