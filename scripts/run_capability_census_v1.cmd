@echo off
setlocal
cd /d %~dp0\..
python scripts\run_capability_census_v1.py
exit /b %ERRORLEVEL%
