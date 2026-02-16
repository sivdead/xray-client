# Xray Client for TencentOS / CentOS

一个支持 JustMySocks 订阅链接的 Xray 客户端，适用于腾讯云 TencentOS、CentOS、RHEL 等 Linux 系统。

**特点**: 
- 复用 Xray 官方 [install-release.sh](https://github.com/XTLS/Xray-install) 安装核心
- **智能网络适配**：自动检测网络环境，支持直连/镜像/代理/离线多种安装方式

## 功能特性

- ✅ 智能网络适配，支持中国大陆网络环境
- ✅ 复用 Xray 官方安装脚本，规范安装 Xray 核心
- ✅ 支持 JustMySocks 订阅链接自动更新
- ✅ 支持 VMess、VLESS、Shadowsocks、Trojan 协议
- ✅ 自动解析订阅内容并生成 Xray 配置
- ✅ 使用官方 Systemd 服务管理
- ✅ 多节点切换
- ✅ 本地 SOCKS5 + HTTP 双代理

## 系统要求

- TencentOS Server 2/3
- CentOS 7/8/9
- RHEL 7/8/9
- AlmaLinux / Rocky Linux
- Ubuntu / Debian

需要 root 权限运行安装脚本。

## 快速开始

### 方式一：自动安装（推荐，有基本网络访问）

```bash
# 下载安装脚本（使用 jsdelivr CDN）
curl -fsSL -o install.sh https://cdn.jsdelivr.net/gh/your-repo/xray-client@main/install.sh

# 或从 Gitee 下载（国内更快）
curl -fsSL -o install.sh https://gitee.com/your-repo/xray-client/raw/main/install.sh

# 执行安装
chmod +x install.sh
sudo ./install.sh
```

脚本会自动：
1. 检测 GitHub 连通性
2. 如无法直连，自动寻找可用镜像源
3. 使用最佳方式下载并安装 Xray

### 方式二：交互式快速安装

```bash
curl -fsSL -o quick-install.sh https://cdn.jsdelivr.net/gh/your-repo/xray-client@main/quick-install.sh
chmod +x quick-install.sh
sudo ./quick-install.sh
```

### 方式三：离线安装（服务器完全无法外网）

在可以访问 GitHub 的机器上：

```bash
# 下载构建脚本
curl -fsSL -o build-offline.sh https://cdn.jsdelivr.net/gh/your-repo/xray-client@main/build-offline.sh
chmod +x build-offline.sh

# 构建离线包
./build-offline.sh

# 生成的文件: xray-client-offline-202xxxxx.tar.gz
```

然后将离线包上传到服务器：

```bash
# 在服务器上
tar xzf xray-client-offline-202xxxxx.tar.gz
cd xray-client-offline-202xxxxx
sudo ./install-offline.sh
```

### 方式四：手动下载 Xray 后安装

如果服务器能访问部分网络但无法访问 GitHub：

```bash
# 手动下载 Xray 二进制（在本地机器上）
# 从 https://github.com/XTLS/Xray-core/releases 下载对应架构的文件
# 上传到服务器的 /tmp/xray

# 然后在服务器上运行安装脚本，选择离线模式
chmod +x install.sh
sudo ./install.sh
# 按提示选择 "1) 离线安装"
```

## 配置使用

### 1. 编辑配置文件

```bash
vi /etc/xray-client/config.ini
```

```ini
[subscription]
url = https://justmysocks.net/members/getsub.php?service=xxx&id=xxx-xxx-xxx

[local]
socks_port = 10808
http_port = 10809

[node]
selected = 0
```

### 2. 更新订阅并启动

```bash
# 更新订阅
xray-client update

# 启动服务
xray-client restart

# 查看状态
xray-client status
```

### 3. 使用代理

```bash
# 设置 HTTP 代理
export http_proxy=http://127.0.0.1:10809
export https_proxy=http://127.0.0.1:10809

# 测试
curl https://www.google.com
```

## 命令行工具

```bash
# 更新订阅
xray-client update

# 列出节点
xray-client list

# 切换节点（索引从0开始）
xray-client select -i 2

# 启动/停止/重启/查看状态
xray-client start
xray-client stop
xray-client restart
xray-client status

# 测试代理连接
xray-client test
```

## 网络适配说明

安装脚本内置多种网络适配策略：

### 1. 自动检测
脚本首先检测 GitHub 连通性：
- ✅ 如可直连，直接使用官方脚本安装
- ❌ 如不可直连，自动尝试镜像源

### 2. 内置镜像源（按速度排序）
- `https://ghfast.top/`
- `https://ghproxy.com/`
- `https://mirror.ghproxy.com/`
- `https://gh.api.99988866.xyz/`
- `https://ghps.cc/`

### 3. 离线模式
如果所有镜像都不可用，脚本会提示：
- 使用本地预下载的 Xray 二进制
- 或设置 HTTP 代理后重试

## 为其他程序配置代理

### Docker

```bash
mkdir -p /etc/systemd/system/docker.service.d
cat > /etc/systemd/system/docker.service.d/http-proxy.conf << EOF
[Service]
Environment="HTTP_PROXY=http://127.0.0.1:10809"
Environment="HTTPS_PROXY=http://127.0.0.1:10809"
Environment="NO_PROXY=localhost,127.0.0.1,.tencentyun.com,.myqcloud.com"
EOF
systemctl daemon-reload
systemctl restart docker
```

### Git

```bash
git config --global http.proxy http://127.0.0.1:10809
git config --global https.proxy http://127.0.0.1:10809
```

### yum/dnf

```bash
# 在 /etc/yum.conf 末尾添加
proxy=http://127.0.0.1:10809
```

## 日志查看

```bash
# Xray 日志
tail -f /var/log/xray/error.log
tail -f /var/log/xray/access.log

# 客户端日志
tail -f /var/log/xray-client/client.log

# Systemd 服务日志
journalctl -u xray -f
```

## 配置文件说明

### 客户端配置 `/etc/xray-client/config.ini`

```ini
[subscription]
# JustMySocks 订阅链接（必需）
url = https://justmysocks.net/members/getsub.php?...

# 自动更新间隔（秒），默认 3600（1小时）
interval = 3600

[local]
# 本地 SOCKS5 代理端口
socks_port = 10808

# 本地 HTTP 代理端口
http_port = 10809

[node]
# 默认选择的节点索引
selected = 0
```

### Xray 配置 `/usr/local/etc/xray/config.json`

由 `xray-client` 自动生成，**不要手动修改**。

## 局域网访问

默认只监听 127.0.0.1，如需让局域网其他设备使用，修改配置并开放防火墙：

```bash
# 编辑生成的 Xray 配置文件
vi /usr/local/etc/xray/config.json

# 将 "listen": "127.0.0.1" 改为 "listen": "0.0.0.0"

# 开放防火墙
firewall-cmd --permanent --add-port=10808/tcp
firewall-cmd --permanent --add-port=10809/tcp
firewall-cmd --reload
```

同时在腾讯云控制台放通对应端口的安全组规则。

## 卸载

```bash
# 使用官方脚本卸载 Xray
bash <(curl -L https://github.com/XTLS/Xray-install/raw/main/install-release.sh) remove

# 删除客户端配置
rm -rf /etc/xray-client
rm -rf /var/log/xray-client
rm -f /usr/local/bin/xray-client
```

## 目录结构

```
/usr/local/bin/xray              # Xray 核心（官方）
/usr/local/etc/xray/config.json  # Xray 配置（自动生成）
/usr/local/share/xray/           # GeoIP/GeoSite 数据
/etc/systemd/system/xray.service # Systemd 服务（官方）
/var/log/xray/                   # Xray 日志目录

/etc/xray-client/                # 客户端配置
├── config.ini
└── subscription/
    └── nodes.json

/var/log/xray-client/            # 客户端日志
└── client.log

/usr/local/bin/xray-client       # 管理脚本
```

## 常见问题

### Q: 安装时提示 "无法连接 GitHub"

A: 脚本会自动尝试镜像源。如所有镜像都失败，请选择：
1. 离线安装 - 手动下载 Xray 到 /tmp/xray
2. 代理安装 - 设置 HTTP 代理

### Q: 订阅更新失败

A: 
```bash
# 检查订阅链接是否有效
curl -v "你的订阅链接"

# 设置代理后更新
export https_proxy=http://127.0.0.1:10809
xray-client update
```

### Q: 某些节点连不上

```bash
# 列出所有节点
xray-client list

# 尝试其他节点
xray-client select -i 1
xray-client restart
```

### Q: 如何升级 Xray

```bash
# 使用官方脚本（需能访问 GitHub 或设置代理）
bash <(curl -L https://github.com/XTLS/Xray-install/raw/main/install-release.sh) install

# 或使用离线包重新安装
```

## 协议支持

| 协议 | 支持情况 | 说明 |
|------|---------|------|
| VMess | ✅ 完全支持 | 包括 WebSocket + TLS |
| VLESS | ✅ 完全支持 | 支持 XTLS、REALITY |
| Shadowsocks | ✅ 完全支持 | AEAD 加密 |
| Trojan | ✅ 完全支持 | TLS 传输 |

## 相关链接

- [Xray-core](https://github.com/XTLS/Xray-core)
- [Xray-install](https://github.com/XTLS/Xray-install) - 官方安装脚本
- [JustMySocks](https://justmysocks.net/)

## 许可证

MIT License
