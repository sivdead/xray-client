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
    local mirror=$(get_working_mirror)
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

# 检测网络环境
echo ""
echo -e "${YELLOW}检测网络环境...${NC}"
if check_github; then
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

# ==================== 步骤3: 安装 Python ====================
echo ""
echo -e "${YELLOW}[3/5] 安装 Python 和依赖...${NC}"

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

install_python_deps

# ==================== 步骤4: 创建客户端脚本 ====================
echo ""
echo -e "${YELLOW}[4/5] 创建 Xray Client 管理脚本...${NC}"

# 创建目录
mkdir -p "$CLIENT_CONFIG_DIR/subscription"
mkdir -p "$CLIENT_LOG_DIR"

# 嵌入 Python 脚本
cat > /usr/local/bin/xray-client << 'PYTHON_SCRIPT'
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Xray Client - 支持 JustMySocks 订阅
复用官方 Xray 安装，仅提供订阅管理功能
"""

import os
import sys
import json
import base64
import urllib.request
import urllib.parse
import subprocess
import time
import signal
import logging
import argparse
from datetime import datetime
from configparser import ConfigParser

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('/var/log/xray-client/client.log', encoding='utf-8')
    ]
)
logger = logging.getLogger(__name__)

# 使用官方 Xray 路径
XRAY_BIN = '/usr/local/bin/xray'
XRAY_CONFIG = '/usr/local/etc/xray/config.json'
CLIENT_CONFIG_DIR = '/etc/xray-client'
SUBSCRIPTION_FILE = os.path.join(CLIENT_CONFIG_DIR, 'subscription', 'nodes.json')
INI_FILE = os.path.join(CLIENT_CONFIG_DIR, 'config.ini')

# GitHub 代理镜像列表（按速度排序）
GH_MIRRORS = [
    "https://ghfast.top/",
    "https://ghproxy.com/",
    "https://mirror.ghproxy.com/",
    "https://gh.api.99988866.xyz/",
    "https://ghps.cc/",
    "https://gh-proxy.com/",
    ""
]

class XrayClient:
    def __init__(self):
        self.subscription_url = ""
        self.auto_update_interval = 3600
        self.selected_node = 0
        self.local_socks_port = 10808
        self.local_http_port = 10809
        self.github_mirror = ""
        
        self.load_config()
        self.detect_network()
    
    def detect_network(self):
        """检测网络并找到最佳镜像"""
        test_url = "https://github.com/XTLS/Xray-core/releases/latest"
        
        # 尝试直连
        try:
            req = urllib.request.Request(test_url, method='HEAD')
            req.add_header('User-Agent', 'Mozilla/5.0')
            urllib.request.urlopen(req, timeout=5)
            self.github_mirror = ""
            logger.info("GitHub 可直连")
            return
        except:
            pass
        
        # 尝试镜像
        for mirror in GH_MIRRORS[:-1]:  # 排除最后一个空字符串
            try:
                req = urllib.request.Request(mirror + test_url, method='HEAD')
                req.add_header('User-Agent', 'Mozilla/5.0')
                urllib.request.urlopen(req, timeout=5)
                self.github_mirror = mirror
                logger.info(f"使用 GitHub 镜像: {mirror}")
                return
            except:
                continue
        
        logger.warning("无法连接 GitHub 及镜像，在线功能将不可用")
    
    def load_config(self):
        """加载配置文件"""
        if os.path.exists(INI_FILE):
            config = ConfigParser()
            config.read(INI_FILE, encoding='utf-8')
            
            if 'subscription' in config:
                self.subscription_url = config['subscription'].get('url', '')
                self.auto_update_interval = config['subscription'].getint('interval', 3600)
            
            if 'local' in config:
                self.local_socks_port = config['local'].getint('socks_port', 10808)
                self.local_http_port = config['local'].getint('http_port', 10809)
            
            if 'node' in config:
                self.selected_node = config['node'].getint('selected', 0)
            
            logger.info("配置文件加载成功")
        else:
            logger.warning(f"配置文件不存在: {INI_FILE}")
    
    def save_subscription_data(self, data):
        """保存订阅数据"""
        os.makedirs(os.path.dirname(SUBSCRIPTION_FILE), exist_ok=True)
        with open(SUBSCRIPTION_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    
    def load_subscription_data(self):
        """加载订阅数据"""
        if os.path.exists(SUBSCRIPTION_FILE):
            with open(SUBSCRIPTION_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        return None
    
    def fetch_subscription(self):
        """获取订阅链接内容"""
        if not self.subscription_url:
            logger.error("未配置订阅链接")
            return None
        
        try:
            logger.info(f"正在获取订阅...")
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            
            req = urllib.request.Request(self.subscription_url, headers=headers)
            
            with urllib.request.urlopen(req, timeout=30) as response:
                content = response.read()
                
                try:
                    text = content.decode('utf-8')
                except:
                    text = content.decode('utf-8', errors='ignore')
                
                logger.info("订阅获取成功")
                return text
                
        except Exception as e:
            logger.error(f"获取订阅失败: {e}")
            return None
    
    def parse_base64(self, text):
        """解析 Base64 编码的订阅内容"""
        try:
            padding = 4 - len(text) % 4
            if padding != 4:
                text += '=' * padding
            
            decoded = base64.b64decode(text).decode('utf-8', errors='ignore')
            return decoded
        except Exception as e:
            logger.error(f"Base64 解码失败: {e}")
            return None
    
    def parse_vmess(self, url):
        """解析 VMess 链接"""
        try:
            b64_data = url[8:]  # 去掉 'vmess://'
            padding = 4 - len(b64_data) % 4
            if padding != 4:
                b64_data += '=' * padding
            
            json_str = base64.b64decode(b64_data).decode('utf-8', errors='ignore')
            node = json.loads(json_str)
            
            return {
                'type': 'vmess',
                'name': node.get('ps', 'unnamed'),
                'server': node.get('add', ''),
                'port': int(node.get('port', 0)),
                'uuid': node.get('id', ''),
                'alterId': int(node.get('aid', 0)),
                'security': node.get('scy', 'auto'),
                'network': node.get('net', 'tcp'),
                'tls': node.get('tls', ''),
                'sni': node.get('sni', ''),
                'host': node.get('host', ''),
                'path': node.get('path', '')
            }
        except Exception as e:
            logger.error(f"解析 VMess 失败: {e}")
            return None
    
    def parse_vless(self, url):
        """解析 VLESS 链接"""
        try:
            url = url[8:]  # 去掉 'vless://'
            
            if '#' in url:
                url, name = url.rsplit('#', 1)
                name = urllib.parse.unquote(name)
            else:
                name = 'unnamed'
            
            if '?' in url:
                main_part, params = url.split('?', 1)
            else:
                main_part, params = url, ''
            
            uuid, rest = main_part.split('@', 1)
            server, port = rest.rsplit(':', 1)
            port = int(port)
            
            param_dict = urllib.parse.parse_qs(params)
            
            return {
                'type': 'vless',
                'name': name,
                'server': server,
                'port': port,
                'uuid': uuid,
                'encryption': param_dict.get('encryption', ['none'])[0],
                'flow': param_dict.get('flow', [''])[0],
                'security': param_dict.get('security', [''])[0],
                'sni': param_dict.get('sni', [''])[0],
                'fp': param_dict.get('fp', [''])[0],
                'pbk': param_dict.get('pbk', [''])[0],
                'sid': param_dict.get('sid', [''])[0],
                'spx': param_dict.get('spx', [''])[0],
                'net_type': param_dict.get('type', ['tcp'])[0],
                'host': param_dict.get('host', [''])[0],
                'path': urllib.parse.unquote(param_dict.get('path', [''])[0])
            }
        except Exception as e:
            logger.error(f"解析 VLESS 失败: {e}")
            return None
    
    def parse_ss(self, url):
        """解析 Shadowsocks 链接"""
        try:
            if url.startswith('ss://'):
                url = url[5:]
            
            if '#' in url:
                url, name = url.rsplit('#', 1)
                name = urllib.parse.unquote(name)
            else:
                name = 'unnamed'
            
            if '@' not in url:
                padding = 4 - len(url) % 4
                if padding != 4:
                    url += '=' * padding
                decoded = base64.b64decode(url).decode('utf-8', errors='ignore')
                method_pass, server_port = decoded.split('@', 1)
                method, password = method_pass.split(':', 1)
                server, port = server_port.rsplit(':', 1)
            else:
                method_pass, server_port = url.split('@', 1)
                method, password = method_pass.split(':', 1)
                server, port = server_port.rsplit(':', 1)
            
            return {
                'type': 'shadowsocks',
                'name': name,
                'server': server,
                'port': int(port),
                'method': method,
                'password': password
            }
        except Exception as e:
            logger.error(f"解析 SS 失败: {e}")
            return None
    
    def parse_trojan(self, url):
        """解析 Trojan 链接"""
        try:
            url = url[9:]  # 去掉 'trojan://'
            
            if '#' in url:
                url, name = url.rsplit('#', 1)
                name = urllib.parse.unquote(name)
            else:
                name = 'unnamed'
            
            if '?' in url:
                main_part, params = url.split('?', 1)
            else:
                main_part, params = url, ''
            
            password, rest = main_part.split('@', 1)
            server, port = rest.rsplit(':', 1)
            port = int(port)
            
            param_dict = urllib.parse.parse_qs(params)
            
            return {
                'type': 'trojan',
                'name': name,
                'server': server,
                'port': port,
                'password': password,
                'sni': param_dict.get('sni', [''])[0]
            }
        except Exception as e:
            logger.error(f"解析 Trojan 失败: {e}")
            return None
    
    def parse_subscription(self, content):
        """解析订阅内容"""
        nodes = []
        
        if not content:
            return nodes
        
        decoded = self.parse_base64(content)
        
        if decoded:
            lines = decoded.strip().split('\n')
        else:
            lines = content.strip().split('\n')
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            node = None
            
            if line.startswith('vmess://'):
                node = self.parse_vmess(line)
            elif line.startswith('vless://'):
                node = self.parse_vless(line)
            elif line.startswith('ss://'):
                node = self.parse_ss(line)
            elif line.startswith('trojan://'):
                node = self.parse_trojan(line)
            
            if node:
                nodes.append(node)
                logger.info(f"解析节点: {node['name']}")
        
        logger.info(f"共解析到 {len(nodes)} 个节点")
        return nodes
    
    def generate_xray_config(self, node):
        """生成 Xray 配置文件"""
        
        config = {
            "log": {
                "loglevel": "warning",
                "access": "/var/log/xray/access.log",
                "error": "/var/log/xray/error.log"
            },
            "inbounds": [
                {
                    "tag": "socks",
                    "port": self.local_socks_port,
                    "listen": "127.0.0.1",
                    "protocol": "socks",
                    "sniffing": {
                        "enabled": True,
                        "destOverride": ["http", "tls", "quic"]
                    },
                    "settings": {
                        "auth": "noauth",
                        "udp": True,
                        "ip": "127.0.0.1"
                    }
                },
                {
                    "tag": "http",
                    "port": self.local_http_port,
                    "listen": "127.0.0.1",
                    "protocol": "http",
                    "sniffing": {
                        "enabled": True,
                        "destOverride": ["http", "tls", "quic"]
                    }
                }
            ],
            "outbounds": [],
            "routing": {
                "domainStrategy": "IPIfNonMatch",
                "rules": [
                    {
                        "type": "field",
                        "ip": ["geoip:private"],
                        "outboundTag": "direct"
                    },
                    {
                        "type": "field",
                        "domain": ["geosite:cn"],
                        "outboundTag": "direct"
                    },
                    {
                        "type": "field",
                        "ip": ["geoip:cn"],
                        "outboundTag": "direct"
                    }
                ]
            },
            "dns": {
                "servers": [
                    "https+local://1.1.1.1/dns-query",
                    "https+local://8.8.8.8/dns-query",
                    "localhost"
                ]
            }
        }
        
        outbound = self.create_outbound(node)
        config["outbounds"].append(outbound)
        config["outbounds"].append({
            "protocol": "freedom",
            "tag": "direct"
        })
        config["outbounds"].append({
            "protocol": "blackhole",
            "tag": "block"
        })
        
        config["routing"]["rules"].append({
            "type": "field",
            "network": "tcp,udp",
            "outboundTag": "proxy"
        })
        
        return config
    
    def create_outbound(self, node):
        """创建出站配置"""
        outbound = {
            "tag": "proxy",
            "protocol": node['type'],
            "settings": {},
            "streamSettings": {},
            "mux": {
                "enabled": False,
                "concurrency": -1
            }
        }
        
        node_type = node['type']
        
        if node_type == 'vmess':
            outbound["settings"] = {
                "vnext": [{
                    "address": node['server'],
                    "port": node['port'],
                    "users": [{
                        "id": node['uuid'],
                        "alterId": node.get('alterId', 0),
                        "security": node.get('security', 'auto'),
                        "level": 0
                    }]
                }]
            }
            
            stream_settings = {
                "network": node.get('network', 'tcp')
            }
            
            if node.get('tls'):
                stream_settings["security"] = node['tls']
                if node['tls'] == 'tls':
                    stream_settings["tlsSettings"] = {
                        "serverName": node.get('sni', node['server']),
                        "allowInsecure": False
                    }
            
            if node.get('network') == 'ws':
                stream_settings["wsSettings"] = {
                    "path": node.get('path', '/'),
                    "headers": {
                        "Host": node.get('host', node['server'])
                    }
                }
            elif node.get('network') == 'tcp' and node.get('host'):
                stream_settings["tcpSettings"] = {
                    "header": {
                        "type": "http",
                        "request": {
                            "path": [node.get('path', '/')],
                            "headers": {
                                "Host": [node.get('host', node['server'])]
                            }
                        }
                    }
                }
            
            outbound["streamSettings"] = stream_settings
            
        elif node_type == 'vless':
            outbound["settings"] = {
                "vnext": [{
                    "address": node['server'],
                    "port": node['port'],
                    "users": [{
                        "id": node['uuid'],
                        "encryption": node.get('encryption', 'none'),
                        "flow": node.get('flow', ''),
                        "level": 0
                    }]
                }]
            }
            
            net_type = node.get('net_type', 'tcp')
            stream_settings = {
                "network": net_type
            }
            
            security = node.get('security', '')
            if security:
                stream_settings["security"] = security
                
                if security == 'tls':
                    stream_settings["tlsSettings"] = {
                        "serverName": node.get('sni', node['server']),
                        "allowInsecure": False
                    }
                elif security == 'reality':
                    stream_settings["realitySettings"] = {
                        "serverName": node.get('sni', node['server']),
                        "fingerprint": node.get('fp', 'chrome'),
                        "publicKey": node.get('pbk', ''),
                        "shortId": node.get('sid', ''),
                        "spiderX": node.get('spx', '')
                    }
            
            if net_type == 'ws':
                stream_settings["wsSettings"] = {
                    "path": node.get('path', '/'),
                    "headers": {
                        "Host": node.get('host', node['server'])
                    }
                }
            elif net_type == 'grpc':
                stream_settings["grpcSettings"] = {
                    "serviceName": node.get('path', '')
                }
            elif net_type == 'xhttp':
                stream_settings["xhttpSettings"] = {
                    "path": node.get('path', '/')
                }
            
            outbound["streamSettings"] = stream_settings
            
        elif node_type == 'shadowsocks':
            outbound["settings"] = {
                "servers": [{
                    "address": node['server'],
                    "port": node['port'],
                    "method": node['method'],
                    "password": node['password'],
                    "level": 0
                }]
            }
            
        elif node_type == 'trojan':
            outbound["settings"] = {
                "servers": [{
                    "address": node['server'],
                    "port": node['port'],
                    "password": node['password'],
                    "level": 0
                }]
            }
            
            stream_settings = {
                "network": "tcp"
            }
            
            if node.get('sni'):
                stream_settings["security"] = "tls"
                stream_settings["tlsSettings"] = {
                    "serverName": node['sni'],
                    "allowInsecure": False
                }
            
            outbound["streamSettings"] = stream_settings
        
        return outbound
    
    def update_subscription(self):
        """更新订阅"""
        logger.info("开始更新订阅...")
        
        content = self.fetch_subscription()
        if not content:
            return False
        
        nodes = self.parse_subscription(content)
        if not nodes:
            logger.error("未解析到有效节点")
            return False
        
        data = {
            'update_time': datetime.now().isoformat(),
            'node_count': len(nodes),
            'nodes': nodes
        }
        self.save_subscription_data(data)
        
        logger.info(f"订阅更新成功，共 {len(nodes)} 个节点")
        return True
    
    def generate_config(self, node_index=None):
        """生成 Xray 配置文件"""
        if node_index is None:
            node_index = self.selected_node
        
        data = self.load_subscription_data()
        if not data or not data.get('nodes'):
            logger.error("没有可用的订阅数据，请先更新订阅")
            return False
        
        nodes = data['nodes']
        if node_index >= len(nodes):
            logger.error(f"节点索引 {node_index} 超出范围")
            return False
        
        node = nodes[node_index]
        logger.info(f"使用节点 [{node_index}]: {node['name']}")
        
        config = self.generate_xray_config(node)
        
        # 确保 Xray 配置目录存在
        os.makedirs(os.path.dirname(XRAY_CONFIG), exist_ok=True)
        os.makedirs('/var/log/xray', exist_ok=True)
        
        with open(XRAY_CONFIG, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        
        # 设置权限
        subprocess.run(['chmod', '644', XRAY_CONFIG], check=False)
        
        logger.info(f"配置文件已保存到: {XRAY_CONFIG}")
        return True
    
    def start_xray(self):
        """启动 Xray 服务"""
        logger.info("启动 Xray 服务...")
        result = subprocess.run(['systemctl', 'start', 'xray'], capture_output=True, text=True)
        if result.returncode == 0:
            logger.info("Xray 服务已启动")
            logger.info(f"SOCKS 代理: 127.0.0.1:{self.local_socks_port}")
            logger.info(f"HTTP 代理: 127.0.0.1:{self.local_http_port}")
            return True
        else:
            logger.error(f"启动失败: {result.stderr}")
            return False
    
    def stop_xray(self):
        """停止 Xray 服务"""
        logger.info("停止 Xray 服务...")
        subprocess.run(['systemctl', 'stop', 'xray'], check=False)
        logger.info("Xray 服务已停止")
    
    def restart_xray(self):
        """重启 Xray 服务"""
        logger.info("重启 Xray 服务...")
        result = subprocess.run(['systemctl', 'restart', 'xray'], capture_output=True, text=True)
        if result.returncode == 0:
            logger.info("Xray 服务已重启")
            return True
        else:
            logger.error(f"重启失败: {result.stderr}")
            return False
    
    def status_xray(self):
        """查看 Xray 状态"""
        subprocess.run(['systemctl', 'status', 'xray'])
    
    def list_nodes(self):
        """列出所有节点"""
        data = self.load_subscription_data()
        if not data or not data.get('nodes'):
            print("\n没有可用的节点数据，请先更新订阅")
            print(f"运行: xray-client update")
            return
        
        nodes = data['nodes']
        print(f"\n{'='*80}")
        print(f"共 {len(nodes)} 个节点 (最后更新: {data.get('update_time', '未知')})")
        print(f"{'='*80}")
        print(f"{'索引':<6}{'类型':<12}{'名称':<40}{'服务器':<20}")
        print("-" * 80)
        
        for i, node in enumerate(nodes):
            marker = " *" if i == self.selected_node else "  "
            name = (node['name'][:38] + '..') if len(node['name']) > 38 else node['name']
            server = (node['server'][:18] + '..') if len(node['server']) > 18 else node['server']
            print(f"{marker}{i:<4}{node['type']:<12}{name:<40}{server:<20}")
        
        print("-" * 80)
        print("带 * 的为当前选中节点")
        print("切换节点: xray-client select -i <索引>")
        print()
    
    def select_node(self, index):
        """选择节点"""
        data = self.load_subscription_data()
        if not data or not data.get('nodes'):
            print("没有可用的节点数据，请先更新订阅")
            return False
        
        nodes = data['nodes']
        if index < 0 or index >= len(nodes):
            print(f"节点索引 {index} 超出范围 (0-{len(nodes)-1})")
            return False
        
        self.selected_node = index
        
        config = ConfigParser()
        if os.path.exists(INI_FILE):
            config.read(INI_FILE, encoding='utf-8')
        
        if 'node' not in config:
            config['node'] = {}
        config['node']['selected'] = str(index)
        
        with open(INI_FILE, 'w', encoding='utf-8') as f:
            config.write(f)
        
        print(f"已选择节点 [{index}]: {nodes[index]['name']}")
        return True


def main():
    parser = argparse.ArgumentParser(
        description='Xray Client - 支持 JustMySocks 订阅',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  %(prog)s update                    # 更新订阅
  %(prog)s list                      # 列出所有节点
  %(prog)s select -i 0               # 选择第一个节点
  %(prog)s apply                     # 应用配置并重启 Xray
  %(prog)s status                    # 查看 Xray 状态
  
配置文件: /etc/xray-client/config.ini
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='可用命令')
    
    # update 命令
    subparsers.add_parser('update', help='更新订阅')
    
    # list 命令
    subparsers.add_parser('list', help='列出所有节点')
    
    # select 命令
    select_parser = subparsers.add_parser('select', help='选择节点')
    select_parser.add_argument('-i', '--index', type=int, required=True, help='节点索引')
    
    # apply 命令
    subparsers.add_parser('apply', help='应用配置并重启 Xray')
    
    # start/stop/restart/status 命令
    subparsers.add_parser('start', help='启动 Xray 服务')
    subparsers.add_parser('stop', help='停止 Xray 服务')
    subparsers.add_parser('restart', help='重启 Xray 服务')
    subparsers.add_parser('status', help='查看 Xray 状态')
    
    # test 命令
    subparsers.add_parser('test', help='测试代理连接')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    client = XrayClient()
    
    if args.command == 'update':
        if client.update_subscription():
            client.generate_config()
            print("\n订阅更新完成，运行 'xray-client restart' 应用新配置")
    
    elif args.command == 'list':
        client.list_nodes()
    
    elif args.command == 'select':
        if client.select_node(args.index):
            client.generate_config()
            print("\n节点已切换，运行 'xray-client restart' 应用新配置")
    
    elif args.command == 'apply':
        client.generate_config()
        client.restart_xray()
    
    elif args.command == 'start':
        client.start_xray()
    
    elif args.command == 'stop':
        client.stop_xray()
    
    elif args.command == 'restart':
        client.generate_config()
        client.restart_xray()
    
    elif args.command == 'status':
        client.status_xray()
    
    elif args.command == 'test':
        print("测试代理连接...")
        result = subprocess.run(
            ['curl', '-s', '-o', '/dev/null', '-w', '%{http_code}', 
             '-x', f'http://127.0.0.1:{client.local_http_port}', 
             '--connect-timeout', '10', 'https://www.google.com'],
            capture_output=True, text=True
        )
        if result.stdout.strip() == '200':
            print(f"代理连接成功! HTTP 状态码: 200")
        else:
            print(f"代理连接失败，HTTP 状态码: {result.stdout.strip()}")
            print("请检查 Xray 服务是否正常运行")


if __name__ == '__main__':
    main()
PYTHON_SCRIPT

chmod +x /usr/local/bin/xray-client

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

# 重载 systemd
systemctl daemon-reload

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
