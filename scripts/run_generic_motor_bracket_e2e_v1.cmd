@echo off
setlocal
cd /d "%~dp0.."
set "PYTHON=%CD%\vendor\q3ds-solidworks-mcp\.venv\Scripts\python.exe"
if not exist "%PYTHON%" (
  echo ERROR: Python runtime not found: %PYTHON%
  exit /b 2
)
"%PYTHON%" -m scripts.run_generic_motor_bracket_e2e_v1
set "CODE=%ERRORLEVEL%"
endlocal & exit /b %CODE%
