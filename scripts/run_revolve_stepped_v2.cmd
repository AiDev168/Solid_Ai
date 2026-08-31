@echo off
setlocal
cd /d "%~dp0.."
set "PYTHON=%CD%\vendor\q3ds-solidworks-mcp\.venv\Scripts\python.exe"
"%PYTHON%" "%CD%\scripts\run_revolve_stepped_v2.py"
set "CODE=%ERRORLEVEL%"
endlocal & exit /b %CODE%
