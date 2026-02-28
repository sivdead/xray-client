#!/bin/bash
# Xray Client 安装脚本 for TencentOS/CentOS/RHEL
# 复用 Xray 官方 install-release.sh 安装核心
# 支持多种网络环境：直连、代理、离线、镜像源

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# 使用官方安装脚本配置
export DAT_PATH='/usr/local/share/xray'
export JSON_PATH='/usr/local/etc/xray'

# 我们的配置目录
CLIENT_CONFIG_DIR="/etc/xray-client"
CLIENT_LOG_DIR="/var/log/xray-client"

# GitHub 代理镜像（按速度排序）
GH_MIRRORS=(
    "https://ghfast.top/"
    "https://ghproxy.com/"
    "https://mirror.ghproxy.com/"
    "https://gh.api.99988866.xyz/"
    "https://ghps.cc/"
    "https://gh-proxy.com/"
)

# 检测是否在中国大陆
is_in_china() {
    # 通过检测 baidu.com 和 google.com 的响应来判断
    if curl -s --connect-timeout 3 -o /dev/null https://www.baidu.com && \
       ! curl -s --connect-timeout 3 -o /dev/null https://www.google.com 2>/dev/null; then
        return 0
    fi
    return 1
}

# 测试 GitHub 连通性
check_github() {
    curl -s --connect-timeout 5 -o /dev/null https://github.com/XTLS/Xray-core/releases/latest 2>/dev/null
}

# 获取可用的 GitHub 代理
get_working_mirror() {
    echo "测试 GitHub 镜像源..."
    for mirror in "${GH_MIRRORS[@]}"; do
        if curl -s --connect-timeout 5 -o /dev/null "${mirror}https://github.com/XTLS/Xray-core/releases/latest" 2>/dev/null; then
            echo -e "${GREEN}找到可用镜像: $mirror${NC}"
            echo "$mirror"
            return 0
        fi
    done
    echo ""
    return 1
}

# 带重试的下载函数
download_with_retry() {
    local url="$1"
    local output="$2"
    local max_retries=3
    local retry_count=0
    
    while [ $retry_count -lt $max_retries ]; do
        if curl -fsSL --connect-timeout 15 --max-time 60 -o "$output" "$url" 2>/dev/null; then
            return 0
        fi
        retry_count=$((retry_count + 1))
        echo -e "${YELLOW}下载失败，第 $retry_count 次重试...${NC}"
        sleep 2
    done
    return 1
}

# 下载文件（自动选择镜像）
download_file() {
    local url="$1"
    local output="$2"
    local use_mirror="${3:-auto}"
    
    # 如果指定不使用镜像，直接下载
    if [ "$use_mirror" = "no" ]; then
        download_with_retry "$url" "$output"
        return $?
    fi
    
    # 尝试直连
    if check_github; then
        echo "GitHub 可直连，直接下载..."
        if download_with_retry "$url" "$output"; then
            return 0
        fi
    fi
    
    # 尝试镜像
    local mirror
    mirror=$(get_working_mirror)
    if [ -n "$mirror" ]; then
        echo "使用镜像下载..."
        if download_with_retry "${mirror}${url}" "$output"; then
            return 0
        fi
    fi
    
    return 1
}

echo -e "${BLUE}"
echo "╔══════════════════════════════════════════════════════╗"
echo "║     Xray Client 安装脚本                              ║"
echo "║     支持 JustMySocks 订阅                             ║"
echo "║     自动适配网络环境                                  ║"
echo "╚══════════════════════════════════════════════════════╝"
echo -e "${NC}"

# 检查 root
if [ "$EUID" -ne 0 ]; then
    echo -e "${RED}请使用 root 权限运行此脚本${NC}"
    exit 1
fi

# 检测系统
if [ -f /etc/os-release ]; then
    . /etc/os-release
    OS=$ID
    echo -e "${YELLOW}检测到操作系统: $OS${NC}"
else
    echo -e "${RED}无法检测操作系统类型${NC}"
    exit 1
