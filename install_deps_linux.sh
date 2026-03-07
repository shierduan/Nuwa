#!/bin/bash
# 女娲依赖安装脚本 (Linux)
# 用于在 Linux 系统上安装所有必需的依赖

set -e

echo "🔧 开始安装女娲依赖..."

# 检查 Python 版本
python3 --version || { echo "❌ 错误：未找到 Python 3"; exit 1; }

# 检查 pip
pip3 --version || { echo "❌ 错误：未找到 pip"; exit 1; }

# 升级 pip
echo "📦 升级 pip..."
pip3 install --upgrade pip

# 安装系统级依赖（Ubuntu/Debian）
if [ -f /etc/debian_version ]; then
    echo "📦 安装系统级依赖..."
    sudo apt-get update || true
    sudo apt-get install -y python3-dev build-essential libpq-dev
fi

# 安装 Python 依赖
echo "📦 安装 Python 依赖..."
pip3 install -r requirements.txt

# 验证安装
echo "\n✅ 验证安装..."
python3 -c "import pyarrow; print('✅ PyArrow:', pyarrow.__version__)" || echo "⚠️  PyArrow 安装失败"
python3 -c "import lancedb; print('✅ LanceDB:', lancedb.__version__)" || echo "⚠️  LanceDB 安装失败"
python3 -c "import sentence_transformers; print('✅ Sentence Transformers')" || echo "⚠️  Sentence Transformers 安装失败"

echo "\n✅ 依赖安装完成！"
echo "\n提示：如果遇到 pyarrow 安装失败，请确保已安装 python3-dev 和 build-essential"
