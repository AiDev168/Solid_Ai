@echo off
setlocal
cd /d %~dp0..
python scripts\run_live_capability_qualification_v1.py
exit /b %ERRORLEVEL%
