#!/bin/bash
set -e

# 如果设置了订阅链接，自动配置
if [ -n "$SUB_URL" ]; then
    echo "Configuring subscription..."
    cat > /etc/xray-client/config.ini << EOF
[subscription]
url = $SUB_URL
interval = 3600

[local]
socks_port = ${SOCKS_PORT:-10808}
http_port = ${HTTP_PORT:-10809}

[node]
selected = ${NODE_INDEX:-0}
EOF

    # 更新订阅
    echo "Updating subscription..."
    xray-client update || true
    
    # 生成配置
    xray-client select -i ${NODE_INDEX:-0} || true
fi

# 启动 Web UI（如果启用）
if [ "$WEB_UI" = "true" ]; then
    echo "Starting Web UI on port ${WEB_UI_PORT:-5000}..."
    python3 /usr/local/bin/xray-webui &
fi

# 前台启动 Xray
echo "Starting Xray..."
exec /usr/local/bin/xray run -config /usr/local/etc/xray/config.json