fi

# 检测网络环境（如果外部已设置 NETWORK_MODE 则跳过检测）
echo ""
if [ -n "$NETWORK_MODE" ]; then
    echo -e "${YELLOW}使用预设网络模式: ${NC}$NETWORK_MODE"
elif check_github; then
    echo -e "${GREEN}✓ GitHub 可直连${NC}"
    NETWORK_MODE="direct"
else
    echo -e "${YELLOW}✗ GitHub 不可直连，尝试使用镜像源...${NC}"
    MIRROR_URL=$(get_working_mirror)
    if [ -n "$MIRROR_URL" ]; then
        NETWORK_MODE="mirror"
        echo -e "${GREEN}✓ 将使用镜像源: $MIRROR_URL${NC}"
    else
        echo -e "${RED}✗ 无法连接 GitHub，也未找到可用镜像${NC}"
        echo ""
        echo -e "${YELLOW}请选择安装方式:${NC}"
        echo "  1) 离线安装 - 使用本地已下载的 Xray 二进制文件"
        echo "  2) 代理安装 - 设置 HTTP 代理后重试"
        echo "  3) 退出安装"
        read -p "请选择 [1/2/3]: " choice
        
        case $choice in
            1)
                NETWORK_MODE="offline"
                ;;
            2)
                read -p "请输入 HTTP 代理地址 (如 http://127.0.0.1:10809): " proxy_url
                export http_proxy="$proxy_url"
                export https_proxy="$proxy_url"
                if check_github; then
                    echo -e "${GREEN}✓ 通过代理可访问 GitHub${NC}"
                    NETWORK_MODE="proxy"
                else
                    echo -e "${RED}✗ 通过代理仍无法访问 GitHub${NC}"
                    exit 1
                fi
                ;;
            *)
                exit 1
                ;;
        esac
    fi
fi

# ==================== 步骤1: 安装 Xray ====================
echo ""
echo -e "${YELLOW}[1/5] 安装 Xray 核心...${NC}"

install_xray_offline() {
    echo -e "${YELLOW}离线安装模式${NC}"
    echo "请确保已准备好以下文件："
    echo "  1. Xray 二进制文件 -> /tmp/xray"
    echo "  2. 官方 install-release.sh -> /tmp/install-release.sh (可选)"
    echo ""
    read -p "文件已准备好? [y/N]: " confirm
    
    if [ "$confirm" != "y" ] && [ "$confirm" != "Y" ]; then
        echo "请手动下载 Xray 二进制文件到 /tmp/xray"
        echo "下载地址: https://github.com/XTLS/Xray-core/releases"
        exit 1
    fi
    
    if [ ! -f "/tmp/xray" ]; then
        echo -e "${RED}错误: 未找到 /tmp/xray${NC}"
        exit 1
    fi
    
    # 手动安装 Xray
    mkdir -p /usr/local/bin
    mkdir -p /usr/local/etc/xray
    mkdir -p /usr/local/share/xray
    mkdir -p /var/log/xray
    
    cp /tmp/xray /usr/local/bin/xray
    chmod +x /usr/local/bin/xray
    
    # 创建 systemd 服务
    cat > /etc/systemd/system/xray.service << 'EOF'
[Unit]
Description=Xray Service
Documentation=https://github.com/xtls
After=network.target nss-lookup.target

[Service]
User=nobody
CapabilityBoundingSet=CAP_NET_ADMIN CAP_NET_BIND_SERVICE
AmbientCapabilities=CAP_NET_ADMIN CAP_NET_BIND_SERVICE
NoNewPrivileges=true
ExecStart=/usr/local/bin/xray run -config /usr/local/etc/xray/config.json
Restart=on-failure
RestartPreventExitStatus=23
LimitNPROC=10000
LimitNOFILE=1000000

[Install]
WantedBy=multi-user.target
EOF
    
    systemctl daemon-reload
    echo -e "${GREEN}Xray 离线安装完成${NC}"
}

