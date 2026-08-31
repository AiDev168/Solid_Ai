@echo off
setlocal
cd /d "%~dp1.."
set "PYTHON=%CD%\vendor\q3ds-solidworks-mcp\.venv\Scripts\python.exe"
"%PYTHON%" -m scripts.run_revolve_stepped_v2
set "CODE=%ERRORLEVEL%"
endlocal & exit /b %CODE%
