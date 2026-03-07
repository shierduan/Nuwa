@echo off
REM 女娲依赖安装脚本 (Windows)
REM 用于在 Windows 系统上安装所有必需的依赖

echo 🔧 开始安装女娲依赖...

REM 检查 Python 版本
python --version >nul 2>&1 || { echo "❌ 错误：未找到 Python"; exit /b 1 }

REM 检查 pip
pip --version >nul 2>&1 || { echo "❌ 错误：未找到 pip"; exit /b 1 }

REM 升级 pip
echo 📦 升级 pip...
python -m pip install --upgrade pip

REM 安装 Python 依赖
echo 📦 安装 Python 依赖...
pip install -r requirements.txt

REM 验证安装
echo.
echo ✅ 验证安装...
python -c "import pyarrow; print('✅ PyArrow:', pyarrow.__version__)" || echo "⚠️  PyArrow 安装失败"
python -c "import lancedb; print('✅ LanceDB:', lancedb.__version__)" || echo "⚠️  LanceDB 安装失败"
python -c "import sentence_transformers; print('✅ Sentence Transformers')" || echo "⚠️  Sentence Transformers 安装失败"

echo.
echo ✅ 依赖安装完成！
