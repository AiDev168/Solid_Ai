@echo off
setlocal
cd /d "%~dp0.."
set "PYTHON=%CD%\vendor\q3ds-solidworks-mcp\.venv\Scripts\python.exe"
if not exist "%PYTHON%" (
  echo ERROR: Python runtime not found: %PYTHON%
  exit /b 2
)
if "%*"=="" (
  "%PYTHON%" scripts\run_llm_plan_v1.py
) else (
  "%PYTHON%" scripts\run_llm_plan_v1.py %*
)
set "CODE=%ERRORLEVEL%"
endlocal & exit /b %CODE%
