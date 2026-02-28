#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Xray Client TUI - 终端交互管理界面
基于 curses，无需额外依赖
"""

import curses
import json
import locale
import os
import subprocess
import shutil
import threading
import time

# 路径配置
CLIENT_CONFIG_DIR = "/etc/xray-client"
SUBSCRIPTION_FILE = os.path.join(CLIENT_CONFIG_DIR, "subscription", "nodes.json")
INI_FILE = os.path.join(CLIENT_CONFIG_DIR, "config.ini")

# 确保 locale 正确（支持中文）
locale.setlocale(locale.LC_ALL, "")


def _resolve_executable(name):
    """通过 shutil.which() 安全解析可执行文件路径"""
    path = shutil.which(name)
    if path is None:
        raise FileNotFoundError(f"找不到命令: {name}")
    return path


def load_nodes():
    """加载节点数据"""
    if os.path.exists(SUBSCRIPTION_FILE):
        with open(SUBSCRIPTION_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"nodes": [], "update_time": "从未"}


def get_xray_status():
    """获取 Xray 服务状态"""
    try:
        result = subprocess.run(
            [_resolve_executable("systemctl"), "is-active", "xray"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True,
            timeout=5,
        )
        return result.stdout.strip()
    except Exception:
        return "unknown"


def get_selected_node():
    """从配置文件读取当前选中节点索引"""
    try:
        from configparser import ConfigParser

        config = ConfigParser()
        config.read(INI_FILE, encoding="utf-8")
        return config.getint("node", "selected", fallback=0)
    except Exception:
        return 0


def run_xray_client(args, timeout=120):
    """运行 xray-client 命令并捕获输出"""
    try:
        cmd = [_resolve_executable("xray-client")] + args
        result = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True,
            timeout=timeout,
        )
        output = result.stdout + result.stderr
        return result.returncode == 0, output.strip()
    except FileNotFoundError:
        return False, "找不到 xray-client 命令"
    except subprocess.TimeoutExpired:
        return False, "命令执行超时"
    except Exception as e:
        return False, str(e)


class TUI:
    """Xray Client 终端管理界面"""

    # 颜色对定义
    PAIR_NORMAL = 1
    PAIR_HEADER = 2
    PAIR_STATUS_OK = 3
    PAIR_STATUS_ERR = 4
    PAIR_SELECTED = 5
    PAIR_HIGHLIGHT = 6
    PAIR_HELP = 7
    PAIR_TYPE_VMESS = 8
    PAIR_TYPE_VLESS = 9
    PAIR_TYPE_SS = 10
    PAIR_TYPE_TROJAN = 11
    PAIR_MSG_OK = 12
    PAIR_MSG_ERR = 13

    def __init__(self, stdscr):
        self.stdscr = stdscr
        self.nodes = []
        self.update_time = "从未"
        self.status = "unknown"
        self.selected = 0  # 当前选中节点（配置里的）
        self.cursor = 0  # 光标所在行
        self.scroll_offset = 0  # 滚动偏移

        self.message = ""  # 底部消息
        self.message_time = 0  # 消息显示时间
        self.message_is_error = False

        self.running = True
        self.busy = False  # 是否正在执行操作
        self.busy_text = ""

        self._setup_colors()
        self._refresh_data()

        # 启动后台状态刷新线程
        self._status_thread = threading.Thread(target=self._status_loop, daemon=True)
        self._status_thread.start()

    def _setup_colors(self):
        """初始化颜色方案"""
        curses.start_color()
        curses.use_default_colors()
        curses.init_pair(self.PAIR_NORMAL, -1, -1)
        curses.init_pair(self.PAIR_HEADER, curses.COLOR_WHITE, curses.COLOR_BLUE)
        curses.init_pair(self.PAIR_STATUS_OK, curses.COLOR_GREEN, -1)
        curses.init_pair(self.PAIR_STATUS_ERR, curses.COLOR_RED, -1)
        curses.init_pair(self.PAIR_SELECTED, curses.COLOR_CYAN, -1)
        curses.init_pair(self.PAIR_HIGHLIGHT, curses.COLOR_BLACK, curses.COLOR_CYAN)
        curses.init_pair(self.PAIR_HELP, curses.COLOR_YELLOW, -1)
        curses.init_pair(self.PAIR_TYPE_VMESS, curses.COLOR_BLUE, -1)
        curses.init_pair(self.PAIR_TYPE_VLESS, curses.COLOR_MAGENTA, -1)
        curses.init_pair(self.PAIR_TYPE_SS, curses.COLOR_GREEN, -1)
        curses.init_pair(self.PAIR_TYPE_TROJAN, curses.COLOR_YELLOW, -1)
        curses.init_pair(self.PAIR_MSG_OK, curses.COLOR_GREEN, -1)
        curses.init_pair(self.PAIR_MSG_ERR, curses.COLOR_RED, -1)

    def _refresh_data(self):
        """刷新节点数据和状态"""
        data = load_nodes()
        self.nodes = data.get("nodes", [])
        self.update_time = data.get("update_time", "从未")
        self.status = get_xray_status()
        self.selected = get_selected_node()

        # 修正光标范围
        if self.nodes:
            if self.cursor >= len(self.nodes):
                self.cursor = len(self.nodes) - 1
        else:
            self.cursor = 0

    def _status_loop(self):
        """后台定时刷新状态"""
        while self.running:
            time.sleep(5)
            if not self.busy:
                self.status = get_xray_status()

    def _show_message(self, text, is_error=False):
        """设置底部消息"""
        self.message = text
        self.message_time = time.time()
        self.message_is_error = is_error

    def _type_color(self, node_type):
        """根据协议类型返回颜色"""
        t = node_type.lower()
        if t == "vmess":
            return self.PAIR_TYPE_VMESS
        elif t == "vless":
            return self.PAIR_TYPE_VLESS
        elif t == "shadowsocks":
            return self.PAIR_TYPE_SS
        elif t == "trojan":
            return self.PAIR_TYPE_TROJAN
        return self.PAIR_NORMAL

    def _run_async(self, description, func):
        """在后台线程中执行操作"""
        if self.busy:
            return

        self.busy = True
        self.busy_text = description

        def wrapper():
            try:
                func()
            finally:
                self.busy = False
                self.busy_text = ""

        t = threading.Thread(target=wrapper, daemon=True)
        t.start()

    def _do_select(self):
        """选择当前光标所在节点"""
        if not self.nodes:
            return
        index = self.cursor

        def task():
            self._show_message(f"正在切换到节点 [{index}]...")
            ok, output = run_xray_client(["select", "-i", str(index)])
            if ok:
                run_xray_client(["restart"])
                self._refresh_data()
                self._show_message(f"已切换到节点 [{index}]")
            else:
                self._show_message(f"切换失败: {output}", is_error=True)

        self._run_async("切换节点", task)

    def _do_update(self):
        """更新订阅"""

        def task():
            self._show_message("正在更新订阅...")
            ok, output = run_xray_client(["update"])
            if ok:
                run_xray_client(["restart"])
                self._refresh_data()
                self._show_message("订阅更新成功")
            else:
                self._show_message(f"更新失败: {output}", is_error=True)

        self._run_async("更新订阅", task)

    def _do_restart(self):
        """重启服务"""

        def task():
            self._show_message("正在重启服务...")
            ok, output = run_xray_client(["restart"])
            if ok:
                time.sleep(1)
                self.status = get_xray_status()
                self._show_message("服务已重启")
            else:
                self._show_message(f"重启失败: {output}", is_error=True)

        self._run_async("重启服务", task)

    def _do_test(self):
        """测试节点延迟"""

        def task():
            self._show_message("正在测试节点延迟（可能需要较长时间）...")
            ok, output = run_xray_client(["test"], timeout=300)
            if ok:
                self._show_message("测试完成，查看终端输出了解详情")
            else:
                self._show_message(f"测试失败: {output}", is_error=True)

        self._run_async("测试节点", task)

    def _do_auto_select(self):
        """自动选择最佳节点"""

        def task():
            self._show_message("正在自动选择最佳节点...")
            ok, output = run_xray_client(["auto-select"], timeout=300)
            if ok:
                self._refresh_data()
                self._show_message("已自动选择最佳节点")
            else:
                self._show_message(f"自动选择失败: {output}", is_error=True)

        self._run_async("自动选择", task)

    def _do_ping(self):
        """测试代理连接"""

        def task():
            self._show_message("正在测试代理连接...")
            ok, output = run_xray_client(["ping"])
            if ok:
                self._show_message(f"连接测试: {output}")
            else:
                self._show_message(f"连接失败: {output}", is_error=True)

        self._run_async("测试连接", task)

    def _safe_addstr(self, y, x, text, attr=0, max_width=None):
        """安全输出字符串，避免超出窗口边界"""
        h, w = self.stdscr.getmaxyx()
        if y < 0 or y >= h or x >= w:
            return
        if max_width is None:
            max_width = w - x
        if max_width <= 0:
            return
        # 截断文本
        display = text[:max_width]
        try:
            self.stdscr.addnstr(y, x, display, max_width, attr)
        except curses.error:
            pass  # 忽略写入最后一个字符的错误

    def draw(self):
        """绘制完整界面"""
        self.stdscr.erase()
        h, w = self.stdscr.getmaxyx()

        if h < 10 or w < 40:
            self._safe_addstr(0, 0, "终端太小，请调整窗口大小")
            self.stdscr.refresh()
            return

        # ── 标题栏 ──
        title = " Xray Client TUI "
        title_line = title.center(w)
        self._safe_addstr(0, 0, title_line, curses.color_pair(self.PAIR_HEADER) | curses.A_BOLD)

        # ── 状态栏 ──
        y = 1
        if self.status == "active":
            status_text = "● 运行中"
            status_color = curses.color_pair(self.PAIR_STATUS_OK) | curses.A_BOLD
        else:
            status_text = "○ 已停止"
            status_color = curses.color_pair(self.PAIR_STATUS_ERR) | curses.A_BOLD

        self._safe_addstr(y, 1, "状态: ", curses.A_BOLD)
        self._safe_addstr(y, 8, status_text, status_color)

        info = f"节点: {len(self.nodes)}  更新: {self.update_time}"
        info_x = w - len(info) - 2
        if info_x > 20:
            self._safe_addstr(y, info_x, info, curses.color_pair(self.PAIR_NORMAL))

        # ── 分隔线 ──
        y = 2
        self._safe_addstr(y, 0, "─" * w, curses.color_pair(self.PAIR_NORMAL))

        # ── 节点列表 ──
        list_top = 3
        # 底部留 3 行: 分隔线 + 帮助 + 消息
        list_bottom = h - 3
        visible_count = list_bottom - list_top

        if visible_count <= 0:
            self.stdscr.refresh()
            return

        if not self.nodes:
            self._safe_addstr(list_top + 1, 2, "暂无节点数据，按 u 更新订阅", curses.color_pair(self.PAIR_HELP))
        else:
            # 确保光标在可见范围
            if self.cursor < self.scroll_offset:
                self.scroll_offset = self.cursor
            elif self.cursor >= self.scroll_offset + visible_count:
                self.scroll_offset = self.cursor - visible_count + 1

            # 列头
            col_header = f"  {'#':<5}{'类型':<13}{'名称':<35}{'服务器'}"
            self._safe_addstr(list_top, 0, col_header[:w], curses.A_BOLD | curses.A_UNDERLINE)

            for i in range(visible_count):
                idx = self.scroll_offset + i
                if idx >= len(self.nodes):
                    break

                node = self.nodes[idx]
                row_y = list_top + 1 + i

                is_cursor = idx == self.cursor
                is_selected = idx == self.selected

                # 标记符号
                marker = "▸ " if is_cursor else "  "
                if is_selected:
                    marker = "★ " if is_cursor else "★ "

                # 截断名称和服务器
                name = node.get("name", "")
                if len(name) > 32:
                    name = name[:30] + ".."
                server = f"{node.get('server', '')}:{node.get('port', '')}"
                if len(server) > 22:
                    server = server[:20] + ".."
                ntype = node.get("type", "unknown")

                # 行底色
                if is_cursor:
                    line_attr = curses.color_pair(self.PAIR_HIGHLIGHT) | curses.A_BOLD
                    # 填充整行背景
                    self._safe_addstr(row_y, 0, " " * w, line_attr)
                elif is_selected:
                    line_attr = curses.color_pair(self.PAIR_SELECTED) | curses.A_BOLD
                else:
                    line_attr = curses.color_pair(self.PAIR_NORMAL)

                # 输出标记
                self._safe_addstr(row_y, 0, marker, line_attr)

                # 索引
                self._safe_addstr(row_y, 2, f"{idx:<5}", line_attr)

                # 协议类型 (带颜色)
                type_attr = curses.color_pair(self._type_color(ntype))
                if is_cursor:
                    type_attr = line_attr  # 光标行覆盖颜色
                self._safe_addstr(row_y, 7, f"{ntype:<13}", type_attr)

                # 名称
                self._safe_addstr(row_y, 20, f"{name:<35}", line_attr)

                # 服务器
                self._safe_addstr(row_y, 55, server, line_attr)

        # ── 底部分隔线 ──
        sep_y = h - 3
        self._safe_addstr(sep_y, 0, "─" * w, curses.color_pair(self.PAIR_NORMAL))

        # ── 帮助栏 ──
        help_y = h - 2
        help_attr = curses.color_pair(self.PAIR_HELP)
        if self.busy:
            help_text = f"  ⟳ {self.busy_text}..."
            self._safe_addstr(help_y, 0, help_text, help_attr | curses.A_BOLD)
        else:
            helps = [
                "↑↓:移动",
                "Enter:选择",
                "u:更新",
                "r:重启",
                "t:测速",
                "a:自动选",
                "p:测连接",
                "q:退出",
            ]
            help_text = "  " + "  │  ".join(helps)
            self._safe_addstr(help_y, 0, help_text, help_attr)

        # ── 消息栏 ──
        msg_y = h - 1
        if self.message and (time.time() - self.message_time < 5):
            msg_attr = curses.color_pair(self.PAIR_MSG_ERR if self.message_is_error else self.PAIR_MSG_OK)
            self._safe_addstr(msg_y, 1, self.message, msg_attr | curses.A_BOLD)

        self.stdscr.refresh()

    def handle_input(self, key):
        """处理键盘输入"""
        if key == ord("q") or key == ord("Q"):
            self.running = False

        elif key == curses.KEY_UP or key == ord("k"):
            if self.cursor > 0:
                self.cursor -= 1

        elif key == curses.KEY_DOWN or key == ord("j"):
            if self.cursor < len(self.nodes) - 1:
                self.cursor += 1

        elif key == curses.KEY_HOME or key == ord("g"):
            self.cursor = 0

        elif key == curses.KEY_END or key == ord("G"):
            if self.nodes:
                self.cursor = len(self.nodes) - 1

        elif key == curses.KEY_PPAGE:  # Page Up
            visible = self.stdscr.getmaxyx()[0] - 6
            self.cursor = max(0, self.cursor - visible)

        elif key == curses.KEY_NPAGE:  # Page Down
            visible = self.stdscr.getmaxyx()[0] - 6
            if self.nodes:
                self.cursor = min(len(self.nodes) - 1, self.cursor + visible)

        elif key in (curses.KEY_ENTER, 10, 13):
            self._do_select()

        elif key == ord("u") or key == ord("U"):
            self._do_update()

        elif key == ord("r") or key == ord("R"):
            self._do_restart()

        elif key == ord("t") or key == ord("T"):
            self._do_test()

        elif key == ord("a") or key == ord("A"):
            self._do_auto_select()

        elif key == ord("p") or key == ord("P"):
            self._do_ping()

        elif key == ord("l") or key == ord("L") or key == curses.KEY_F5:
            # 手动刷新
            self._refresh_data()
            self._show_message("已刷新数据")

    def run(self):
        """主循环"""
        self.stdscr.nodelay(True)
        curses.curs_set(0)  # 隐藏光标

        while self.running:
            self.draw()
            try:
                key = self.stdscr.getch()
                if key != -1:
                    self.handle_input(key)
            except KeyboardInterrupt:
                self.running = False
            time.sleep(0.05)  # ~20fps


def main():
    """入口"""

    def _run(stdscr):
        tui = TUI(stdscr)
        tui.run()

    try:
        curses.wrapper(_run)
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
