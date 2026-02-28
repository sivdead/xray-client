# Xray Client for Linux

**English** | [中文](README_CN.md)

A lightweight Xray client with JustMySocks subscription support for TencentOS, CentOS, RHEL, Ubuntu, and Debian.

**Key Features**:
- Smart network adaptation (auto-detects and uses mirrors in China)
- Multi-protocol support: VMess, VLESS, Shadowsocks, Trojan
- Clash subscription format support
- Auto node selection based on latency
- TUI (Terminal UI) for interactive management
- Docker support
- Systemd integration

## 📑 Table of Contents

- [Features](#features)
- [Requirements](#requirements)
- [Quick Start](#quick-start)
- [Installation](#installation)
  - [Method 1: Download from GitHub Releases (No Python required)](#method-1-download-from-github-releases-no-python-required)
  - [Method 2: Online Installation](#method-2-online-installation)
  - [Method 3: Interactive Quick Install](#method-3-interactive-quick-install)
  - [Method 4: Offline Installation](#method-4-offline-installation)
- [Configuration](#configuration)
- [Usage](#usage)
- [TUI](#%EF%B8%8F-tui)
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
- ✅ **TUI Management** - Interactive terminal UI for node management
- ✅ **Auto Node Selection** - Tests latency and auto-selects best node
- ✅ **Scheduled Updates** - Systemd timer for daily subscription updates
- ✅ **Hot Reload** - Reload config without restarting service
- ✅ **Docker Support** - Official Docker image available
- ✅ **System Proxy Toggle** - One-command enable/disable of system-wide HTTP/SOCKS proxy env vars
- ✅ **TUN Transparent Proxy** - Route all TCP traffic through Xray via iptables (no per-app config needed)

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

### Method 1: Download from GitHub Releases (No Python required)

Pre-built standalone binary (`xray-client`) is available on the [GitHub Releases](https://github.com/sivdead/xray-client/releases) page. It bundles all Python dependencies (including TUI) and runs on any Linux x86_64 system without requiring Python.

```bash
# Download the latest release
curl -fsSL -L -o xray-client https://github.com/sivdead/xray-client/releases/latest/download/xray-client

# Install to system path
sudo install -m 755 xray-client /usr/local/bin/xray-client
```

Then proceed with [Configuration](#%EF%B8%8F-configuration) and run `sudo xray-client update` to get started.

> **Tip:** For servers in China, you can use a mirror or download via a machine with proxy access and then scp the binaries to the target server.

### Method 2: Online Installation

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

### Method 3: Interactive Quick Install

```bash
curl -fsSL -o quick-install.sh https://cdn.jsdelivr.net/gh/sivdead/xray-client@master/quick-install.sh
sudo bash quick-install.sh
```

This will prompt you for subscription URL and ports.

### Method 4: Offline Installation

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

# Transparent proxy (TUN) port — used by tun-on/tun-off
tun_port = 12345

# Addresses that bypass the system proxy (used by proxy-on)
no_proxy = localhost,127.0.0.1,::1

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

# Enable system-wide HTTP/SOCKS proxy env vars (writes to /etc/profile.d/)
sudo xray-client proxy-on

# Disable system proxy
sudo xray-client proxy-off

# Enable TUN transparent proxy (iptables redirect + dokodemo-door)
sudo xray-client tun-on

# Disable TUN transparent proxy
sudo xray-client tun-off
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

## 🖥️ TUI

Interactive terminal interface for node management:

```bash
# Launch TUI
sudo xray-client tui
```

Keyboard shortcuts:
- `↑`/`↓` or `j`/`k` — Navigate nodes
- `Enter` — Select node and apply
- `u` — Update subscription
- `r` — Restart Xray service
- `t` — Test node latency
- `a` — Auto-select best node
- `p` — Test proxy connection
- `l` / `F5` — Refresh data
- `q` — Quit

Features:
- Real-time service status display
- Color-coded protocol types (VMess, VLESS, Shadowsocks, Trojan)
- Node list with scrolling
- Background operations (non-blocking UI)

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

```

### Build Your Own Image

```bash
git clone https://github.com/sivdead/xray-client.git
cd xray-client
docker build -t xray-client .
docker run -d -e SUB_URL=xxx -p 10808:10808 -p 10809:10809 xray-client
```

## 🔧 Proxy Settings

### System Proxy (HTTP/SOCKS env vars)

The installer creates shell functions `proxy-on` and `proxy-off` that automatically
apply changes to the **current terminal** — no manual `source` needed.

```bash
# First time in an existing terminal (new terminals skip this):
source /etc/profile.d/xray-client-functions.sh

# Enable proxy — sets env vars AND applies them in the current shell
proxy-on

# Disable proxy — removes env vars AND unsets them in the current shell
proxy-off
```

Under the hood, `proxy-on` is equivalent to:
```bash
sudo xray-client proxy-on && source /etc/profile.d/xray-proxy.sh
```

To exclude additional addresses from the proxy, add `no_proxy` to `config.ini`:

```ini
[local]
no_proxy = localhost,127.0.0.1,::1,10.0.0.0/8,192.168.0.0/16
```

#### GUI applications

`proxy-on` only sets shell environment variables, which GUI apps (browsers, Electron, etc.)
launched from a desktop session do not inherit. For GUI use, the recommended approach is
**`tun-on`** (transparent proxy mode below) — it routes all traffic at the iptables level
with no per-app or per-session configuration needed.

### TUN Transparent Proxy (no per-app config needed)

Routes **all TCP traffic** from the machine through Xray using iptables NAT redirect.
Private address ranges (10.x, 192.168.x, etc.) are automatically excluded.

```bash
# Enable TUN mode (iptables + dokodemo-door inbound on port 12345)
sudo xray-client tun-on

# Disable TUN mode and clean up iptables rules
sudo xray-client tun-off
```

> **Note:** TUN mode state (`tun_mode`) is persisted in `config.ini` and survives Xray restarts.
> Re-run `tun-on` after a system reboot to re-apply iptables rules.

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
sudo rm -f /etc/profile.d/xray-proxy.sh /etc/profile.d/xray-client-functions.sh

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
