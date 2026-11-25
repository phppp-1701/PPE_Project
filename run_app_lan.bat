@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo ========================================================
echo   KHỞI ĐỘNG HỆ THỐNG GIÁM SÁT PPE (CHẾ ĐỘ MẠNG LAN / TV BOX)
echo ========================================================
echo.
echo   Địa chỉ truy cập trên TV Box: http://192.168.1.197:8080
echo ========================================================
echo.
.\.venv\Scripts\python.exe -m desktop.main --host 0.0.0.0 --port 8080
pause
