#!/bin/bash
# 快速部署脚本 - 一键安装并配置 Xray Client
# 自动适配网络环境

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# 检查 root
if [ "$EUID" -ne 0 ]; then
    echo -e "${RED}请使用 root 权限运行此脚本${NC}"
    exit 1
fi

echo -e "${BLUE}"
echo "╔══════════════════════════════════════════════════════╗"
echo "║     Xray Client 快速部署脚本                          ║"
echo "║     支持 JustMySocks 订阅                             ║"
echo "║     自动适配网络环境                                  ║"
echo "╚══════════════════════════════════════════════════════╝"
echo -e "${NC}"

# 下载 install.sh（尝试多个源）
download_install_script() {
    local urls=(
        "https://raw.githubusercontent.com/your-repo/xray-client/main/install.sh"
        "https://cdn.jsdelivr.net/gh/your-repo/xray-client@main/install.sh"
        "https://ghproxy.com/https://raw.githubusercontent.com/your-repo/xray-client/main/install.sh"
        "https://gitee.com/your-repo/xray-client/raw/main/install.sh"
    )
    
    echo "获取安装脚本..."
    for url in "${urls[@]}"; do
        if curl -fsSL --connect-timeout 10 -o /tmp/xray-client-install.sh "$url" 2>/dev/null; then
            echo -e "${GREEN}✓ 下载成功${NC}"
            return 0
        fi
    done
    
    return 1
}

# 如果本地有 install.sh 就使用本地的
if [ -f "install.sh" ]; then
    echo -e "${YELLOW}使用本地 install.sh${NC}"
    cp install.sh /tmp/xray-client-install.sh
elif ! download_install_script; then
    echo -e "${RED}无法下载安装脚本，请检查网络连接${NC}"
    echo ""
    echo "你可以:"
    echo "  1. 手动下载 install.sh 到当前目录"
    echo "  2. 使用离线安装包"
    echo "  3. 检查网络连接"
    exit 1
fi

# 交互式配置
echo ""
echo -e "${YELLOW}请输入 JustMySocks 订阅链接:${NC}"
echo "(格式: https://justmysocks.net/members/getsub.php?service=xxx&id=xxx-xxx-xxx)"
read -p "> " SUB_URL

if [ -z "$SUB_URL" ]; then
    echo -e "${RED}订阅链接不能为空${NC}"
    exit 1
fi

echo ""
echo -e "${YELLOW}请输入本地 SOCKS5 代理端口 (默认 10808):${NC}"
read -p "> " SOCKS_PORT
SOCKS_PORT=${SOCKS_PORT:-10808}

echo ""
echo -e "${YELLOW}请输入本地 HTTP 代理端口 (默认 10809):${NC}"
read -p "> " HTTP_PORT
HTTP_PORT=${HTTP_PORT:-10809}

# 执行安装
echo ""
echo -e "${YELLOW}开始安装...${NC}"
bash /tmp/xray-client-install.sh

# 检查安装结果
if [ ! -f '/usr/local/bin/xray' ]; then
    echo -e "${RED}安装失败${NC}"
    exit 1
fi

# 写入配置
cat > /etc/xray-client/config.ini << EOF
[subscription]
url = $SUB_URL
interval = 3600

[local]
socks_port = $SOCKS_PORT
http_port = $HTTP_PORT

[node]
selected = 0
EOF

echo -e "${GREEN}配置已写入${NC}"

# 更新订阅
echo ""
echo -e "${YELLOW}正在更新订阅...${NC}"
xray-client update

# 重启 Xray 服务
echo ""
echo -e "${YELLOW}启动 Xray 服务...${NC}"
xray-client restart

# 等待服务启动
sleep 2

# 检查状态
if systemctl is-active --quiet xray; then
    echo ""
    echo -e "${GREEN}╔══════════════════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║                 安装成功!                             ║${NC}"
    echo -e "${GREEN}╚══════════════════════════════════════════════════════╝${NC}"
    echo ""
    echo -e "${YELLOW}代理地址:${NC}"
    echo "  SOCKS5: 127.0.0.1:$SOCKS_PORT"
    echo "  HTTP:   127.0.0.1:$HTTP_PORT"
    echo ""
    echo -e "${YELLOW}常用命令:${NC}"
    echo "  xray-client list         # 查看节点列表"
    echo "  xray-client select -i 0  # 切换到第一个节点"
    echo "  xray-client restart      # 重启 Xray 服务"
    echo "  xray-client status       # 查看服务状态"
    echo "  xray-client test         # 测试代理连接"
    echo ""
    echo -e "${YELLOW}查看日志:${NC}"
    echo "  tail -f /var/log/xray/error.log"
    echo "  tail -f /var/log/xray-client/client.log"
    echo ""
    echo -e "${YELLOW}测试代理:${NC}"
    echo "  export https_proxy=http://127.0.0.1:$HTTP_PORT"
    echo "  curl -s https://www.google.com | head -5"
    echo ""
else
    echo -e "${RED}服务启动失败，请检查日志:${NC}"
    echo "  journalctl -u xray -n 20"
    echo "  tail -n 20 /var/log/xray/error.log"
    exit 1
fi

# 清理
rm -f /tmp/xray-client-install.sh
