@echo off
setlocal
cd /d "%~dp0.."
set "REPO_ROOT=%CD%\vendor\q3ds-solidworks-mcp"
set "PYTHON_EXE=%REPO_ROOT%\.venv\Scripts\python.exe"

if not exist "%PYTHON_EXE%" (
  echo ERROR: Repository Python environment not found:
  echo %PYTHON_EXE%
  echo Create it with: py -3.12 -m venv vendor\q3ds-solidworks-mcp\.venv
  exit /b 2
)

"%PYTHON_EXE%" "%CD%\gui\solid_ai_gui.py"
exit /b %ERRORLEVEL%
