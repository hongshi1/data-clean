@echo off
chcp 65001 >nul
title SRS微调数据集构建平台 - 公网共享启动器
echo ============================================================
echo   SRS微调数据集构建平台(一致性校验增强版) - 公网共享
echo   公网地址: https://srs-demo-2026.loca.lt
echo   (固定子域名, 重启后地址不变)
echo ============================================================
echo.

cd /d D:\study\hengxiang\data_clean

echo [1/3] 检查并启动后端 API (127.0.0.1:8300)...
netstat -ano | findstr ":8300 " | findstr "LISTENING" >nul 2>&1
if errorlevel 1 (
    start "SRS后端8300" /min "D:\software\anaconda\python.exe" -X utf8 server\main.py
    echo       已启动新进程
) else (
    echo       已在运行, 跳过
)

echo [2/3] 检查并启动反向代理 (127.0.0.1:8399, 静态HTML+API转发)...
netstat -ano | findstr ":8399 " | findstr "LISTENING" >nul 2>&1
if errorlevel 1 (
    start "SRS代理8399" /min "D:\software\anaconda\python.exe" -X utf8 tools\reverse_proxy.py
    echo       已启动新进程
) else (
    echo       已在运行, 跳过
)

echo [3/3] 启动公网隧道 (localtunnel 固定子域名)...
tasklist /fi "imagename eq node.exe" /fo csv | findstr /i "localtunnel" >nul 2>&1
if errorlevel 1 (
    start "SRS公网隧道" /min "C:\nvm4w\nodejs\node.exe" "D:\software\node-v12.13.1-win-x64\node_global\node_modules\localtunnel\bin\lt.js" --port 8399 --subdomain srs-demo-2026
    echo       已启动新进程
) else (
    echo       已在运行, 跳过
)

echo.
timeout /t 10 >nul
echo ============================================================
echo  启动完成!
echo.
echo  把这个链接发给别人即可:
echo      https://srs-demo-2026.loca.lt
echo.
echo  注意:
echo   1. 访客首次打开会看到一个提示页, 在输入框输入页面
echo      上显示的"访客自己的公网IP"即可进入(每个浏览器一次)
echo   2. 页面里的"实时召回引擎查询"功能走同源API, 公网可用
echo   3. 需保持本机不睡眠; 停止服务请关闭3个最小化窗口
echo   4. 断网/重启后, 双击本脚本即可恢复, 地址不变
echo ============================================================
pause
