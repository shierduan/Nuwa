# 女娲核心系统 - Dockerfile
# 基于Python 3.11轻量镜像
FROM python:3.11-slim

# 设置工作目录
WORKDIR /app

# 设置环境变量
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    NUWA_ENV=production \
    LOG_LEVEL=INFO

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 复制依赖文件
COPY requirements.txt .
COPY pyproject.toml . 2>/dev/null || true

# 安装Python依赖
RUN pip install --no-cache-dir -r requirements.txt

# 复制项目代码
COPY nuwa_core/ ./nuwa_core/
COPY tests/ ./tests/
COPY scripts/ ./scripts/
COPY web/ ./web/
COPY config/ ./config/
COPY *.py ./
COPY *.md ./
COPY LICENSE ./
COPY chat_channels_example_config.yaml ./

# 创建数据目录
RUN mkdir -p /app/data /app/logs /app/management-scripts/scripts/data/nuwa

# 复制状态文件
COPY management-scripts/scripts/data/nuwa/state.json /app/management-scripts/scripts/data/nuwa/state.json 2>/dev/null || true

# 暴露端口（HTTP/WebSocket）
EXPOSE 8000 8001 8080

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python health_check.py || exit 1

# 启动命令
CMD ["python", "main_async.py"]