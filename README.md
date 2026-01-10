# GPU Grab

**GPU Training Task Scheduler**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)

一个基于 Python 的 GPU 训练任务调度系统，专为管理和优化深度学习训练任务而设计。它能够监控 GPU 资源，并根据显存和利用率智能调度任务。

## ✨ 核心特性

- **🚀 自动调度**: 只有当 GPU 资源满足要求（显存、利用率）时才启动任务。
- **📊 状态监控**: 实时监控 GPU 显存、利用率和温度。
- **📋 任务队列**: 支持优先级队列，确保高优先级任务优先执行。
- **🔄 持久化**: 任务队列使用 JSON 文件持久化，服务重启不丢失。
- **💻 CLI 工具**: 方便的命令行界面，用于提交、管理和查看任务。
- **🔌 Socket 通信**: 使用 Unix Socket 进行高效的进程间通信。
- **⚙️ Systemd 集成**: 作为用户级服务后台运行，开机自启。
- **🔥 热重载配置**: 无需重启服务即可更新配置参数。

## 🛠️ 安装

本项目使用 [uv](https://github.com/astral-sh/uv) 进行依赖管理（也可以使用 pip）。

### 方式 1: 使用 uv (推荐)

```bash
# 初始化环境并安装依赖
uv sync
```

### 方式 2: 使用 pip

```bash
pip install .
```

## 🚀 快速开始

### 1. 启动服务

首次安装后，需要配置并启动 Systemd 服务：

```bash
# 重新加载配置
systemctl --user daemon-reload

# 启用并启动服务
systemctl --user enable gpu-grab.service
systemctl --user start gpu-grab.service

# 查看服务状态
systemctl --user status gpu-grab.service
```

### 2. 配置 PATH（可选）

如果直接运行 `gpu-grab` 命令提示 `command not found`，需要将虚拟环境添加到 PATH：

```bash
# Zsh 用户
echo 'export PATH="/home/ubuntu/.gpu-grab/.venv/bin:$PATH"' >> ~/.zshrc
source ~/.zshrc

# Bash 用户
echo 'export PATH="/home/ubuntu/.gpu-grab/.venv/bin:$PATH"' >> ~/.bashrc
source ~/.bashrc
```

或者使用 `uv run gpu-grab` 代替直接调用。

### 3. 提交任务

提交一个简单的 Python 训练脚本：

```bash
# 使用 uv 运行
uv run gpu-grab submit "python train.py"

# 或者如果已配置 PATH
gpu-grab submit "python train.py"
```

指定 GPU 资源需求：

```bash
# 需要 2 个 GPU，每个至少 20GB 空闲显存，当前利用率低于 10%
gpu-grab submit "python train.py" \
  --name "resnet-training" \
  --gpu-count 2 \
  --memory 20 \
  --util-margin 90 \
  --gpus 0,1
```

### 指定 Conda 环境

如果任务依赖特定的 Conda 环境，请使用 `conda run` 运行：

```bash
# 在 pytorch-test 环境中运行
gpu-grab submit "conda run -n pytorch-test python train.py"
```

或者使用 Python 解释器的绝对路径：

```bash
gpu-grab submit "/path/to/envs/pytorch-test/bin/python train.py"
```

### 4. 查看状态

查看 GPU 实时状态和任务队列：

```bash
gpu-grab status
```

输出示例：
```
=== GPU Status ===
  GPU 0: NVIDIA L20
    Memory: 1082/46068 MB (44985 MB free)
    Utilization: 0%
    Temperature: 42°C
...

=== Task Statistics ===
  Pending:   1
  Running:   1
  Completed: 5
  Failed:    0
```

### 5. 管理任务

```bash
# 列出所有任务
gpu-grab list

# 查看特定任务日志
gpu-grab logs <task_id>

# 取消任务
gpu-grab cancel <task_id>
```

## 📖 详细文档

### CLI 命令详解

| 命令 | 说明 | 示例 |
|------|------|------|
| `submit` | 提交新任务 | `gpu-grab submit "cmd"` |
| `status` | 查看 GPU 和服务状态 | `gpu-grab status` |
| `list` | 列出任务 | `gpu-grab list -s running` |
| `cancel` | 取消任务 | `gpu-grab cancel ab12c` |
| `logs` | 查看任务日志 | `gpu-grab logs ab12c -t 50` |
| `clean` | 清理已完成任务 | `gpu-grab clean` |
| `reload` | 热重载配置 | `gpu-grab reload` |

### 提交参数 (`submit`)

- `-n, --name`: 任务名称
- `-w, --workdir`: 工作目录（默认当前目录）
- `-g, --gpus`: 指定 GPU ID 列表 (如 `0,1`)
- `-c, --gpu-count`: 需要的 GPU 数量 (默认 1)
- `-m, --memory`: 最小空闲显存 (GB)
- `-u, --util-margin`: 最小空闲利用率百分比 (如 20 表示利用率需 <= 80%)
- `-p, --priority`: 优先级 (数字越大越优先)
- `-e, --env`: 环境变量 (`KEY=VALUE`)

### 配置文件

默认配置文件位于 `~/.gpu-grab/config.yaml`：

```yaml
check_interval: 10.0          # 调度检查间隔(秒)
max_concurrent_tasks: 4       # 最大并发任务数
log_level: INFO
default_gpu_count: 1
```

### 热重载配置

修改 `config.yaml` 后，无需重启服务即可应用配置变更：

```bash
# 方式一：使用 CLI 命令
gpu-grab reload

# 方式二：发送 SIGHUP 信号
kill -HUP $(pgrep -f "python -m gpu_grab")

# 方式三：使用 systemctl
systemctl --user reload gpu-grab
```

**可热重载的配置项**：
- `check_interval` - 调度检查间隔
- `max_concurrent_tasks` - 最大并发任务数
- `log_level` - 日志级别
- `default_gpu_count` - 默认 GPU 数量
- `default_min_memory_gb` - 默认最小显存需求
- `default_max_util_percent` - 默认最大利用率阈值

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

### 开发环境设置

```bash
# 克隆仓库
git clone https://github.com/hjnnjh/gpu-grab.git
cd gpu-grab

# 安装依赖
uv sync

# 运行本地开发服务
uv run python -m gpu_grab
```

## 📄 License

MIT License
