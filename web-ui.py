#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Xray Client Web UI - 简单的 Web 管理界面
"""

import os
import sys
import json
import subprocess
from datetime import datetime
from flask import Flask, render_template_string, jsonify, request

app = Flask(__name__)

# 路径配置
CLIENT_CONFIG_DIR = '/etc/xray-client'
SUBSCRIPTION_FILE = os.path.join(CLIENT_CONFIG_DIR, 'subscription', 'nodes.json')
INI_FILE = os.path.join(CLIENT_CONFIG_DIR, 'config.ini')

# 基本认证 token（通过环境变量设置，未设置则不启用认证）
AUTH_TOKEN = os.environ.get('WEB_UI_TOKEN', '')


def check_auth():
    """检查请求认证"""
    if not AUTH_TOKEN:
        return True  # 未配置 token 则不启用认证
    token = request.args.get('token') or request.headers.get('X-Auth-Token', '')
    return token == AUTH_TOKEN


@app.before_request
def auth_guard():
    """全局认证守卫"""
    if not check_auth():
        return jsonify({'error': 'Unauthorized'}), 401


def load_nodes():
    """加载节点数据"""
    if os.path.exists(SUBSCRIPTION_FILE):
        with open(SUBSCRIPTION_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {'nodes': [], 'update_time': '从未'}


def get_xray_status():
    """获取 Xray 服务状态"""
    try:
        result = subprocess.run(
            ['systemctl', 'is-active', 'xray'],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True
        )
        return result.stdout.strip()
    except Exception:
        return '未知'


@app.route('/')
def index():
    """主页"""
    data = load_nodes()
    status = get_xray_status()

    return render_template_string(
        HTML_TEMPLATE,
        nodes=data.get('nodes', []),
        update_time=data.get('update_time', '从未'),
        count=len(data.get('nodes', [])),
        status=status
    )


@app.route('/api/nodes')
def api_nodes():
    """API: 获取节点列表"""
    return jsonify(load_nodes())


@app.route('/api/status')
def api_status():
    """API: 获取 Xray 状态"""
    return jsonify({'status': get_xray_status()})


@app.route('/api/select', methods=['POST'])
def api_select():
    """API: 选择节点"""
    data = request.get_json(silent=True) or {}
    index = data.get('index')
    if not isinstance(index, int) or index < 0:
        return jsonify({'success': False, 'error': '无效的节点索引'}), 400
    try:
        result = subprocess.run(
            ['xray-client', 'select', '-i', str(index)],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True
        )
        subprocess.run(['xray-client', 'restart'], check=False)
        return jsonify({'success': True, 'output': result.stdout})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


@app.route('/api/update', methods=['POST'])
def api_update():
    """API: 更新订阅"""
    try:
        result = subprocess.run(
            ['xray-client', 'update'],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True,
            timeout=60
        )
        subprocess.run(['xray-client', 'restart'], check=False)
        return jsonify({'success': True, 'output': result.stdout + result.stderr})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


@app.route('/api/restart', methods=['POST'])
def api_restart():
    """API: 重启 Xray"""
    try:
        subprocess.run(['xray-client', 'restart'], check=True)
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


HTML_TEMPLATE = '''<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Xray Client Web UI</title>
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            background: #f5f5f5;
            padding: 20px;
        }
        .container {
            max-width: 1200px;
            margin: 0 auto;
        }
        h1 {
            color: #333;
            margin-bottom: 20px;
            padding-bottom: 10px;
            border-bottom: 2px solid #007bff;
        }
        .status-bar {
            background: white;
            padding: 15px;
            border-radius: 8px;
            margin-bottom: 20px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        .status-badge {
            padding: 5px 15px;
            border-radius: 20px;
            font-weight: bold;
        }
        .status-active { background: #28a745; color: white; }
        .status-inactive { background: #dc3545; color: white; }
        .controls {
            display: flex;
            gap: 10px;
        }
        button {
            padding: 10px 20px;
            border: none;
            border-radius: 5px;
            cursor: pointer;
            font-size: 14px;
            transition: opacity 0.2s;
        }
        button:hover { opacity: 0.8; }
        .btn-primary { background: #007bff; color: white; }
        .btn-success { background: #28a745; color: white; }
        .btn-warning { background: #ffc107; color: #333; }
        .node-list {
            background: white;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            overflow: hidden;
        }
        .node-item {
            padding: 15px;
            border-bottom: 1px solid #eee;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        .node-item:last-child { border-bottom: none; }
        .node-item:hover { background: #f8f9fa; }
        .node-info { flex: 1; }
        .node-name { font-weight: bold; color: #333; margin-bottom: 5px; }
        .node-meta { color: #666; font-size: 13px; }
        .node-type {
            display: inline-block;
            padding: 3px 10px;
            border-radius: 12px;
            font-size: 12px;
            margin-right: 10px;
        }
        .type-vmess { background: #e3f2fd; color: #1976d2; }
        .type-vless { background: #f3e5f5; color: #7b1fa2; }
        .type-shadowsocks { background: #e8f5e9; color: #388e3c; }
        .type-trojan { background: #fff3e0; color: #f57c00; }
        .selected { background: #e3f2fd !important; border-left: 4px solid #007bff; }
        .loading {
            text-align: center;
            padding: 40px;
            color: #666;
        }
        .message {
            position: fixed;
            top: 20px;
            right: 20px;
            padding: 15px 25px;
            border-radius: 5px;
            color: white;
            z-index: 1000;
            display: none;
        }
        .msg-success { background: #28a745; }
        .msg-error { background: #dc3545; }
    </style>
</head>
<body>
    <div class="container">
        <h1>Xray Client Web UI</h1>

        <div class="status-bar">
            <div>
                <strong>服务状态:</strong>
                <span class="status-badge status-{{ 'active' if status == 'active' else 'inactive' }}">
                    {{ '运行中' if status == 'active' else '已停止' }}
                </span>
                <span style="margin-left: 20px; color: #666;">
                    节点数: {{ count }} | 更新时间: {{ update_time }}
                </span>
            </div>
            <div class="controls">
                <button class="btn-primary" onclick="updateSub()">更新订阅</button>
                <button class="btn-success" onclick="restartService()">重启服务</button>
            </div>
        </div>

        <div class="node-list">
            {% for node in nodes %}
            <div class="node-item" data-index="{{ loop.index0 }}">
                <div class="node-info">
                    <div class="node-name">
                        <span class="node-type type-{{ node.type }}">{{ node.type }}</span>
                        {{ node.name }}
                    </div>
                    <div class="node-meta">
                        {{ node.server }}:{{ node.port }} | 来源: {{ node.subscription or 'default' }}
                    </div>
                </div>
                <button class="btn-primary" onclick="selectNode({{ loop.index0 }})">
                    选择
                </button>
            </div>
            {% else %}
            <div class="loading">
                暂无节点数据，请先更新订阅
            </div>
            {% endfor %}
        </div>
    </div>

    <div id="message" class="message"></div>

    <script>
        function showMessage(text, isError = false) {
            const msg = document.getElementById('message');
            msg.textContent = text;
            msg.className = 'message ' + (isError ? 'msg-error' : 'msg-success');
            msg.style.display = 'block';
            setTimeout(() => msg.style.display = 'none', 3000);
        }

        async function selectNode(index) {
            try {
                const res = await fetch('/api/select', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ index })
                });
                const data = await res.json();
                if (data.success) {
                    showMessage('节点切换成功');
                    document.querySelectorAll('.node-item').forEach(el => el.classList.remove('selected'));
                    document.querySelector(`[data-index="${index}"]`).classList.add('selected');
                } else {
                    showMessage('切换失败: ' + data.error, true);
                }
            } catch (e) {
                showMessage('请求失败', true);
            }
        }

        async function updateSub() {
            showMessage('正在更新订阅...');
            try {
                const res = await fetch('/api/update', { method: 'POST' });
                const data = await res.json();
                if (data.success) {
                    showMessage('订阅更新成功');
                    setTimeout(() => location.reload(), 1000);
                } else {
                    showMessage('更新失败: ' + data.error, true);
                }
            } catch (e) {
                showMessage('请求失败', true);
            }
        }

        async function restartService() {
            showMessage('正在重启服务...');
            try {
                const res = await fetch('/api/restart', { method: 'POST' });
                const data = await res.json();
                if (data.success) {
                    showMessage('服务重启成功');
                } else {
                    showMessage('重启失败: ' + data.error, true);
                }
            } catch (e) {
                showMessage('请求失败', true);
            }
        }

        // 定时刷新状态
        setInterval(async () => {
            try {
                const res = await fetch('/api/status');
                const data = await res.json();
                const badge = document.querySelector('.status-badge');
                if (badge) {
                    badge.className = 'status-badge status-' + (data.status === 'active' ? 'active' : 'inactive');
                    badge.textContent = data.status === 'active' ? '运行中' : '已停止';
                }
            } catch (e) {}
        }, 5000);
    </script>
</body>
</html>
'''

if __name__ == '__main__':
    port = int(os.environ.get('WEB_UI_PORT', 5000))
    bind = os.environ.get('WEB_UI_BIND', '127.0.0.1')
    if AUTH_TOKEN:
        print(f"Auth enabled. Use ?token=<TOKEN> or X-Auth-Token header.")
    print(f"Starting Xray Client Web UI on http://{bind}:{port}")
    app.run(host=bind, port=port, debug=False)
