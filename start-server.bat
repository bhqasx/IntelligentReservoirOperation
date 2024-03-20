@echo off
cd "%~dp0"
python -m http.server
pause
REM 打开浏览器输入 localhost:8000