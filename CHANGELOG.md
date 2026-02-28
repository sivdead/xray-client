# Changelog

All notable changes to this project will be documented in this file.

## [Unreleased]

## [v0.5.0] - 2025-01-01

### Fixed
- 兼容 PEP 668，`install.sh` 安装 pyyaml 失败时重试 `--break-system-packages`
- 将 `yaml` 改为懒加载，修复非 sudo 模式下的 `ImportError`

## [v0.4.0] - 2025-01-01

### Added
- TUI 实时监控文件变化和服务状态，自动刷新界面

### Changed
- 将 Web UI 替换为 curses TUI 终端管理界面

### Fixed
- 修复 CodeRabbit 第二轮 review 的 5 个问题
- 在 README 顶部添加中英文切换链接
- 修复 CodeRabbit review 提出的 7 个问题

## [v0.3.0] - 2025-01-01

### Added
- `no_proxy` 支持从 `config.ini` 读取配置
- 新增 `proxy-on` / `proxy-off` 和 `tun-on` / `tun-off` 四个子命令

### Fixed
- 修复 CodeRabbit 审查的 4 个问题
- 修复 Ruff F541（f-string 无占位符），更新 README

### Chores
- 在 `.gitignore` 中忽略 Python 缓存文件

## [v0.2.0] - 2025-01-01

### Added
- 支持 `workflow_dispatch` 手动触发 Release
- CI 流水线中增加 PyInstaller 构建验证
- 使用 PyInstaller 将项目打包为独立可执行文件（`xray-client`、`xray-tui`）

### Fixed
- 修复 CodeRabbit 第二轮 review 问题
- 修复 CodeRabbit review 初轮问题

## [v0.1.0] - 2025-01-01

### Added
- 初始版本：支持 JustMySocks 的 Xray Client
- 新增英文 README，保留中文版为 `README_CN.md`
- 8 项新功能（见初始提交）

### Security
- 通过 `shutil.which()` 将 subprocess 命令解析为绝对路径
- 修复 CodeRabbit 安全审查问题

### Fixed
- 修复 `install.sh` 中的 shellcheck SC2155 警告
- 修复多个 bug，提升项目整体质量

### Refactored
- 切换到 ruff 进行代码检查和格式化
- 修复所有 flake8 lint 错误以通过 CI
