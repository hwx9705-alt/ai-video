@echo off
chcp 65001
echo.
echo  AI 科普视频生产系统 - Web UI
echo  ================================
echo.

set HTTP_PROXY=
set HTTPS_PROXY=
set NO_PROXY=*
set PYTHONIOENCODING=utf-8

cd /d "%~dp0"

echo. | "C:\Users\10536\AppData\Local\Programs\Python\Python38\Scripts\streamlit.exe" run app.py --server.port 8501 --server.headless true

pause
