@echo off
echo Installing dependencies...
pip install -r requirements.txt --quiet
echo.
echo Open http://localhost:5000 in your browser
echo Press Ctrl+C to stop
echo.
python server.py
pause
