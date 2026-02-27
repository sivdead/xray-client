# Xray Client Docker Image
FROM python:3.9-slim

LABEL maintainer="sivdead"
LABEL description="Xray Client with JustMySocks support"

# 安装系统依赖 + Python 依赖（合并层减小镜像）
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    unzip \
    iproute2 \
    && rm -rf /var/lib/apt/lists/* \
    && pip install --no-cache-dir flask pyyaml

# 下载并安装 Xray（使用 latest 自动获取最新版）
ARG XRAY_VERSION=latest
RUN set -eux; \
    if [ "$XRAY_VERSION" = "latest" ]; then \
        XRAY_VERSION=$(curl -fsSL https://api.github.com/repos/XTLS/Xray-core/releases/latest | grep '"tag_name"' | head -1 | cut -d'"' -f4); \
    fi; \
    ARCH=$(uname -m); \
    case "$ARCH" in \
        x86_64)  XRAY_ARCH="64" ;; \
        aarch64) XRAY_ARCH="arm64-v8a" ;; \
        *)       echo "Unsupported arch: $ARCH" && exit 1 ;; \
    esac; \
    curl -fsSL -o /tmp/xray.zip \
        "https://github.com/XTLS/Xray-core/releases/download/${XRAY_VERSION}/Xray-linux-${XRAY_ARCH}.zip" \
    && unzip /tmp/xray.zip -d /usr/local/bin/ \
    && rm /tmp/xray.zip \
    && chmod +x /usr/local/bin/xray

# 下载 GeoIP/GeoSite（修复 || 优先级问题，用子 shell 隔离）
RUN mkdir -p /usr/local/share/xray \
    && (curl -fsSL -o /usr/local/share/xray/geoip.dat \
        https://github.com/v2fly/geoip/releases/latest/download/geoip.dat \
        || curl -fsSL -o /usr/local/share/xray/geoip.dat \
        https://ghproxy.com/https://github.com/v2fly/geoip/releases/latest/download/geoip.dat) \
    && (curl -fsSL -o /usr/local/share/xray/geosite.dat \
        https://github.com/v2fly/domain-list-community/releases/latest/download/dlc.dat \
        || curl -fsSL -o /usr/local/share/xray/geosite.dat \
        https://ghproxy.com/https://github.com/v2fly/domain-list-community/releases/latest/download/dlc.dat)

# 创建配置目录
RUN mkdir -p /etc/xray-client/subscription \
    /var/log/xray \
    /var/log/xray-client

# 复制脚本
COPY xray-client.py /usr/local/bin/xray-client
COPY web-ui.py /usr/local/bin/xray-webui
COPY docker-entrypoint.sh /entrypoint.sh

RUN chmod +x /usr/local/bin/xray-client /usr/local/bin/xray-webui /entrypoint.sh

# 环境变量
ENV SUB_URL=""
ENV NODE_INDEX=0
ENV SOCKS_PORT=10808
ENV HTTP_PORT=10809
ENV WEB_UI=false
ENV WEB_UI_PORT=5000

# 暴露端口
EXPOSE 10808/tcp 10809/tcp 5000/tcp

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD curl -fsS --connect-timeout 5 -x http://127.0.0.1:10809 https://www.google.com > /dev/null || exit 1

ENTRYPOINT ["/entrypoint.sh"]
