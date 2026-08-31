@echo off
setlocal
cd /d %~dp0..
set "SOLID_AI_VENV=%CD%\vendor\q3ds-solidworks-mcp\.venv\Scripts\python.exe"
if not exist "%SOLID_AI_VENV%" (
  echo ERROR: SolidPilot MCP Python environment not found:
  echo %SOLID_AI_VENV%
  exit /b 1
)
"%SOLID_AI_VENV%" scripts\run_live_capability_qualification_v1.py
exit /b %ERRORLEVEL%
