@echo off
cd "%~dp0"
set "PAGE_URL=http://localhost:8000/ReleaseProcessGenerator.html?v=%RANDOM%"
start "" powershell -NoProfile -WindowStyle Hidden -Command "Start-Sleep -Seconds 2; Start-Process '%PAGE_URL%'"
python -m http.server
pause
REM 打开浏览器输入 localhost:8000