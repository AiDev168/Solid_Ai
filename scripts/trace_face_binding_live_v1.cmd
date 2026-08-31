@echo off
setlocal
cd /d "%~dp0.."
set "PYTHON=%CD%\vendor\q3ds-solidworks-mcp\.venv\Scripts\python.exe"
"%PYTHON%" "%CD%\scripts\trace_face_binding_live_v1.py"
set "CODE=%ERRORLEVEL%"
endlocal & exit /b %CODE%
