@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo ========================================================
echo   KHỞI ĐỘNG HỆ THỐNG GIÁM SÁT PPE (DESKTOP NATIVE APP)
echo ========================================================
echo.
.\.venv\Scripts\python.exe -m desktop.main
pause

