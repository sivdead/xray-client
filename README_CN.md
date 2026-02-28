# Xray Client for Linux

[English](README.md) | **中文**

一个轻量级的 Xray 客户端，支持 JustMySocks 订阅，适用于 TencentOS、CentOS、RHEL、Ubuntu、Debian 等 Linux 系统。

**功能特性**:
- 智能网络适配，自动检测并使用国内镜像
- 多协议支持：VMess、VLESS、Shadowsocks、Trojan
- 支持 Clash YAML 订阅格式
- 节点测速与自动选择
- TUI 终端交互管理界面
- Docker 支持
- Systemd 服务集成
- 一键开关系统代理
- TUN 透明代理模式（无需逐应用配置）

## 📑 目录

- [功能特性](#-功能特性)
- [系统要求](#-系统要求)
- [快速开始](#-快速开始)
- [安装方式](#-安装方式)
  - [方式一：从 GitHub Release 下载预编译可执行文件（无需 Python）](#方式一从-github-release-下载预编译可执行文件无需-python)
  - [方式二：在线安装](#方式二在线安装)
  - [方式三：交互式快速安装](#方式三交互式快速安装)
  - [方式四：离线安装](#方式四离线安装)
- [配置说明](#%EF%B8%8F-配置说明)
- [使用命令](#-使用命令)
- [代理设置](#-代理设置)
- [TUI 界面](#%EF%B8%8F-tui-界面)
- [Docker](#-docker)
- [常见问题](#-常见问题)
- [卸载](#-卸载)

## ✨ 功能特性

- ✅ **智能网络适配** — 自动检测网络环境，支持直连/镜像/代理/离线多种安装方式
- ✅ **官方 Xray 安装** — 使用官方 install-release.sh，规范安装 Xray 核心
- ✅ **JustMySocks 订阅** — 自动更新订阅链接
- ✅ **多协议支持** — VMess、VLESS、Shadowsocks、Trojan
- ✅ **Clash 格式** — 支持 Clash YAML 订阅格式
- ✅ **TUI 管理界面** — 终端交互管理节点
- ✅ **自动选择节点** — 测速并自动选择最佳节点
- ✅ **定时更新** — Systemd Timer 每日自动更新订阅
- ✅ **热重载** — 无需重启服务即可重载配置
- ✅ **Docker 支持** — 提供官方 Docker 镜像
- ✅ **系统代理开关** — 一条命令开启/关闭系统全局 HTTP/SOCKS 代理环境变量
- ✅ **TUN 透明代理** — 通过 iptables 将所有 TCP 流量路由至 Xray，无需逐应用配置

## 📋 系统要求

- 带 systemd 的 Linux（TencentOS、CentOS 7/8/9、RHEL、Ubuntu、Debian）
- root 权限
- Python 3.6+（会自动安装）

## 🚀 快速开始

```bash
# 下载并安装（使用 jsDelivr CDN，国内更快）
curl -fsSL -o install.sh https://cdn.jsdelivr.net/gh/sivdead/xray-client@master/install.sh
sudo bash install.sh

# 配置订阅链接
sudo vi /etc/xray-client/config.ini
# 修改: url = https://your-subscription-link

# 更新订阅并启动
sudo xray-client update
sudo xray-client restart

# 开启系统代理
sudo xray-client proxy-on
source /etc/profile.d/xray-proxy.sh
```

## 📦 安装方式

### 方式一：从 GitHub Release 下载预编译可执行文件（无需 Python）

[GitHub Releases](https://github.com/sivdead/xray-client/releases) 页面提供已打包的独立可执行文件（`xray-client` 和 `xray-tui`），内置所有 Python 依赖，无需在目标机器上安装 Python，直接可用。

```bash
# 下载最新版本的可执行文件
curl -fsSL -L -o xray-client https://github.com/sivdead/xray-client/releases/latest/download/xray-client
curl -fsSL -L -o xray-tui    https://github.com/sivdead/xray-client/releases/latest/download/xray-tui

# 安装到系统路径
sudo install -m 755 xray-client /usr/local/bin/xray-client
sudo install -m 755 xray-tui    /usr/local/bin/xray-tui
```

安装完成后，参考[配置说明](#%EF%B8%8F-配置说明)完成配置，然后运行 `sudo xray-client update` 即可开始使用。

> **提示：** 国内服务器若无法直连 GitHub，可在有代理的机器上下载好文件后，通过 scp 传输到目标服务器。

### 方式二：在线安装

```bash
# 使用 jsDelivr CDN（国内推荐）
curl -fsSL -o install.sh https://cdn.jsdelivr.net/gh/sivdead/xray-client@master/install.sh
sudo bash install.sh

# 或使用 GitHub 直连
curl -fsSL -o install.sh https://raw.githubusercontent.com/sivdead/xray-client/master/install.sh
sudo bash install.sh
```

安装脚本会自动完成：
1. 检测网络环境
2. 使用官方 install-release.sh 安装 Xray 核心
3. 安装 Python 依赖
4. 配置 Systemd 服务
5. 设置定时自动更新

### 方式三：交互式快速安装

```bash
curl -fsSL -o quick-install.sh https://cdn.jsdelivr.net/gh/sivdead/xray-client@master/quick-install.sh
sudo bash quick-install.sh
```

根据提示输入订阅链接和端口。

### 方式四：离线安装

适用于无法访问外网的服务器：

```bash
# 在有网络的机器上构建离线包
./build-offline.sh
# 生成: xray-client-offline-202xxxxx.tar.gz

# 将离线包传到目标服务器后执行
tar xzf xray-client-offline-202xxxxx.tar.gz
cd xray-client-offline-202xxxxx
sudo ./install-offline.sh
```

## ⚙️ 配置说明

编辑 `/etc/xray-client/config.ini`：

```ini
[subscription]
# 订阅链接（必填）
url = https://justmysocks.net/members/getsub.php?service=xxx&id=xxx

# 多订阅支持
url2 = https://example.com/sub2
url3 = https://example.com/sub3

# 自动更新间隔（秒），默认 1 小时
interval = 3600

[local]
# 本地 SOCKS5 代理端口
socks_port = 10808

# 本地 HTTP 代理端口
http_port = 10809

# 启用 UDP
udp = true

# 启用热重载
hot_reload = true

# TUN 透明代理端口（tun-on/tun-off 使用）
tun_port = 12345

# 不走代理的地址（proxy-on 使用）
no_proxy = localhost,127.0.0.1,::1

[node]
# 默认选中的节点索引
selected = 0
```

## 🎮 使用命令

### 节点管理

```bash
# 更新所有订阅
sudo xray-client update

# 更新指定订阅
sudo xray-client update -n default

# 列出所有节点
sudo xray-client list

# 选择节点（按索引）
sudo xray-client select -i 2

# 测试节点延迟
sudo xray-client test

# 自动选择最佳节点
sudo xray-client auto-select

# 应用配置并重启
sudo xray-client apply

# 热重载（不中断连接）
sudo xray-client reload

# 查看 Xray 状态
sudo xray-client status

# 测试代理连通性
sudo xray-client ping
```

### 服务控制

```bash
sudo xray-client start
sudo xray-client stop
sudo xray-client restart
```

### 代理模式切换

```bash
# 开启系统代理（写入 /etc/profile.d/xray-proxy.sh）
sudo xray-client proxy-on

# 关闭系统代理（删除上述文件）
sudo xray-client proxy-off

# 开启 TUN 透明代理模式
sudo xray-client tun-on

# 关闭 TUN 透明代理模式
sudo xray-client tun-off
```

## 🔧 代理设置

### 系统代理（HTTP/SOCKS 环境变量）

```bash
# 一键开启 — 同时写入 /etc/profile.d/xray-proxy.sh 和 /etc/environment
sudo xray-client proxy-on

# 新终端自动生效；当前终端执行：
source /etc/profile.d/xray-proxy.sh

# 关闭系统代理
sudo xray-client proxy-off
# 当前终端同时执行：
unset http_proxy https_proxy HTTP_PROXY HTTPS_PROXY all_proxy
```

如需排除内网地址，在 `config.ini` 中设置：

```ini
[local]
no_proxy = localhost,127.0.0.1,::1,10.0.0.0/8,192.168.0.0/16
```

#### proxy-on 的工作原理及 GUI 环境说明

`proxy-on` 会将代理设置写入两个位置：

| 文件 | 读取方 | 生效时机 |
|------|--------|---------|
| `/etc/profile.d/xray-proxy.sh` | 新建 bash/sh 终端会话 | 立即（新终端） |
| `/etc/environment` | PAM（登录管理器、SSH、`su -`） | **重新登录**后 |

**GUI 应用**（浏览器、Electron 应用等）的环境变量由桌面登录时的显示管理器决定，
不会自动读取 `/etc/profile.d/`，因此：

- 执行 `proxy-on` 后**重新登录系统**，GUI 应用才能通过 `/etc/environment` 获取代理设置。
- 或在应用内单独配置代理（如 GNOME / KDE 系统代理设置）。
- 或使用 **`tun-on` 透明代理模式**（推荐 GUI 用户使用），无需任何应用级或会话级配置，
  所有流量自动经过 Xray。

### TUN 透明代理（无需逐应用配置）

将本机所有 TCP 出站流量通过 iptables NAT 重定向至 Xray，私有地址段自动豁免。

```bash
# 开启（iptables + dokodemo-door 入站，默认端口 12345）
sudo xray-client tun-on

# 关闭（清理 iptables 规则）
sudo xray-client tun-off
```

> **注意：** `tun_mode` 状态会持久化到 `config.ini`，Xray 重启后保持不变。
> 系统重启后需重新执行 `tun-on` 来恢复 iptables 规则。

### 应用级代理配置

**wget：**
```bash
wget -e use_proxy=yes -e http_proxy=127.0.0.1:10809 https://example.com
```

**curl：**
```bash
curl -x http://127.0.0.1:10809 https://example.com
```

**yum/dnf：**
```bash
# 在 /etc/yum.conf 末尾添加
proxy=http://127.0.0.1:10809
```

**Git：**
```bash
git config --global http.proxy http://127.0.0.1:10809
git config --global https.proxy http://127.0.0.1:10809
```

**Docker：**
```bash
mkdir -p /etc/systemd/system/docker.service.d
cat > /etc/systemd/system/docker.service.d/http-proxy.conf << EOF
[Service]
Environment="HTTP_PROXY=http://127.0.0.1:10809"
Environment="HTTPS_PROXY=http://127.0.0.1:10809"
Environment="NO_PROXY=localhost,127.0.0.1"
EOF
systemctl daemon-reload && systemctl restart docker
```

## 🖥️ TUI 界面

```bash
# 启动 TUI
sudo xray-tui
```

快捷键：
- `↑`/`↓` 或 `j`/`k` — 上下移动
- `Enter` — 选择节点并应用
- `u` — 更新订阅
- `r` — 重启服务
- `t` — 测试节点延迟
- `a` — 自动选择最佳节点
- `p` — 测试代理连接
- `l` / `F5` — 刷新数据
- `q` — 退出

功能：实时服务状态、协议类型彩色标注、节点列表滚动、后台异步操作。

## 🐳 Docker

```bash
# 运行（指定订阅链接）
docker run -d \
  --name xray-client \
  -e SUB_URL=https://your-subscription-url \
  -p 10808:10808 \
  -p 10809:10809 \
  sivdead/xray-client

```

## 🔍 常见问题

### 服务无法启动

```bash
sudo journalctl -u xray -n 50
sudo /usr/local/bin/xray -test -c /usr/local/etc/xray/config.json
sudo ss -tlnp | grep 1080
```

### 订阅更新失败

```bash
curl -v "你的订阅链接"
export https_proxy=http://127.0.0.1:10809
sudo xray-client update
```

### 节点无法连接

```bash
sudo xray-client auto-select
# 或手动测试后切换
sudo xray-client test
sudo xray-client select -i 3
sudo xray-client restart
```

## ❌ 卸载

```bash
# 使用官方脚本卸载 Xray
bash <(curl -L https://github.com/XTLS/Xray-install/raw/main/install-release.sh) remove

# 删除客户端文件
sudo rm -rf /etc/xray-client
sudo rm -rf /var/log/xray-client
sudo rm -f /usr/local/bin/xray-client
sudo rm -f /etc/profile.d/xray-proxy.sh

# 删除定时任务
sudo systemctl stop xray-client-update.timer
sudo systemctl disable xray-client-update.timer
sudo rm -f /etc/systemd/system/xray-client-update.*
sudo systemctl daemon-reload
```

## 📊 协议支持

| 协议 | 支持 | 说明 |
|------|------|------|
| VMess | ✅ 完整 | 含 WebSocket + TLS |
| VLESS | ✅ 完整 | 支持 XTLS、REALITY |
| Shadowsocks | ✅ 完整 | AEAD 加密 |
| Trojan | ✅ 完整 | TLS 传输 |

## 📝 目录结构

```
/usr/local/bin/xray              # Xray 核心（官方）
/usr/local/etc/xray/config.json  # Xray 配置（自动生成）
/usr/local/share/xray/           # GeoIP/GeoSite 数据
/etc/systemd/system/xray.service # Systemd 服务（官方）
/var/log/xray/                   # Xray 日志

/etc/xray-client/                # 客户端配置
├── config.ini
└── subscription/
    └── nodes.json

/var/log/xray-client/            # 客户端日志
└── client.log

/usr/local/bin/xray-client       # 管理脚本
/etc/profile.d/xray-proxy.sh     # 系统代理环境变量（proxy-on 生成）
```

## 🤝 贡献

欢迎提交 Pull Request！大型改动请先开 Issue 讨论。

## 📄 许可证

[MIT](LICENSE)

## 🔗 相关链接

- [Xray-core](https://github.com/XTLS/Xray-core)
- [Xray-install](https://github.com/XTLS/Xray-install) — 官方安装脚本
- [JustMySocks](https://justmysocks.net/)
