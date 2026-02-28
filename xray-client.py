#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Xray Client - 支持 JustMySocks 订阅
功能: 多订阅管理、Clash格式、节点测速、自动选择、热重载
"""

import os
import json
import base64
import urllib.request
import urllib.parse
import subprocess
import shutil
import time
import signal
import logging
import argparse
import socket
from datetime import datetime
from configparser import ConfigParser
from concurrent.futures import ThreadPoolExecutor, as_completed

# 配置日志
_log_handlers = [logging.StreamHandler()]
_log_file = "/var/log/xray-client/client.log"
try:
    os.makedirs(os.path.dirname(_log_file), exist_ok=True)
    _log_handlers.append(logging.FileHandler(_log_file, encoding="utf-8"))
except OSError:
    pass  # 非 root 用户无法写日志文件，仅输出到终端
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=_log_handlers,
)
logger = logging.getLogger(__name__)

# 使用官方 Xray 路径
XRAY_BIN = "/usr/local/bin/xray"
XRAY_CONFIG = "/usr/local/etc/xray/config.json"
CLIENT_CONFIG_DIR = "/etc/xray-client"
SUBSCRIPTION_FILE = os.path.join(CLIENT_CONFIG_DIR, "subscription", "nodes.json")
INI_FILE = os.path.join(CLIENT_CONFIG_DIR, "config.ini")
PID_FILE = "/var/run/xray-client.pid"
PROXY_PROFILE = "/etc/profile.d/xray-proxy.sh"
PROXY_FUNCTIONS_FILE = "/etc/profile.d/xray-client-functions.sh"
ETC_ENVIRONMENT = "/etc/environment"
IPTABLES_CHAIN = "XRAY"

# GitHub 代理镜像列表
GH_MIRRORS = [
    "https://ghfast.top/",
    "https://ghproxy.com/",
    "https://mirror.ghproxy.com/",
    "https://gh.api.99988866.xyz/",
    "https://ghps.cc/",
    "",
]


def _resolve_executable(name):
    """Resolve a command name to its absolute path via shutil.which().

    Prevents PATH manipulation from causing unintended command execution.
    """
    path = shutil.which(name)
    if path is None:
        raise FileNotFoundError(f"Required executable not found in PATH: {name}")
    return path


class XrayClient:
    def __init__(self):
        self.subscriptions = []
        self.auto_update_interval = 3600
        self.selected_node = 0
        self.local_socks_port = 10808
        self.local_http_port = 10809
        self.enable_udp = True
        self.github_mirror = ""
        self.hot_reload = True  # 启用热重载
        self.tun_mode = False  # TUN 透明代理模式
        self.tun_port = 12345  # 透明代理监听端口
        self.no_proxy = "localhost,127.0.0.1,::1"  # 不走代理的地址
        self._network_detected = False

        self.load_config()

        # 注册信号处理（热重载）
        if self.hot_reload:
            signal.signal(signal.SIGHUP, self.handle_reload)

    def ensure_network_detected(self):
        """按需检测网络，避免本地命令也触发网络探测"""
        if not self._network_detected:
            self.detect_network()
            self._network_detected = True

    def handle_reload(self, signum, frame):
        """处理 SIGHUP 信号，热重载配置"""
        logger.info("收到 SIGHUP 信号，执行热重载...")
        self.load_config()
        if self.generate_config():
            # 使用 USR1 信号触发 Xray 热重载
            try:
                subprocess.run(["killall", "-USR1", "xray"], check=False)
                logger.info("Xray 热重载完成")
            except Exception as e:
                logger.warning(f"热重载失败，尝试正常重启: {e}")
                self.restart_xray()

    def detect_network(self):
        """检测网络并找到最佳镜像"""
        test_url = "https://github.com/XTLS/Xray-core/releases/latest"

        # 尝试直连
        try:
            req = urllib.request.Request(test_url, method="HEAD")
            req.add_header("User-Agent", "Mozilla/5.0")
            urllib.request.urlopen(req, timeout=5)
            self.github_mirror = ""
            logger.info("GitHub 可直连")
            return
        except Exception:
            pass

        # 尝试镜像
        for mirror in GH_MIRRORS[:-1]:
            try:
                req = urllib.request.Request(mirror + test_url, method="HEAD")
                req.add_header("User-Agent", "Mozilla/5.0")
                urllib.request.urlopen(req, timeout=5)
                self.github_mirror = mirror
                logger.info(f"使用 GitHub 镜像: {mirror}")
                return
            except Exception:
                continue

        logger.warning("无法连接 GitHub 及镜像，在线功能将不可用")

    def load_config(self):
        """加载配置文件（支持多订阅）"""
        if os.path.exists(INI_FILE):
            config = ConfigParser()
            config.read(INI_FILE, encoding="utf-8")

            # 加载订阅列表（支持多个）
            if "subscription" in config:
                # 兼容旧版单订阅
                single_url = config["subscription"].get("url", "")
                if single_url:
                    self.subscriptions = [{"name": "default", "url": single_url}]
                else:
                    # 新版多订阅格式
                    self.subscriptions = []
                    for key in config["subscription"]:
                        if key.startswith("url"):
                            name = key[3:] if key != "url" else "default"
                            url = config["subscription"][key]
                            if url:
                                self.subscriptions.append({"name": name, "url": url})

                self.auto_update_interval = config["subscription"].getint("interval", 3600)

            if "local" in config:
                self.local_socks_port = config["local"].getint("socks_port", 10808)
                self.local_http_port = config["local"].getint("http_port", 10809)
                self.enable_udp = config["local"].getboolean("udp", True)
                self.hot_reload = config["local"].getboolean("hot_reload", True)
                self.tun_mode = config["local"].getboolean("tun_mode", False)
                tun_port = config["local"].getint("tun_port", 12345)
                if 1 <= tun_port <= 65535:
                    self.tun_port = tun_port
                else:
                    logger.warning(f"tun_port {tun_port} 超出有效范围 (1-65535)，使用默认值 12345")
                self.no_proxy = config["local"].get("no_proxy", "localhost,127.0.0.1,::1")

            if "node" in config:
                self.selected_node = config["node"].getint("selected", 0)

            logger.info(f"配置文件加载成功，共 {len(self.subscriptions)} 个订阅")
        else:
            logger.warning(f"配置文件不存在: {INI_FILE}")

    def save_subscription_data(self, data):
        """保存订阅数据"""
        os.makedirs(os.path.dirname(SUBSCRIPTION_FILE), exist_ok=True)
        with open(SUBSCRIPTION_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def load_subscription_data(self):
        """加载订阅数据"""
        if os.path.exists(SUBSCRIPTION_FILE):
            with open(SUBSCRIPTION_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        return None

    def fetch_subscription(self, url):
        """获取订阅链接内容"""
        self.ensure_network_detected()
        if not url:
            logger.error("订阅链接为空")
            return None

        # 仅允许 http/https 协议，防止 file:// 等本地资源访问
        parsed = urllib.parse.urlparse(url)
        if parsed.scheme not in ("http", "https"):
            logger.error(f"不支持的 URL 协议: {parsed.scheme}")
            return None

        try:
            headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

            req = urllib.request.Request(url, headers=headers)

            with urllib.request.urlopen(req, timeout=30) as response:
                content = response.read()

                try:
                    text = content.decode("utf-8")
                except UnicodeDecodeError:
                    text = content.decode("utf-8", errors="ignore")

                return text

        except Exception as e:
            logger.error(f"获取订阅失败: {e}")
            return None

    def parse_base64(self, text):
        """解析 Base64 编码"""
        try:
            padding = 4 - len(text) % 4
            if padding != 4:
                text += "=" * padding
            return base64.b64decode(text).decode("utf-8", errors="ignore")
        except Exception:
            return None

    def parse_vmess(self, url):
        """解析 VMess 链接"""
        try:
            b64_data = url[8:]
            padding = 4 - len(b64_data) % 4
            if padding != 4:
                b64_data += "=" * padding

            json_str = base64.b64decode(b64_data).decode("utf-8", errors="ignore")
            node = json.loads(json_str)

            return {
                "type": "vmess",
                "name": node.get("ps", "unnamed"),
                "server": node.get("add", ""),
                "port": int(node.get("port", 0)),
                "uuid": node.get("id", ""),
                "alterId": int(node.get("aid", 0)),
                "security": node.get("scy", "auto"),
                "network": node.get("net", "tcp"),
                "tls": node.get("tls", ""),
                "sni": node.get("sni", ""),
                "host": node.get("host", ""),
                "path": node.get("path", ""),
            }
        except Exception as e:
            logger.error(f"解析 VMess 失败: {e}")
            return None

    def parse_vless(self, url):
        """解析 VLESS 链接"""
        try:
            url = url[8:]

            if "#" in url:
                url, name = url.rsplit("#", 1)
                name = urllib.parse.unquote(name)
            else:
                name = "unnamed"

            if "?" in url:
                main_part, params = url.split("?", 1)
            else:
                main_part, params = url, ""

            uuid, rest = main_part.split("@", 1)
            server, port = rest.rsplit(":", 1)
            port = int(port)

            param_dict = urllib.parse.parse_qs(params)

            return {
                "type": "vless",
                "name": name,
                "server": server,
                "port": port,
                "uuid": uuid,
                "encryption": param_dict.get("encryption", ["none"])[0],
                "flow": param_dict.get("flow", [""])[0],
                "security": param_dict.get("security", [""])[0],
                "sni": param_dict.get("sni", [""])[0],
                "fp": param_dict.get("fp", [""])[0],
                "pbk": param_dict.get("pbk", [""])[0],
                "sid": param_dict.get("sid", [""])[0],
                "spx": param_dict.get("spx", [""])[0],
                "net_type": param_dict.get("type", ["tcp"])[0],
                "host": param_dict.get("host", [""])[0],
                "path": urllib.parse.unquote(param_dict.get("path", [""])[0]),
            }
        except Exception as e:
            logger.error(f"解析 VLESS 失败: {e}")
            return None

    def parse_ss(self, url):
        """解析 Shadowsocks 链接"""
        try:
            if url.startswith("ss://"):
                url = url[5:]

            if "#" in url:
                url, name = url.rsplit("#", 1)
                name = urllib.parse.unquote(name)
            else:
                name = "unnamed"

            if "@" not in url:
                padding = 4 - len(url) % 4
                if padding != 4:
                    url += "=" * padding
                decoded = base64.b64decode(url).decode("utf-8", errors="ignore")
                method_pass, server_port = decoded.split("@", 1)
                method, password = method_pass.split(":", 1)
                server, port = server_port.rsplit(":", 1)
            else:
                method_pass, server_port = url.split("@", 1)
                method, password = method_pass.split(":", 1)
                server, port = server_port.rsplit(":", 1)

            return {
                "type": "shadowsocks",
                "name": name,
                "server": server,
                "port": int(port),
                "method": method,
                "password": password,
            }
        except Exception as e:
            logger.error(f"解析 SS 失败: {e}")
            return None

    def parse_trojan(self, url):
        """解析 Trojan 链接"""
        try:
            url = url[9:]

            if "#" in url:
                url, name = url.rsplit("#", 1)
                name = urllib.parse.unquote(name)
            else:
                name = "unnamed"

            if "?" in url:
                main_part, params = url.split("?", 1)
            else:
                main_part, params = url, ""

            password, rest = main_part.split("@", 1)
            server, port = rest.rsplit(":", 1)
            port = int(port)

            param_dict = urllib.parse.parse_qs(params)

            return {
                "type": "trojan",
                "name": name,
                "server": server,
                "port": port,
                "password": password,
                "sni": param_dict.get("sni", [""])[0],
            }
        except Exception as e:
            logger.error(f"解析 Trojan 失败: {e}")
            return None

    def parse_clash(self, content):
        """解析 Clash YAML 配置"""
        try:
            import yaml
        except ImportError:
            logger.error("解析 Clash 格式需要 pyyaml，请执行: pip install pyyaml")
            return []
        nodes = []
        try:
            data = yaml.safe_load(content)
            if not data or "proxies" not in data:
                return nodes

            for proxy in data["proxies"]:
                try:
                    node = self.convert_clash_proxy(proxy)
                    if node:
                        nodes.append(node)
                except Exception as e:
                    logger.error(f"转换 Clash 节点失败: {e}")
                    continue

            logger.info(f"从 Clash 配置解析了 {len(nodes)} 个节点")
        except Exception as e:
            logger.error(f"解析 Clash 配置失败: {e}")

        return nodes

    def convert_clash_proxy(self, proxy):
        """将 Clash proxy 转换为内部格式"""
        proxy_type = proxy.get("type", "").lower()
        name = proxy.get("name", "unnamed")
        server = proxy.get("server", "")
        port = proxy.get("port", 0)

        if proxy_type == "ss":
            return {
                "type": "shadowsocks",
                "name": name,
                "server": server,
                "port": port,
                "method": proxy.get("cipher", "aes-256-gcm"),
                "password": proxy.get("password", ""),
            }
        elif proxy_type == "vmess":
            return {
                "type": "vmess",
                "name": name,
                "server": server,
                "port": port,
                "uuid": proxy.get("uuid", ""),
                "alterId": proxy.get("alterId", 0),
                "security": proxy.get("cipher", "auto"),
                "network": proxy.get("network", "tcp"),
                "tls": "tls" if proxy.get("tls") else "",
                "sni": proxy.get("servername", ""),
                "host": (
                    proxy.get("ws-headers", {}).get("Host", "")
                    if proxy.get("ws-headers")
                    else proxy.get("ws-opts", {}).get("headers", {}).get("Host", "")
                ),
                "path": proxy.get("ws-path", "") if "ws-path" in proxy else proxy.get("ws-opts", {}).get("path", ""),
            }
        elif proxy_type == "trojan":
            return {
                "type": "trojan",
                "name": name,
                "server": server,
                "port": port,
                "password": proxy.get("password", ""),
                "sni": proxy.get("sni", ""),
            }
        elif proxy_type == "vless":
            return {
                "type": "vless",
                "name": name,
                "server": server,
                "port": port,
                "uuid": proxy.get("uuid", ""),
                "encryption": proxy.get("cipher", "none"),
                "flow": proxy.get("flow", ""),
                "security": "tls" if proxy.get("tls") else "",
                "sni": proxy.get("servername", ""),
                "net_type": proxy.get("network", "tcp"),
                "path": proxy.get("ws-opts", {}).get("path", ""),
            }
        else:
            logger.warning(f"不支持的 Clash 协议: {proxy_type}")
            return None

    def parse_subscription(self, content):
        """解析订阅内容（支持多种格式）"""
        nodes = []

        if not content:
            return nodes

        # 尝试解析为 Clash YAML
        if content.strip().startswith("proxies:") or "proxies:" in content[:200]:
            logger.info("检测到 Clash 格式")
            return self.parse_clash(content)

        # 尝试 Base64 解码
        decoded = self.parse_base64(content)
        if decoded:
            lines = decoded.strip().split("\n")
        else:
            lines = content.strip().split("\n")

        for line in lines:
            line = line.strip()
            if not line:
                continue

            node = None

            if line.startswith("vmess://"):
                node = self.parse_vmess(line)
            elif line.startswith("vless://"):
                node = self.parse_vless(line)
            elif line.startswith("ss://"):
                node = self.parse_ss(line)
            elif line.startswith("trojan://"):
                node = self.parse_trojan(line)
            elif line.startswith("http://") or line.startswith("https://"):
                # 可能是订阅嵌套，忽略
                continue

            if node:
                nodes.append(node)
                logger.info(f"解析节点: {node['name']}")

        return nodes

    def update_subscription(self, name=None):
        """更新订阅（支持多订阅）"""
        all_nodes = []
        update_time = datetime.now().isoformat()

        subs_to_update = self.subscriptions
        if name:
            subs_to_update = [s for s in self.subscriptions if s["name"] == name]

        for sub in subs_to_update:
            if not sub.get("url"):
                continue

            logger.info(f"正在更新订阅 [{sub['name']}]: {sub['url'][:50]}...")

            content = self.fetch_subscription(sub["url"])
            if not content:
                logger.error(f"订阅 [{sub['name']}] 获取失败")
                continue

            nodes = self.parse_subscription(content)
            if nodes:
                # 为节点添加订阅来源标记
                for node in nodes:
                    node["subscription"] = sub["name"]
                all_nodes.extend(nodes)
                logger.info(f"订阅 [{sub['name']}] 解析成功: {len(nodes)} 个节点")
            else:
                logger.warning(f"订阅 [{sub['name']}] 未解析到节点")

        if not all_nodes:
            logger.error("没有成功获取任何订阅")
            return False

        # 保存合并的订阅数据
        data = {
            "update_time": update_time,
            "node_count": len(all_nodes),
            "subscriptions": [s["name"] for s in self.subscriptions],
            "nodes": all_nodes,
        }
        self.save_subscription_data(data)

        logger.info(f"订阅更新完成，共 {len(all_nodes)} 个节点")
        return True

    def test_node_latency(self, node, timeout=5):
        """测试节点延迟（TCP 连接测试）"""
        try:
            start = time.time()
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(timeout)
            result = sock.connect_ex((node["server"], node["port"]))
            sock.close()

            if result == 0:
                latency = (time.time() - start) * 1000
                return {"node": node, "latency": latency, "ok": True}
            else:
                return {"node": node, "latency": -1, "ok": False}
        except Exception as e:
            return {"node": node, "latency": -1, "ok": False, "error": str(e)}

    def test_all_nodes(self, max_workers=10):
        """测试所有节点延迟"""
        data = self.load_subscription_data()
        if not data or not data.get("nodes"):
            print("没有可用的节点数据")
            return

        nodes = data["nodes"]
        results = []

        print(f"\n正在测试 {len(nodes)} 个节点...")
        print("=" * 80)

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {executor.submit(self.test_node_latency, node): i for i, node in enumerate(nodes)}

            for future in as_completed(futures):
                i = futures[future]
                result = future.result()
                results.append((i, result))

                node = result["node"]
                if result["ok"]:
                    print(f"[{i}] {node['name'][:40]:<40} {result['latency']:.1f}ms")
                else:
                    print(f"[{i}] {node['name'][:40]:<40} 超时/失败")

        # 排序并显示结果
        results.sort(key=lambda x: x[1]["latency"] if x[1]["ok"] else 999999)

        print("\n" + "=" * 80)
        print("延迟排序（前10）:")
        print("-" * 80)
        for i, (idx, result) in enumerate(results[:10]):
            if result["ok"]:
                node = result["node"]
                marker = " *" if idx == self.selected_node else "  "
                print(f"{marker} [{idx}] {node['name'][:40]:<40} {result['latency']:.1f}ms")

        return results

    def auto_select_best_node(self):
        """自动选择最佳节点"""
        results = self.test_all_nodes()

        # 找到延迟最低的正常节点
        best = None
        for idx, result in results:
            if result["ok"]:
                best = idx
                break

        if best is not None:
            print(f"\n自动选择最佳节点: [{best}]")
            self.select_node(best)
            self.generate_config()
            return True
        else:
            print("\n没有可用的节点")
            return False

    def generate_xray_config(self, node):
        """生成 Xray 配置文件"""
        config = {
            "log": {
                "loglevel": "warning",
                "access": "/var/log/xray/access.log",
                "error": "/var/log/xray/error.log",
            },
            "inbounds": [
                {
                    "tag": "socks",
                    "port": self.local_socks_port,
                    "listen": "127.0.0.1",
                    "protocol": "socks",
                    "sniffing": {
                        "enabled": True,
                        "destOverride": ["http", "tls", "quic"],
                    },
                    "settings": {
                        "auth": "noauth",
                        "udp": self.enable_udp,
                        "ip": "127.0.0.1",
                    },
                },
                {
                    "tag": "http",
                    "port": self.local_http_port,
                    "listen": "127.0.0.1",
                    "protocol": "http",
                    "sniffing": {
                        "enabled": True,
                        "destOverride": ["http", "tls", "quic"],
                    },
                },
            ],
            "outbounds": [],
            "routing": {
                "domainStrategy": "IPIfNonMatch",
                "rules": [
                    {"type": "field", "ip": ["geoip:private"], "outboundTag": "direct"},
                    {
                        "type": "field",
                        "domain": ["geosite:cn"],
                        "outboundTag": "direct",
                    },
                    {"type": "field", "ip": ["geoip:cn"], "outboundTag": "direct"},
                ],
            },
            "dns": {
                "servers": [
                    "https+local://1.1.1.1/dns-query",
                    "https+local://8.8.8.8/dns-query",
                    "localhost",
                ]
            },
        }

        # TUN 透明代理入站（dokodemo-door）
        if self.tun_mode:
            config["inbounds"].append(
                {
                    "tag": "transparent",
                    "port": self.tun_port,
                    "listen": "127.0.0.1",
                    "protocol": "dokodemo-door",
                    "settings": {
                        "network": "tcp",
                        "followRedirect": True,
                    },
                    "sniffing": {
                        "enabled": True,
                        "destOverride": ["http", "tls", "quic"],
                    },
                }
            )

        outbound = self.create_outbound(node)
        config["outbounds"].append(outbound)
        config["outbounds"].append({"protocol": "freedom", "tag": "direct"})
        config["outbounds"].append({"protocol": "blackhole", "tag": "block"})

        config["routing"]["rules"].append({"type": "field", "network": "tcp,udp", "outboundTag": "proxy"})

        return config

    def create_outbound(self, node):
        """创建出站配置"""
        outbound = {
            "tag": "proxy",
            "protocol": node["type"],
            "settings": {},
            "streamSettings": {},
            "mux": {"enabled": False, "concurrency": -1},
        }

        node_type = node["type"]

        if node_type == "vmess":
            outbound["settings"] = {
                "vnext": [
                    {
                        "address": node["server"],
                        "port": node["port"],
                        "users": [
                            {
                                "id": node["uuid"],
                                "alterId": node.get("alterId", 0),
                                "security": node.get("security", "auto"),
                                "level": 0,
                            }
                        ],
                    }
                ]
            }

            stream_settings = {"network": node.get("network", "tcp")}

            if node.get("tls"):
                stream_settings["security"] = node["tls"]
                if node["tls"] == "tls":
                    stream_settings["tlsSettings"] = {
                        "serverName": node.get("sni", node["server"]),
                        "allowInsecure": False,
                    }

            if node.get("network") == "ws":
                stream_settings["wsSettings"] = {
                    "path": node.get("path", "/"),
                    "headers": {"Host": node.get("host", node["server"])},
                }

            outbound["streamSettings"] = stream_settings

        elif node_type == "vless":
            outbound["settings"] = {
                "vnext": [
                    {
                        "address": node["server"],
                        "port": node["port"],
                        "users": [
                            {
                                "id": node["uuid"],
                                "encryption": node.get("encryption", "none"),
                                "flow": node.get("flow", ""),
                                "level": 0,
                            }
                        ],
                    }
                ]
            }

            net_type = node.get("net_type", "tcp")
            stream_settings = {"network": net_type}

            security = node.get("security", "")
            if security:
                stream_settings["security"] = security

                if security == "tls":
                    stream_settings["tlsSettings"] = {
                        "serverName": node.get("sni", node["server"]),
                        "allowInsecure": False,
                    }
                elif security == "reality":
                    stream_settings["realitySettings"] = {
                        "serverName": node.get("sni", node["server"]),
                        "fingerprint": node.get("fp", "chrome"),
                        "publicKey": node.get("pbk", ""),
                        "shortId": node.get("sid", ""),
                        "spiderX": node.get("spx", ""),
                    }

            if net_type == "ws":
                stream_settings["wsSettings"] = {
                    "path": node.get("path", "/"),
                    "headers": {"Host": node.get("host", node["server"])},
                }
            elif net_type == "grpc":
                stream_settings["grpcSettings"] = {"serviceName": node.get("path", "")}

            outbound["streamSettings"] = stream_settings

        elif node_type == "shadowsocks":
            outbound["settings"] = {
                "servers": [
                    {
                        "address": node["server"],
                        "port": node["port"],
                        "method": node["method"],
                        "password": node["password"],
                        "level": 0,
                    }
                ]
            }

        elif node_type == "trojan":
            outbound["settings"] = {
                "servers": [
                    {
                        "address": node["server"],
                        "port": node["port"],
                        "password": node["password"],
                        "level": 0,
                    }
                ]
            }

            stream_settings = {"network": "tcp"}

            if node.get("sni"):
                stream_settings["security"] = "tls"
                stream_settings["tlsSettings"] = {
                    "serverName": node["sni"],
                    "allowInsecure": False,
                }

            outbound["streamSettings"] = stream_settings

        return outbound

    def generate_config(self, node_index=None):
        """生成 Xray 配置文件"""
        if node_index is None:
            node_index = self.selected_node

        data = self.load_subscription_data()
        if not data or not data.get("nodes"):
            logger.error("没有可用的订阅数据")
            return False

        nodes = data["nodes"]
        if node_index >= len(nodes):
            logger.error(f"节点索引 {node_index} 超出范围")
            return False

        node = nodes[node_index]
        logger.info(f"使用节点 [{node_index}]: {node['name']}")

        config = self.generate_xray_config(node)

        os.makedirs(os.path.dirname(XRAY_CONFIG), exist_ok=True)
        os.makedirs("/var/log/xray", exist_ok=True)

        with open(XRAY_CONFIG, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2, ensure_ascii=False)

        subprocess.run([_resolve_executable("chmod"), "644", XRAY_CONFIG], check=False)

        logger.info(f"配置文件已保存: {XRAY_CONFIG}")
        return True

    def reload_xray(self):
        """热重载 Xray"""
        if not self.hot_reload:
            return self.restart_xray()

        try:
            # 发送 USR1 信号触发热重载
            result = subprocess.run(
                ["killall", "-USR1", "xray"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True,
            )
            if result.returncode == 0:
                logger.info("Xray 热重载成功")
                return True
            else:
                logger.warning("热重载失败，尝试重启...")
                return self.restart_xray()
        except Exception as e:
            logger.error(f"热重载出错: {e}")
            return self.restart_xray()

    def start_xray(self):
        """启动 Xray 服务"""
        logger.info("启动 Xray 服务...")
        result = subprocess.run(
            [_resolve_executable("systemctl"), "start", "xray"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True,
        )
        if result.returncode == 0:
            logger.info("Xray 服务已启动")
            return True
        else:
            logger.error(f"启动失败: {result.stderr}")
            return False

    def stop_xray(self):
        """停止 Xray 服务"""
        logger.info("停止 Xray 服务...")
        subprocess.run([_resolve_executable("systemctl"), "stop", "xray"], check=False)
        logger.info("Xray 服务已停止")

    def restart_xray(self):
        """重启 Xray 服务"""
        logger.info("重启 Xray 服务...")
        result = subprocess.run(
            [_resolve_executable("systemctl"), "restart", "xray"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True,
        )
        if result.returncode == 0:
            logger.info("Xray 服务已重启")
            return True
        else:
            logger.error(f"重启失败: {result.stderr}")
            return False

    def status_xray(self):
        """查看 Xray 状态"""
        subprocess.run([_resolve_executable("systemctl"), "status", "xray"])

    def list_nodes(self):
        """列出所有节点"""
        data = self.load_subscription_data()
        if not data or not data.get("nodes"):
            print("\n没有可用的节点数据，请先更新订阅")
            return

        nodes = data["nodes"]
        print(f"\n{'=' * 85}")
        print(f"共 {len(nodes)} 个节点 (最后更新: {data.get('update_time', '未知')})")
        print(f"{'=' * 85}")
        print(f"{'索引':<6}{'类型':<12}{'订阅':<10}{'名称':<35}{'服务器':<20}")
        print("-" * 85)

        for i, node in enumerate(nodes):
            marker = " *" if i == self.selected_node else "  "
            name = (node["name"][:33] + "..") if len(node["name"]) > 33 else node["name"]
            server = (node["server"][:18] + "..") if len(node["server"]) > 18 else node["server"]
            sub = node.get("subscription", "default")[:8]
            print(f"{marker}{i:<4}{node['type']:<12}{sub:<10}{name:<35}{server:<20}")

        print("-" * 85)
        print("带 * 的为当前选中节点")
        print()

    def select_node(self, index):
        """选择节点"""
        data = self.load_subscription_data()
        if not data or not data.get("nodes"):
            print("没有可用的节点数据")
            return False

        nodes = data["nodes"]
        if index < 0 or index >= len(nodes):
            print(f"节点索引 {index} 超出范围 (0-{len(nodes) - 1})")
            return False

        self.selected_node = index

        config = ConfigParser()
        if os.path.exists(INI_FILE):
            config.read(INI_FILE, encoding="utf-8")

        if "node" not in config:
            config["node"] = {}
        config["node"]["selected"] = str(index)

        with open(INI_FILE, "w", encoding="utf-8") as f:
            config.write(f)

        print(f"已选择节点 [{index}]: {nodes[index]['name']}")
        return True

    # Keys managed in /etc/environment
    _ENV_KEYS = (
        "http_proxy", "https_proxy", "HTTP_PROXY", "HTTPS_PROXY",
        "all_proxy", "no_proxy", "NO_PROXY",
    )

    def _update_etc_environment(self, add: bool) -> None:
        """Add or remove proxy vars from /etc/environment (for GUI / PAM sessions)."""
        lines: list[str] = []
        if os.path.exists(ETC_ENVIRONMENT):
            with open(ETC_ENVIRONMENT, "r", encoding="utf-8") as f:
                lines = f.readlines()
        # Strip any previously written proxy entries
        lines = [
            l for l in lines
            if not any(l.strip().startswith(k + "=") for k in self._ENV_KEYS)
        ]
        if add:
            http_url = f"http://127.0.0.1:{self.local_http_port}"
            socks_url = f"socks5://127.0.0.1:{self.local_socks_port}"
            new_entries = [
                f"http_proxy={http_url}\n",
                f"https_proxy={http_url}\n",
                f"HTTP_PROXY={http_url}\n",
                f"HTTPS_PROXY={http_url}\n",
                f"all_proxy={socks_url}\n",
                f"no_proxy={self.no_proxy}\n",
                f"NO_PROXY={self.no_proxy}\n",
            ]
            # Ensure the file ends with a newline before appending
            if lines and not lines[-1].endswith("\n"):
                lines[-1] += "\n"
            lines.extend(new_entries)
        with open(ETC_ENVIRONMENT, "w", encoding="utf-8") as f:
            f.writelines(lines)

    @staticmethod
    def install_shell_functions() -> None:
        """写入 /etc/profile.d/xray-client-functions.sh，提供免 source 的 proxy-on/proxy-off 壳函数。"""
        content = (
            "# xray-client shell convenience functions\n"
            "# Sourced automatically by new bash/sh sessions.\n"
            "# proxy-on / proxy-off apply changes to the CURRENT shell without manual sourcing.\n"
            "proxy-on() {\n"
            "    sudo xray-client proxy-on \"$@\" && . /etc/profile.d/xray-proxy.sh\n"
            "}\n"
            "proxy-off() {\n"
            "    sudo xray-client proxy-off \"$@\" && \\\n"
            "        unset http_proxy https_proxy HTTP_PROXY HTTPS_PROXY all_proxy no_proxy NO_PROXY\n"
            "}\n"
        )
        os.makedirs(os.path.dirname(PROXY_FUNCTIONS_FILE), exist_ok=True)
        with open(PROXY_FUNCTIONS_FILE, "w", encoding="utf-8") as f:
            f.write(content)
        subprocess.run([_resolve_executable("chmod"), "644", PROXY_FUNCTIONS_FILE], check=False)

    def enable_proxy(self):
        """开启系统 HTTP/HTTPS 代理环境变量"""
        content = (
            "#!/bin/sh\n"
            "# Generated by xray-client proxy-on - DO NOT EDIT MANUALLY\n"
            f"export http_proxy=http://127.0.0.1:{self.local_http_port}\n"
            f"export https_proxy=http://127.0.0.1:{self.local_http_port}\n"
            f"export HTTP_PROXY=http://127.0.0.1:{self.local_http_port}\n"
            f"export HTTPS_PROXY=http://127.0.0.1:{self.local_http_port}\n"
            f"export all_proxy=socks5://127.0.0.1:{self.local_socks_port}\n"
            f"export no_proxy={self.no_proxy}\n"
            f"export NO_PROXY={self.no_proxy}\n"
        )
        try:
            os.makedirs(os.path.dirname(PROXY_PROFILE), exist_ok=True)
            with open(PROXY_PROFILE, "w", encoding="utf-8") as f:
                f.write(content)
            subprocess.run([_resolve_executable("chmod"), "644", PROXY_PROFILE], check=False)
            self._update_etc_environment(add=True)
            self.install_shell_functions()
            print("系统代理已开启")
            print(f"  HTTP  代理: http://127.0.0.1:{self.local_http_port}")
            print(f"  SOCKS 代理: socks5://127.0.0.1:{self.local_socks_port}")
            print(f"\n新终端直接使用 proxy-on / proxy-off 即可（自动 source，无需手动操作）。")
            print(f"当前终端请执行（仅需一次）: source {PROXY_FUNCTIONS_FILE}")
            print("\nGUI 应用（浏览器等）请重新登录系统后生效，或使用 tun-on 透明代理模式。")
            return True
        except Exception as e:
            logger.error(f"开启系统代理失败: {e}")
            return False

    def disable_proxy(self):
        """关闭系统 HTTP/HTTPS 代理环境变量"""
        if os.path.exists(PROXY_PROFILE):
            try:
                os.remove(PROXY_PROFILE)
                self._update_etc_environment(add=False)
                print("系统代理已关闭")
                print("当前终端请执行: unset http_proxy https_proxy HTTP_PROXY HTTPS_PROXY all_proxy")
                print("GUI 应用请重新登录系统后生效。")
            except OSError as e:
                logger.error(f"关闭系统代理失败: {e}")
                return False
        else:
            # /etc/profile.d/ file may have been removed manually;
            # still clean up /etc/environment in case entries linger.
            self._update_etc_environment(add=False)
            print("系统代理未开启")
        return True

    def _run_iptables(self, *args):
        """执行 iptables 命令，返回 CompletedProcess"""
        cmd = [_resolve_executable("iptables")] + list(args)
        return subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)

    def _get_xray_uid(self):
        """获取 Xray 进程运行的 UID，用于 iptables 豁免，避免透明代理回环"""
        import pwd

        # 优先从 systemd 服务配置读取运行用户
        try:
            result = subprocess.run(
                ["systemctl", "show", "xray", "--property=User", "--value"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True,
            )
            xray_user = result.stdout.strip()
            if xray_user:
                return pwd.getpwnam(xray_user).pw_uid
        except Exception:
            pass

        # 备选：从运行中的 xray 进程读取 UID
        try:
            result = subprocess.run(["pgrep", "-x", "xray"], stdout=subprocess.PIPE, universal_newlines=True)
            pid = result.stdout.strip().split("\n")[0]
            if pid:
                with open(f"/proc/{pid}/status") as f:
                    for line in f:
                        if line.startswith("Uid:"):
                            return int(line.split()[1])
        except Exception:
            pass

        return None

    def _setup_tproxy_rules(self):
        """设置 iptables 透明代理规则（NAT REDIRECT）"""
        tport = str(self.tun_port)

        # 创建 XRAY 链（忽略已存在的错误）
        self._run_iptables("-t", "nat", "-N", IPTABLES_CHAIN)
        # 清空链
        self._run_iptables("-t", "nat", "-F", IPTABLES_CHAIN)

        # 豁免 Xray 自身流量，防止出站连接被 REDIRECT 回环
        xray_uid = self._get_xray_uid()
        if xray_uid is not None:
            self._run_iptables(
                "-t", "nat", "-A", IPTABLES_CHAIN, "-m", "owner", "--uid-owner", str(xray_uid), "-j", "RETURN"
            )
            logger.info(f"已豁免 Xray 进程流量（UID: {xray_uid}）")
        else:
            logger.warning("无法获取 Xray 进程 UID，透明代理可能出现回环，请确认 Xray 运行用户")

        # 跳过私有地址和回环地址
        private_ranges = [
            "0.0.0.0/8",
            "10.0.0.0/8",
            "127.0.0.0/8",
            "169.254.0.0/16",
            "172.16.0.0/12",
            "192.168.0.0/16",
            "224.0.0.0/4",
            "240.0.0.0/4",
        ]
        for cidr in private_ranges:
            self._run_iptables("-t", "nat", "-A", IPTABLES_CHAIN, "-d", cidr, "-j", "RETURN")

        # 重定向 TCP 到透明代理端口
        self._run_iptables("-t", "nat", "-A", IPTABLES_CHAIN, "-p", "tcp", "-j", "REDIRECT", "--to-ports", tport)

        # 将 OUTPUT 链（本机出站流量）接入 XRAY 链
        # 先检查是否已经存在，避免重复添加
        check = self._run_iptables("-t", "nat", "-C", "OUTPUT", "-p", "tcp", "-j", IPTABLES_CHAIN)
        if check.returncode != 0:
            self._run_iptables("-t", "nat", "-A", "OUTPUT", "-p", "tcp", "-j", IPTABLES_CHAIN)

        logger.info(f"透明代理 iptables 规则已设置，监听端口: {tport}")

    def _cleanup_tproxy_rules(self):
        """清理 iptables 透明代理规则"""
        # 从 OUTPUT 链移除引用
        self._run_iptables("-t", "nat", "-D", "OUTPUT", "-p", "tcp", "-j", IPTABLES_CHAIN)
        # 清空并删除 XRAY 链
        self._run_iptables("-t", "nat", "-F", IPTABLES_CHAIN)
        self._run_iptables("-t", "nat", "-X", IPTABLES_CHAIN)
        logger.info("透明代理 iptables 规则已清理")

    def _save_tun_mode(self, enabled):
        """持久化 TUN 模式开关到配置文件"""
        config = ConfigParser()
        if os.path.exists(INI_FILE):
            config.read(INI_FILE, encoding="utf-8")
        if "local" not in config:
            config["local"] = {}
        config["local"]["tun_mode"] = "true" if enabled else "false"
        with open(INI_FILE, "w", encoding="utf-8") as f:
            config.write(f)
        self.tun_mode = enabled

    def enable_tun(self):
        """开启 TUN 透明代理模式"""
        # 1. 更新内存状态并生成配置（尚未持久化）
        self.tun_mode = True
        if not self.generate_config():
            self.tun_mode = False
            return False

        # 2. 设置 iptables 规则
        self._setup_tproxy_rules()

        # 3. 重启 Xray；若失败则回滚 iptables 并恢复内存状态
        if not self.restart_xray():
            logger.error("Xray 重启失败，回滚 iptables 规则")
            self._cleanup_tproxy_rules()
            self.tun_mode = False
            self.generate_config()
            return False

        # 4. 全部成功后才持久化
        self._save_tun_mode(True)
        print("TUN 模式已开启")
        print(f"  透明代理端口: {self.tun_port}")
        print("  本机所有 TCP 流量将通过 Xray 代理（私有地址除外）")
        return True

    def disable_tun(self):
        """关闭 TUN 透明代理模式"""
        # 1. 无论后续是否成功，先清理 iptables 并持久化关闭状态
        self._cleanup_tproxy_rules()
        self._save_tun_mode(False)

        # 2. 重新生成不含透明代理入站的配置
        if not self.generate_config():
            return False

        # 3. 重启 Xray（不影响 iptables 已清理的结果）
        self.restart_xray()
        print("TUN 模式已关闭")
        return True


def main():
    parser = argparse.ArgumentParser(
        description="Xray Client - 支持 JustMySocks 订阅",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  %(prog)s update                    # 更新所有订阅
  %(prog)s update -n default         # 更新指定订阅
  %(prog)s list                      # 列出所有节点
  %(prog)s select -i 0               # 选择第一个节点
  %(prog)s test                      # 测试所有节点延迟
  %(prog)s auto-select               # 自动选择最佳节点
  %(prog)s apply                     # 应用配置
  %(prog)s reload                    # 热重载配置
  %(prog)s status                    # 查看 Xray 状态
  %(prog)s proxy-on                  # 开启系统代理（HTTP/SOCKS 环境变量）
  %(prog)s proxy-off                 # 关闭系统代理
  %(prog)s tun-on                    # 开启 TUN 透明代理模式
  %(prog)s tun-off                   # 关闭 TUN 透明代理模式

配置文件: /etc/xray-client/config.ini
        """,
    )

    subparsers = parser.add_subparsers(dest="command", help="可用命令")

    # update 命令
    update_parser = subparsers.add_parser("update", help="更新订阅")
    update_parser.add_argument("-n", "--name", help="指定订阅名称")

    # list 命令
    subparsers.add_parser("list", help="列出所有节点")

    # select 命令
    select_parser = subparsers.add_parser("select", help="选择节点")
    select_parser.add_argument("-i", "--index", type=int, required=True, help="节点索引")

    # test 命令
    test_parser = subparsers.add_parser("test", help="测试节点延迟")
    test_parser.add_argument("-t", "--timeout", type=int, default=5, help="超时时间(秒)")

    # auto-select 命令
    subparsers.add_parser("auto-select", help="自动选择最佳节点")

    # apply 命令
    subparsers.add_parser("apply", help="应用配置")

    # reload 命令
    subparsers.add_parser("reload", help="热重载配置")

    # start/stop/restart/status 命令
    subparsers.add_parser("start", help="启动 Xray 服务")
    subparsers.add_parser("stop", help="停止 Xray 服务")
    subparsers.add_parser("restart", help="重启 Xray 服务")
    subparsers.add_parser("status", help="查看 Xray 状态")

    # ping 命令
    subparsers.add_parser("ping", help="测试代理连接")

    # proxy-on / proxy-off 命令
    subparsers.add_parser("proxy-on", help="开启系统代理（写入环境变量到 /etc/profile.d/）")
    subparsers.add_parser("proxy-off", help="关闭系统代理（清除环境变量）")

    # tun-on / tun-off 命令
    subparsers.add_parser("tun-on", help="开启 TUN 透明代理模式（iptables + dokodemo-door）")
    subparsers.add_parser("tun-off", help="关闭 TUN 透明代理模式")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    client = XrayClient()

    if args.command == "update":
        if client.update_subscription(args.name):
            client.generate_config()
            print("\n订阅更新完成")

    elif args.command == "list":
        client.list_nodes()

    elif args.command == "select":
        if client.select_node(args.index):
            client.generate_config()
            print("\n节点已切换，运行 'xray-client apply' 或 'xray-client reload' 应用")

    elif args.command == "test":
        client.test_all_nodes()

    elif args.command == "auto-select":
        if client.auto_select_best_node():
            client.restart_xray()

    elif args.command == "apply":
        client.generate_config()
        client.restart_xray()

    elif args.command == "reload":
        client.generate_config()
        client.reload_xray()

    elif args.command == "start":
        client.start_xray()

    elif args.command == "stop":
        client.stop_xray()

    elif args.command == "restart":
        client.generate_config()
        client.restart_xray()

    elif args.command == "status":
        client.status_xray()

    elif args.command == "proxy-on":
        client.enable_proxy()

    elif args.command == "proxy-off":
        client.disable_proxy()

    elif args.command == "tun-on":
        client.enable_tun()

    elif args.command == "tun-off":
        client.disable_tun()

    elif args.command == "ping":
        print("测试代理连接...")
        result = subprocess.run(
            [
                "curl",
                "-s",
                "-o",
                "/dev/null",
                "-w",
                "%{http_code}",
                "-x",
                f"http://127.0.0.1:{client.local_http_port}",
                "--connect-timeout",
                "10",
                "https://www.google.com",
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True,
        )
        if result.stdout.strip() == "200":
            print("代理连接成功! HTTP 状态码: 200")
        else:
            print(f"代理连接失败，HTTP 状态码: {result.stdout.strip()}")


if __name__ == "__main__":
    main()
