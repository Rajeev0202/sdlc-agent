@echo off
echo Starting SDLC Agent Web Server...
echo.
echo Server will run on: http://127.0.0.1:5002
echo.
echo Press Ctrl+C to stop the server
echo.

cd /d C:\Users\Administrator\sdlc-agent
python -m sdlc_agent.web.app