if [ "$NETWORK_MODE" = "offline" ]; then
    install_xray_offline
else
    # 使用官方脚本安装
    echo "正在获取官方安装脚本..."
    
    INSTALL_SCRIPT_URL="https://github.com/XTLS/Xray-install/raw/main/install-release.sh"
    INSTALL_SCRIPT_PATH="/tmp/install-release.sh"
    
    if download_file "$INSTALL_SCRIPT_URL" "$INSTALL_SCRIPT_PATH" "$NETWORK_MODE"; then
        chmod +x "$INSTALL_SCRIPT_PATH"
        echo "执行官方安装脚本..."
        bash "$INSTALL_SCRIPT_PATH" install --without-geodata
    else
        echo -e "${RED}下载官方安装脚本失败${NC}"
        echo "请手动下载后重试，或使用离线模式"
        exit 1
    fi
    
    rm -f "$INSTALL_SCRIPT_PATH"
fi

# 检查 Xray 是否安装成功
if [ ! -f '/usr/local/bin/xray' ]; then
    echo -e "${RED}Xray 安装失败${NC}"
    exit 1
fi

echo -e "${GREEN}Xray 核心安装成功${NC}"

# ==================== 步骤2: 安装 geodata ====================
echo ""
echo -e "${YELLOW}[2/5] 安装 GeoIP/GeoSite 数据...${NC}"

if [ -f "$DAT_PATH/geoip.dat" ] && [ -f "$DAT_PATH/geosite.dat" ]; then
    echo -e "${GREEN}GeoIP/GeoSite 数据已存在${NC}"
elif [ "$NETWORK_MODE" = "offline" ]; then
    echo "离线模式跳过 geodata 安装"
    echo "可手动下载后放到 $DAT_PATH/"
else
    mkdir -p "$DAT_PATH"
    
    # 使用官方脚本安装 geodata
    if [ -f "/tmp/install-release.sh" ]; then
        bash "/tmp/install-release.sh" install-geodata 2>/dev/null || true
    fi
    
    # 如果失败，尝试直接下载
    if [ ! -f "$DAT_PATH/geoip.dat" ]; then
        echo "尝试直接下载 geodata..."
        GEOIP_URL="https://github.com/v2fly/geoip/releases/latest/download/geoip.dat"
        GEOSITE_URL="https://github.com/v2fly/domain-list-community/releases/latest/download/dlc.dat"
        
        if download_file "$GEOIP_URL" "$DAT_PATH/geoip.dat" "$NETWORK_MODE"; then
            echo -e "${GREEN}✓ GeoIP 下载成功${NC}"
        else
            echo -e "${YELLOW}✗ GeoIP 下载失败${NC}"
        fi
        
        if download_file "$GEOSITE_URL" "$DAT_PATH/geosite.dat" "$NETWORK_MODE"; then
            echo -e "${GREEN}✓ GeoSite 下载成功${NC}"
        else
            echo -e "${YELLOW}✗ GeoSite 下载失败${NC}"
        fi
    fi
fi

# ==================== 步骤3: 安装 Python（按需）====================
echo ""
echo -e "${YELLOW}[3/5] 检查 Python 环境...${NC}"

# 检查是否有预编译的可执行文件（离线包或在线下载）
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
HAS_EXECUTABLE=false
if [ -f "$SCRIPT_DIR/xray-client" ]; then
    if command -v file &> /dev/null && file "$SCRIPT_DIR/xray-client" | grep -q "ELF"; then
        HAS_EXECUTABLE=true
    elif [ -x "$SCRIPT_DIR/xray-client" ] && head -c 4 "$SCRIPT_DIR/xray-client" 2>/dev/null | grep -q $'\x7fELF'; then
        # file 命令不可用时，通过 ELF magic bytes 判断
        HAS_EXECUTABLE=true
    fi
fi
if [ "$HAS_EXECUTABLE" = true ]; then
    echo -e "${GREEN}检测到预编译可执行文件，跳过 Python 安装${NC}"
