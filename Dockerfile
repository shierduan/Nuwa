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
    LOG_LEVEL=INFO \
    NUWA_WS_HOST=0.0.0.0 \
    NUWA_WS_PORT=8766 \
    NUWA_METRICS_HOST=0.0.0.0 \
    NUWA_METRICS_PORT=8080

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 复制依赖文件
COPY requirements.txt .

# 安装Python依赖
RUN pip install --no-cache-dir -r requirements.txt

# 复制项目代码
COPY nuwa_core/ ./nuwa_core/
COPY scripts/ ./scripts/
COPY skills/ ./skills/
COPY config/ ./config/
COPY *.py ./
COPY *.md ./
COPY LICENSE ./
COPY chat_channels_example_config.yaml ./

# 创建数据目录
RUN mkdir -p /app/data /app/logs

# 暴露端口（WebSocket / 指标JSON / 指标Prometheus格式）
EXPOSE 8766 8080 8081

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python health_check.py || exit 1

# 启动命令（服务器模式，为前端/渠道提供 WebSocket 服务）
CMD ["python", "server_async.py"]