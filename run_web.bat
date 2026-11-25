@echo off
chcp 65001 >nul
cd /d "%~dp0"
rem Port co the doi bang bien moi truong: set PPE_WEB_PORT=8010 roi moi chay file nay
if "%PPE_WEB_PORT%"=="" set PPE_WEB_PORT=8000
echo ========================================================
echo   KHỞI ĐỘNG HỆ THỐNG GIÁM SÁT PPE (WEB BROWSER MODE)
echo   Truy cập: http://127.0.0.1:%PPE_WEB_PORT%/dashboard
echo ========================================================
echo.
.\.venv\Scripts\python.exe -m uvicorn backend.app:app --host 127.0.0.1 --port %PPE_WEB_PORT%
pause