fi

install_python_deps() {
    if ! command -v python3 &> /dev/null; then
        echo "安装 Python3..."
        if command -v yum &> /dev/null; then
            yum install -y python3 || yum install -y python36
        elif command -v apt &> /dev/null; then
            apt update && apt install -y python3
        elif command -v dnf &> /dev/null; then
            dnf install -y python3
        else
            echo -e "${RED}无法安装 Python3，请手动安装${NC}"
            exit 1
        fi
    fi

    # 检查 pip
    if ! python3 -m pip --version &> /dev/null 2>&1; then
        echo "安装 pip..."
        python3 -m ensurepip --upgrade 2>/dev/null || {
            if command -v yum &> /dev/null; then
                yum install -y python3-pip
            elif command -v apt &> /dev/null; then
                apt install -y python3-pip
            fi
        }
    fi

    echo -e "${GREEN}Python 安装完成${NC}"
}

if [ "$HAS_EXECUTABLE" = false ]; then
    install_python_deps
fi

# ==================== 步骤4: 创建客户端脚本 ====================
echo ""
echo -e "${YELLOW}[4/5] 创建 Xray Client 管理脚本...${NC}"

# 创建目录
mkdir -p "$CLIENT_CONFIG_DIR/subscription"
mkdir -p "$CLIENT_LOG_DIR"

SCRIPT_BASE_URL="https://raw.githubusercontent.com/sivdead/xray-client/master"

if [ "$HAS_EXECUTABLE" = true ]; then
    # ---- 使用预编译可执行文件（无需 Python）----
    echo "安装预编译可执行文件..."
    cp "$SCRIPT_DIR/xray-client" /usr/local/bin/xray-client
    chmod +x /usr/local/bin/xray-client
    echo -e "${GREEN}✓ xray-client 可执行文件安装成功${NC}"

    if [ -f "$SCRIPT_DIR/xray-tui" ]; then
        cp "$SCRIPT_DIR/xray-tui" /usr/local/bin/xray-tui
        chmod +x /usr/local/bin/xray-tui
        echo -e "${GREEN}✓ xray-tui 可执行文件安装成功${NC}"
    fi
else
    # ---- 使用 Python 脚本 ----
    echo "正在下载 xray-client 脚本..."
    if download_file "${SCRIPT_BASE_URL}/xray-client.py" "/usr/local/bin/xray-client" "$NETWORK_MODE"; then
        echo -e "${GREEN}✓ xray-client 脚本下载成功${NC}"
    else
        echo -e "${RED}下载 xray-client 脚本失败，使用本地备份...${NC}"
        if [ -f "$SCRIPT_DIR/xray-client.py" ]; then
            cp "$SCRIPT_DIR/xray-client.py" /usr/local/bin/xray-client
            echo -e "${GREEN}✓ 使用本地 xray-client.py${NC}"
        else
            echo -e "${RED}无法获取 xray-client 脚本，安装失败${NC}"
            exit 1
        fi
    fi

    chmod +x /usr/local/bin/xray-client

    # 下载 TUI 脚本（可选）
    echo "正在下载 TUI 脚本..."
    if download_file "${SCRIPT_BASE_URL}/tui.py" "/usr/local/bin/xray-tui" "$NETWORK_MODE"; then
        chmod +x /usr/local/bin/xray-tui
        echo -e "${GREEN}✓ TUI 脚本下载成功${NC}"
    else
        if [ -f "$SCRIPT_DIR/tui.py" ]; then
            cp "$SCRIPT_DIR/tui.py" /usr/local/bin/xray-tui
            chmod +x /usr/local/bin/xray-tui
            echo -e "${GREEN}✓ 使用本地 tui.py${NC}"
        else
            echo -e "${YELLOW}TUI 脚本未找到，跳过（可稍后手动安装）${NC}"
        fi
    fi

    # 安装 Python 依赖（用于 Clash 格式解析）
    echo "安装 Python 依赖..."
    if ! python3 -m pip install --quiet pyyaml 2>&1; then
        echo -e "${YELLOW}可选依赖 pyyaml 安装失败（Clash 格式解析可能不可用，核心功能不受影响）${NC}"
    fi
