#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Xray Client - 支持 JustMySocks 订阅
复用官方 Xray 安装，仅提供订阅管理功能

独立版本，可以单独下载使用：
wget -O /usr/local/bin/xray-client https://raw.githubusercontent.com/your-repo/xray-client/main/xray-client.py
chmod +x /usr/local/bin/xray-client
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

class XrayClient:
    def __init__(self):
        self.subscription_url = ""
        self.auto_update_interval = 3600
        self.selected_node = 0
        self.local_socks_port = 10808
        self.local_http_port = 10809
        
        self.load_config()
    
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
        result = subprocess.run(['systemctl', 'start', 'xray'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
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
        result = subprocess.run(['systemctl', 'restart', 'xray'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
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
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True
        )
        if result.stdout.strip() == '200':
            print(f"代理连接成功! HTTP 状态码: 200")
        else:
            print(f"代理连接失败，HTTP 状态码: {result.stdout.strip()}")
            print("请检查 Xray 服务是否正常运行")


if __name__ == '__main__':
    main()
