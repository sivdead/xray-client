# Xray Client for Linux

A lightweight Xray client with JustMySocks subscription support for TencentOS, CentOS, RHEL, Ubuntu, and Debian.

**Key Features**:
- Smart network adaptation (auto-detects and uses mirrors in China)
- Multi-protocol support: VMess, VLESS, Shadowsocks, Trojan
- Clash subscription format support
- Auto node selection based on latency
- Web UI for easy management
- Docker support
- Systemd integration

## 📑 Table of Contents

- [Features](#features)
- [Requirements](#requirements)
- [Quick Start](#quick-start)
- [Installation](#installation)
- [Configuration](#configuration)
- [Usage](#usage)
- [Web UI](#web-ui)
- [Docker](#docker)
- [Proxy Settings](#proxy-settings)
- [Troubleshooting](#troubleshooting)
- [Uninstall](#uninstall)

## ✨ Features

- ✅ **Smart Network Adaptation** - Auto-detects network environment, supports direct connection, mirrors, proxy, and offline installation
- ✅ **Official Xray Installation** - Uses official install-release.sh for standardized installation
- ✅ **JustMySocks Subscription** - Auto-updates subscription links
- ✅ **Multi-Protocol Support** - VMess, VLESS, Shadowsocks, Trojan
- ✅ **Clash Format** - Supports Clash YAML subscription format
- ✅ **Web Management UI** - Browser-based node management
- ✅ **Auto Node Selection** - Tests latency and auto-selects best node
- ✅ **Scheduled Updates** - Systemd timer for daily subscription updates
- ✅ **Hot Reload** - Reload config without restarting service
- ✅ **Docker Support** - Official Docker image available

## 📋 Requirements

- Linux with systemd (TencentOS, CentOS 7/8/9, RHEL, Ubuntu, Debian)
- Root access
- Python 3.6+ (will be auto-installed)

## 🚀 Quick Start

```bash
# Download and install (using jsDelivr CDN for China)
curl -fsSL -o install.sh https://cdn.jsdelivr.net/gh/sivdead/xray-client@master/install.sh
sudo bash install.sh

# Configure subscription
sudo vi /etc/xray-client/config.ini
# Edit: url = https://your-subscription-link

# Update subscription and start
sudo xray-client update
sudo xray-client restart

# Test connection
export https_proxy=http://127.0.0.1:10809
curl https://www.google.com
```

## 📦 Installation

### Method 1: Online Installation (Recommended)

```bash
# Using jsDelivr CDN (faster in China)
curl -fsSL -o install.sh https://cdn.jsdelivr.net/gh/sivdead/xray-client@master/install.sh
sudo bash install.sh

# Or using GitHub directly
curl -fsSL -o install.sh https://raw.githubusercontent.com/sivdead/xray-client/master/install.sh
sudo bash install.sh
```

The installer will:
1. Detect your network environment
2. Install Xray core using official script
3. Install Python dependencies
4. Set up systemd services
5. Configure auto-update timer

### Method 2: Interactive Quick Install

```bash
curl -fsSL -o quick-install.sh https://cdn.jsdelivr.net/gh/sivdead/xray-client@master/quick-install.sh
sudo bash quick-install.sh
```

This will prompt you for subscription URL and ports.

### Method 3: Offline Installation

For servers without internet access:

```bash
# On a machine with internet access
./build-offline.sh
# This creates: xray-client-offline-202xxxxx.tar.gz

# Copy to target server and install
tar xzf xray-client-offline-202xxxxx.tar.gz
cd xray-client-offline-202xxxxx
sudo ./install-offline.sh
```

## ⚙️ Configuration

Edit `/etc/xray-client/config.ini`:

```ini
[subscription]
# Your subscription URL (required)
url = https://justmysocks.net/members/getsub.php?service=xxx&id=xxx

# For multiple subscriptions
url2 = https://example.com/sub2
url3 = https://example.com/sub3

# Auto-update interval (seconds), default 1 hour
interval = 3600

[local]
# Local SOCKS5 proxy port
socks_port = 10808

# Local HTTP proxy port
http_port = 10809

# Enable UDP
udp = true

# Enable hot reload
hot_reload = true

[node]
# Default selected node index
selected = 0
```

## 🎮 Usage

### Basic Commands

```bash
# Update subscription
sudo xray-client update

# List all nodes
sudo xray-client list

# Select a node (by index)
sudo xray-client select -i 2

# Test node latency
sudo xray-client test

# Auto-select best node
sudo xray-client auto-select

# Apply config and restart
sudo xray-client restart

# Hot reload (no connection drop)
sudo xray-client reload

# Check status
sudo xray-client status

# Test proxy connection
sudo xray-client ping
```

### Service Control

```bash
# Start/Stop/Restart
sudo systemctl start xray
sudo systemctl stop xray
sudo systemctl restart xray

# Check status
sudo systemctl status xray

# View logs
sudo journalctl -u xray -f
sudo tail -f /var/log/xray/error.log
```

## 🌐 Web UI

Optional web interface for browser-based management:

```bash
# Install Flask
sudo pip3 install flask pyyaml

# Start Web UI
cd /root/xray-client
sudo python3 web-ui.py

# Access via browser
# http://your-server-ip:5000
```

Features:
- View all nodes
- Switch nodes with one click
- Update subscription
- View service status

## 🐳 Docker

### Using Docker

```bash
# Run with subscription URL
docker run -d \
  --name xray-client \
  -e SUB_URL=https://your-subscription-url \
  -p 10808:10808 \
  -p 10809:10809 \
  sivdead/xray-client

# With Web UI enabled
docker run -d \
  --name xray-client \
  -e SUB_URL=https://your-subscription-url \
  -e WEB_UI=true \
  -p 10808:10808 \
  -p 10809:10809 \
  -p 5000:5000 \
  sivdead/xray-client
```

### Build Your Own Image

```bash
git clone https://github.com/sivdead/xray-client.git
cd xray-client
docker build -t xray-client .
docker run -d -e SUB_URL=xxx -p 10808:10808 -p 10809:10809 xray-client
```

## 🔧 Proxy Settings

After installation, configure system-wide proxy:

### Current Session

```bash
# Enable proxy
export http_proxy=http://127.0.0.1:10809
export https_proxy=http://127.0.0.1:10809
export no_proxy=localhost,127.0.0.1

# Or use the helper
source proxy-on
```

### Permanent (All Users)

Already configured in `/etc/profile.d/proxy.sh`, takes effect on next login.

### Application-Specific

**wget:**
```bash
wget -e use_proxy=yes -e http_proxy=127.0.0.1:10809 https://example.com
```

**curl:**
```bash
curl -x http://127.0.0.1:10809 https://example.com
```

**yum/dnf:**
Already configured in `/etc/yum.conf`

**Docker:**
Not configured by default (most Docker use cases don't need proxy)

**Git:**
```bash
git config --global http.proxy http://127.0.0.1:10809
git config --global https.proxy http://127.0.0.1:10809
```

## 🔍 Troubleshooting

### Service Won't Start

```bash
# Check logs
sudo journalctl -u xray -n 50

# Verify config
sudo /usr/local/bin/xray -test -c /usr/local/etc/xray/config.json

# Check ports
sudo ss -tlnp | grep 1080
```

### Subscription Update Fails

```bash
# Test subscription URL manually
curl -v "your-subscription-url"

# Update with proxy
export https_proxy=http://127.0.0.1:10809
sudo xray-client update
```

### Can't Connect to Proxy

```bash
# Check if Xray is running
sudo systemctl is-active xray

# Test local connection
curl -x http://127.0.0.1:10809 https://www.google.com

# Check firewall
sudo firewall-cmd --list-ports
```

### Some Nodes Don't Work

```bash
# Test all nodes and switch to best
sudo xray-client auto-select

# Or manually test and switch
sudo xray-client test
sudo xray-client select -i 3
sudo xray-client restart
```

## ❌ Uninstall

```bash
# Remove Xray using official script
bash <(curl -L https://github.com/XTLS/Xray-install/raw/main/install-release.sh) remove

# Remove client config
sudo rm -rf /etc/xray-client
sudo rm -rf /var/log/xray-client
sudo rm -f /usr/local/bin/xray-client
sudo rm -f /etc/profile.d/proxy.sh

# Remove systemd timer
sudo systemctl stop xray-client-update.timer
sudo systemctl disable xray-client-update.timer
sudo rm -f /etc/systemd/system/xray-client-update.*
sudo systemctl daemon-reload
```

## 📊 Protocol Support

| Protocol | Support | Notes |
|----------|---------|-------|
| VMess | ✅ Full | Includes WebSocket + TLS |
| VLESS | ✅ Full | Supports XTLS, REALITY |
| Shadowsocks | ✅ Full | AEAD ciphers |
| Trojan | ✅ Full | TLS transport |

## 📝 Directory Structure

```
/usr/local/bin/xray              # Xray core (official)
/usr/local/etc/xray/config.json  # Xray config (auto-generated)
/usr/local/share/xray/           # GeoIP/GeoSite data
/etc/systemd/system/xray.service # Xray service (official)
/var/log/xray/                   # Xray logs

/etc/xray-client/                # Client config
├── config.ini                   # Main configuration
└── subscription/
    └── nodes.json               # Cached nodes

/var/log/xray-client/            # Client logs
└── client.log

/usr/local/bin/xray-client       # Management script
```

## 🤝 Contributing

Pull requests are welcome! For major changes, please open an issue first.

## 📄 License

[MIT](LICENSE)

## 🔗 Links

- [Xray-core](https://github.com/XTLS/Xray-core)
- [Xray-install](https://github.com/XTLS/Xray-install) - Official install script
- [JustMySocks](https://justmysocks.net/)

---

## 🇨🇳 中文版

For Chinese documentation, see [README_CN.md](README_CN.md).
