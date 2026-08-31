@echo off
setlocal
cd /d "%~dp0.."
"vendor\q3ds-solidworks-mcp\.venv\Scripts\python.exe" "scripts\run_aidesigner_composed_e2e_v1.py" %*
exit /b %errorlevel%
