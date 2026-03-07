@echo off
chcp 65001 >nul
echo 启动女娲管理工具...
echo 输入 'help' 查看可用命令，'exit' 退出
echo 使用上下箭头浏览历史命令，回车执行
echo.
python management-scripts/scripts/nuwactl.py
pause