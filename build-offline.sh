#!/bin/bash
# 构建离线安装包
# 在可以访问 GitHub 的机器上运行此脚本，生成离线安装包

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}"
echo "╔══════════════════════════════════════════════════════╗"
echo "║     Xray Client 离线安装包构建工具                    ║"
echo "╚══════════════════════════════════════════════════════╝"
echo -e "${NC}"

# 创建临时目录
BUILD_DIR="xray-client-offline-$(date +%Y%m%d)"
mkdir -p "$BUILD_DIR"

echo -e "${YELLOW}正在下载必要的文件...${NC}"

# 检测架构
ARCH=$(uname -m)
if [[ "$ARCH" == "x86_64" ]]; then
    XRAY_ARCH="Xray-linux-64"
elif [[ "$ARCH" == "aarch64" ]]; then
    XRAY_ARCH="Xray-linux-arm64-v8a"
else
    echo -e "${RED}不支持的架构: $ARCH${NC}"
    exit 1
fi

# 获取最新版本
LATEST_VERSION=$(curl -s https://api.github.com/repos/XTLS/Xray-core/releases/latest | grep '"tag_name":' | sed -E 's/.*"([^"]+)".*/\1/')
if [ -z "$LATEST_VERSION" ]; then
    echo -e "${YELLOW}无法获取最新版本，使用默认版本${NC}"
    LATEST_VERSION="v26.2.6"
fi

echo "最新版本: $LATEST_VERSION"

# 下载 Xray 二进制
echo "下载 Xray 二进制 ($XRAY_ARCH)..."
DOWNLOAD_URL="https://github.com/XTLS/Xray-core/releases/download/$LATEST_VERSION/$XRAY_ARCH.zip"

if ! curl -fsSL -o "$BUILD_DIR/xray.zip" "$DOWNLOAD_URL"; then
    echo -e "${RED}下载失败，尝试使用 ghproxy...${NC}"
    curl -fsSL -o "$BUILD_DIR/xray.zip" "https://ghproxy.com/$DOWNLOAD_URL"
fi

unzip -q "$BUILD_DIR/xray.zip" -d "$BUILD_DIR"
mv "$BUILD_DIR/xray" "$BUILD_DIR/xray-bin"
rm -f "$BUILD_DIR/xray.zip" "$BUILD_DIR/LICENSE" "$BUILD_DIR/README.md" 2>/dev/null || true

# 下载 GeoIP
echo "下载 GeoIP..."
if ! curl -fsSL -o "$BUILD_DIR/geoip.dat" "https://github.com/v2fly/geoip/releases/latest/download/geoip.dat"; then
    curl -fsSL -o "$BUILD_DIR/geoip.dat" "https://ghproxy.com/https://github.com/v2fly/geoip/releases/latest/download/geoip.dat"
fi

# 下载 GeoSite
echo "下载 GeoSite..."
if ! curl -fsSL -o "$BUILD_DIR/geosite.dat" "https://github.com/v2fly/domain-list-community/releases/latest/download/dlc.dat"; then
    curl -fsSL -o "$BUILD_DIR/geosite.dat" "https://ghproxy.com/https://github.com/v2fly/domain-list-community/releases/latest/download/dlc.dat"
fi

# 复制安装脚本
echo "复制安装脚本..."
cp install.sh "$BUILD_DIR/"
cp quick-install.sh "$BUILD_DIR/"
cp xray-client.py "$BUILD_DIR/"

# 如果存在预编译可执行文件则一并打包
if [ -f "dist/xray-client" ]; then
    echo "包含预编译可执行文件..."
    cp dist/xray-client "$BUILD_DIR/"
    echo -e "${GREEN}✓ 已包含可执行文件（含 TUI，目标机器无需 Python）${NC}"
else
    echo -e "${YELLOW}未找到预编译可执行文件，离线包将使用 Python 脚本模式${NC}"
    echo "提示: 先运行 bash build-executable.sh 构建可执行文件"
fi

# 创建离线安装入口脚本
cat > "$BUILD_DIR/install-offline.sh" << 'EOF'
#!/bin/bash
# Xray Client 离线安装脚本

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${YELLOW}Xray Client 离线安装${NC}"
echo ""

if [ "$EUID" -ne 0 ]; then
    echo -e "${RED}请使用 root 权限运行此脚本${NC}"
    exit 1
fi

# 检查必要文件
if [ ! -f "xray-bin" ]; then
    echo -e "${RED}错误: 未找到 xray-bin 文件${NC}"
    exit 1
fi

# 复制 Xray 到临时目录
cp xray-bin /tmp/xray
chmod +x /tmp/xray

# 运行安装脚本，选择离线模式
export NETWORK_MODE="offline"
bash install.sh

echo ""
echo -e "${GREEN}安装完成!${NC}"
echo ""
EOF
chmod +x "$BUILD_DIR/install-offline.sh"

# 创建 README
cat > "$BUILD_DIR/README.txt" << EOF
Xray Client 离线安装包
========================

包含内容:
  - xray-bin: Xray 核心二进制文件 ($LATEST_VERSION, $XRAY_ARCH)
  - geoip.dat: IP 地理位置数据
  - geosite.dat: 域名规则数据
  - install.sh: 主安装脚本
  - install-offline.sh: 离线安装入口
  - quick-install.sh: 快速安装脚本
  - xray-client.py: Python 管理脚本

安装方法:
  1. 将本目录上传到目标服务器
  2. 进入目录: cd xray-client-offline-xxx
  3. 执行安装: sudo ./install-offline.sh

安装后配置:
  1. 编辑配置文件: vi /etc/xray-client/config.ini
  2. 填入 JustMySocks 订阅链接
  3. 更新订阅: xray-client update
  4. 启动服务: xray-client restart

代理地址:
  SOCKS5: 127.0.0.1:10808
  HTTP:   127.0.0.1:10809

构建时间: $(date)
EOF

# 打包
echo -e "${YELLOW}打包...${NC}"
tar czf "${BUILD_DIR}.tar.gz" "$BUILD_DIR"

echo ""
echo -e "${GREEN}离线安装包已生成: ${BUILD_DIR}.tar.gz${NC}"
echo ""
echo "使用方法:"
echo "  1. 将 ${BUILD_DIR}.tar.gz 上传到目标服务器"
echo "  2. 解压: tar xzf ${BUILD_DIR}.tar.gz"
echo "  3. 安装: cd ${BUILD_DIR} && sudo ./install-offline.sh"
echo ""

# 清理
rm -rf "$BUILD_DIR"
