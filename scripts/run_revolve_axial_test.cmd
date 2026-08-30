@echo off
setlocal
cd /d %~dp0..
call .\vendor\q3ds-solidworks-mcp\.venv\Scripts\python.exe .\scripts\run_revolve_axial_test.py
set EXITCODE=%ERRORLEVEL%
echo.
echo EXITCODE=%EXITCODE%
pause
exit /b %EXITCODE%
