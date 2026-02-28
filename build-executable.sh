#!/bin/bash
# 使用 PyInstaller 构建独立可执行文件
# 生成的二进制不需要目标机器安装 Python

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}"
echo "╔══════════════════════════════════════════════════════╗"
echo "║     Xray Client 可执行文件构建工具                    ║"
echo "╚══════════════════════════════════════════════════════╝"
echo -e "${NC}"

# 检查 Python
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}需要 Python3，请先安装${NC}"
    exit 1
fi

# 检查/安装 PyInstaller
if ! python3 -m PyInstaller --version &> /dev/null 2>&1; then
    echo -e "${YELLOW}安装 PyInstaller...${NC}"
    python3 -m pip install pyinstaller
fi

# 确保依赖已安装
echo -e "${YELLOW}安装 Python 依赖...${NC}"
python3 -m pip install pyyaml

BUILD_DIR="dist"
mkdir -p "$BUILD_DIR"

# 构建 xray-client
echo ""
echo -e "${YELLOW}构建 xray-client...${NC}"
python3 -m PyInstaller \
    --onefile \
    --name xray-client \
    --clean \
    --noconfirm \
    --strip \
    --hidden-import yaml \
    xray-client.py

echo ""
echo -e "${YELLOW}构建 xray-tui...${NC}"
python3 -m PyInstaller \
    --onefile \
    --name xray-tui \
    --clean \
    --noconfirm \
    --strip \
    --hidden-import yaml \
    tui.py

echo ""
echo -e "${GREEN}构建完成!${NC}"
echo ""
echo "生成的文件:"
ls -lh dist/xray-client dist/xray-tui
echo ""
echo "可直接复制到目标机器使用:"
echo "  cp dist/xray-client /usr/local/bin/"
echo "  cp dist/xray-tui /usr/local/bin/"
