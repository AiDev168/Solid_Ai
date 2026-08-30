@echo off
setlocal
cd /d "%~dp0.."
set "REPO_ROOT=%CD%\vendor\q3ds-solidworks-mcp"
set "PYTHON_EXE=%REPO_ROOT%\.venv\Scripts\python.exe"
set "PYTHONPATH=%CD%\gui\offline_guard;%PYTHONPATH%"

if not exist "%PYTHON_EXE%" (
  echo ERROR: Repository Python environment not found:
  echo %PYTHON_EXE%
  echo Create it with: py -3.12 -m venv vendor\q3ds-solidworks-mcp\.venv
  exit /b 2
)

echo Solid AI offline mode: Python network access limited to loopback.
"%PYTHON_EXE%" "%CD%\gui\solid_ai_gui.py"
exit /b %ERRORLEVEL%
