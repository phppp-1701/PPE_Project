@echo off
rem Bridge camera Fofu FF-8120WP -> MJPEG cho app PPE
rem Chay file nay TRUOC khi mo Live trong app. Giua cua so nay mo thi stream chay.
rem Bridge crash ngau nhien (segfault FFmpeg thi thoang gap) thi tu khoi dong lai sau 3 giay.
cd /d "%~dp0"
echo [fofu-bridge] dang keo frame tu camera 192.168.1.202 ...
echo [fofu-bridge] stream MJPEG: http://127.0.0.1:8077/stream.mjpg
echo [fofu-bridge] trang thai:   http://127.0.0.1:8077/status
echo (dong cua so nay = tat stream)

:loop
python scripts\fofu_bridge.py --port 8077
echo [fofu-bridge] bridge da thoat bat thuong — tu khoi dong lai sau 3 giay (Ctrl+C de tat that)
timeout /t 3 /nobreak >nul
goto loop
