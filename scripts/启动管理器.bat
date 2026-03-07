@echo off
chcp 65001 >nul
title Nuwa Manager

echo Starting Nuwa Manager...
start "" "node_modules\.bin\electron.cmd" "启动管理器.html"
timeout /t 2