fi

# ==================== 步骤5: 创建配置文件 ====================
echo ""
echo -e "${YELLOW}[5/5] 创建配置文件...${NC}"

# 创建配置目录
mkdir -p "$CLIENT_CONFIG_DIR/subscription"

# 创建默认配置
cat > "$CLIENT_CONFIG_DIR/config.ini" << 'CONFIG_EOF'
[subscription]
# JustMySocks 订阅链接
url = 

# 自动更新间隔（秒），默认1小时
interval = 3600

[local]
# 本地 SOCKS5 代理端口
socks_port = 10808

# 本地 HTTP 代理端口
http_port = 10809

[node]
# 默认选择的节点索引
selected = 0
CONFIG_EOF

# 确保日志目录存在
mkdir -p /var/log/xray

# 安装 systemd timer（定时更新）
echo ""
echo -e "${YELLOW}[6/6] 安装定时更新服务...${NC}"

cat > /etc/systemd/system/xray-client-update.service << 'EOF'
[Unit]
Description=Xray Client Subscription Update
After=network.target

[Service]
Type=oneshot
ExecStart=/usr/local/bin/xray-client update
ExecStartPost=/usr/local/bin/xray-client restart
StandardOutput=journal
StandardError=journal
EOF

cat > /etc/systemd/system/xray-client-update.timer << 'EOF'
[Unit]
Description=Xray Client Subscription Update Timer
Documentation=https://github.com/sivdead/xray-client

[Timer]
OnCalendar=daily
RandomizedDelaySec=3600
Persistent=true

[Install]
WantedBy=timers.target
EOF

systemctl daemon-reload
systemctl enable xray-client-update.timer
systemctl start xray-client-update.timer

echo -e "${GREEN}定时更新服务已安装${NC}"

echo ""
echo -e "${GREEN}╔══════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║                 安装成功!                             ║${NC}"
echo -e "${GREEN}╚══════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${YELLOW}网络模式: ${NC}$NETWORK_MODE"
echo ""
echo -e "${YELLOW}使用说明:${NC}"
echo ""
echo "1. 编辑配置文件添加订阅链接:"
echo -e "   ${GREEN}vi /etc/xray-client/config.ini${NC}"
echo ""
echo "   修改 url = 为你的 JustMySocks 订阅链接"
echo ""
echo "2. 更新订阅并启动服务:"
echo -e "   ${GREEN}xray-client update${NC}     # 更新订阅"
echo -e "   ${GREEN}xray-client restart${NC}    # 重启 Xray 应用配置"
echo ""
echo "3. 其他常用命令:"
echo -e "   ${GREEN}xray-client list${NC}       # 查看节点列表"
echo -e "   ${GREEN}xray-client select -i 0${NC} # 切换到第1个节点"
echo -e "   ${GREEN}xray-client status${NC}     # 查看 Xray 状态"
echo -e "   ${GREEN}xray-client test${NC}       # 测试代理连接"
echo ""
echo -e "${YELLOW}代理地址:${NC}"
echo "  SOCKS5: 127.0.0.1:10808"
echo "  HTTP:   127.0.0.1:10809"
echo ""
echo -e "${YELLOW}日志文件:${NC}"
echo "  Xray:   /var/log/xray/error.log"
echo "  Client: /var/log/xray-client/client.log"
echo ""
echo -e "${YELLOW}如果无法连接 GitHub，可使用以下方式:${NC}"
echo "  1. 设置 HTTP 代理: export https_proxy=http://127.0.0.1:10809"
echo "  2. 手动下载 Xray 到 /tmp/xray 后重新运行安装脚本选择离线模式"
echo "  3. 使用镜像源自动安装（脚本已内置多个镜像）"
echo ""
