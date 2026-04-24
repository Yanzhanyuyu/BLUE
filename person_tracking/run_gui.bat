@echo off
chcp 65001 >nul
echo 正在启动人员检测跟踪系统 GUI...
echo.
python run_gui.py %*
