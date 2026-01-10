# gpu-grab

> AI 辅助开发上下文文档 | 初始化于 2025-12-09

---

## 变更记录 (Changelog)

| 日期 | 版本 | 变更内容 |
|------|------|----------|
| 2026-01-10 17:00 | v1.2.0 | 增量扫描：新增配置热重载功能（`reload` 命令、SIGHUP 信号处理、`RELOADABLE_KEYS`） |
| 2025-12-17 01:27 | v1.1.0 | 增量扫描：发现 `__main__.py` 服务入口、`clean` 命令、新增工具脚本 |
| 2025-12-09 17:27 | v1.0.0 | 完整扫描：识别 Python GPU 任务调度器架构，8 个核心模块，完整 CLI 接口 |
| 2025-12-09 16:43 | v0.0.1 | 增量扫描确认：项目仍为空仓库，等待源代码添加 |
| 2025-12-09 16:41 | v0.0.0 | 初始化项目 AI 上下文文档（空仓库模板） |

---

## 项目愿景

**GPU Training Task Scheduler** - 一个基于 Python 的 GPU 训练任务调度系统，支持：

- 自动监控 GPU 资源状态（显存、利用率、温度）
- 智能任务队列管理与优先级调度
- 基于资源需求的自动 GPU 分配
- 命令行界面 (CLI) 进行任务提交与管理
- Unix Socket 通信实现客户端-服务端架构
- **配置热重载**（无需重启服务即可更新配置）

---

## 架构总览

```
.gpu-grab/
  pyproject.toml         # 项目配置与依赖
  config.yaml            # 运行时配置文件
  ruff.toml              # 代码检查配置
  main.py                # 简单入口（开发用）
  test_task.py           # 测试任务脚本
  check_env.py           # 环境检查脚本
  .python-version        # Python 3.13
  .gitignore             # Git 忽略规则
  gpu_grab/              # 核心包
    __init__.py          # 版本定义
    __main__.py          # 服务端入口 (python -m gpu_grab)
    config.py            # 配置管理（含热重载）
    models.py            # 数据模型（Task, GPUStatus, GPURequirement）
    gpu_monitor.py       # GPU 监控（NVML 接口）
    queue_manager.py     # 任务队列持久化
    task_runner.py       # 进程执行管理
    scheduler.py         # 核心调度器（含配置重载）
    server.py            # Unix Socket 服务端
    cli.py               # 命令行接口（含 reload 命令）
```

**技术栈**:
- **语言**: Python 3.13+（兼容 3.10+）
- **GPU 接口**: pynvml (NVIDIA Management Library)
- **配置格式**: YAML
- **通信协议**: Unix Socket + JSON
- **构建系统**: Hatchling
- **代码检查**: Ruff

**核心依赖**:
- `pynvml>=13.0.1` - NVIDIA GPU 监控
- `pyyaml>=6.0.3` - 配置文件解析

---

## 模块结构图

```mermaid
graph TD
    A["(根) gpu-grab"] --> B["gpu_grab/"]
    B --> K["__main__.py<br/>服务入口"]
    B --> C["config.py<br/>配置管理"]
    B --> D["models.py<br/>数据模型"]
    B --> E["gpu_monitor.py<br/>GPU 监控"]
    B --> F["queue_manager.py<br/>队列管理"]
    B --> G["task_runner.py<br/>任务执行"]
    B --> H["scheduler.py<br/>核心调度"]
    B --> I["server.py<br/>Socket 服务"]
    B --> J["cli.py<br/>命令行"]

    K --> H
    K --> I
    K --> C
    K -.->|SIGHUP| H
    H --> E
    H --> F
    H --> G
    H --> C
    I --> H
    J -.->|Socket| I
    G --> D
    F --> D
    E --> D

    style A fill:#e1f5fe
    style K fill:#ffccbc
    style H fill:#c8e6c9
    style J fill:#fff9c4
    style C fill:#f3e5f5

    click B "./gpu_grab/CLAUDE.md" "查看 gpu_grab 模块文档"
```

---

## 模块索引

| 模块路径 | 职责 | 核心类/函数 | 依赖 |
|----------|------|-------------|------|
| `gpu_grab/__main__.py` | 服务端入口，请求处理，信号处理 | `main()`, `setup_logging()`, `sighup_handler()` | config, scheduler, server, models |
| `gpu_grab/config.py` | 系统配置管理，YAML 加载/保存/热重载 | `Config`, `RELOADABLE_KEYS`, `reload()` | pyyaml |
| `gpu_grab/models.py` | 数据模型定义 | `Task`, `TaskStatus`, `GPUStatus`, `GPURequirement` | - |
| `gpu_grab/gpu_monitor.py` | GPU 状态监控 | `GPUMonitor` | pynvml |
| `gpu_grab/queue_manager.py` | 任务队列持久化（JSON） | `QueueManager` | models |
| `gpu_grab/task_runner.py` | 子进程生命周期管理 | `TaskRunner` | models |
| `gpu_grab/scheduler.py` | 主调度循环，配置重载 | `Scheduler`, `reload_config()` | config, gpu_monitor, queue_manager, task_runner |
| `gpu_grab/server.py` | Unix Socket 服务端 | `UnixSocketServer` | - |
| `gpu_grab/cli.py` | 命令行工具入口 | `main()`, `cmd_*`, `cmd_reload()` | - |

---

## 运行与开发

### 环境要求

- Python 3.10+（推荐 3.13）
- NVIDIA GPU + 驱动
- Linux 系统（Unix Socket 依赖）

### 快速启动

```bash
# 安装依赖
cd ~/.gpu-grab
pip install -e .

# 启动服务端
python -m gpu_grab

# 或者在另一个终端运行 CLI
gpu-grab status
gpu-grab submit "python train.py" --name my-training --gpu-count 2
gpu-grab list
gpu-grab logs <task_id>
gpu-grab clean   # 清理已完成任务
gpu-grab reload  # 热重载配置
```

### 常用命令

| 命令 | 描述 |
|------|------|
| `gpu-grab submit <cmd>` | 提交训练任务 |
| `gpu-grab status` | 查看系统状态（GPU + 队列） |
| `gpu-grab list [-s STATUS]` | 列出任务 |
| `gpu-grab cancel <id>` | 取消任务 |
| `gpu-grab logs <id> [-t N]` | 查看任务日志 |
| `gpu-grab clean [-s STATUS]` | 清理已完成任务 |
| `gpu-grab reload` | **热重载配置**（v1.2.0 新增） |

### CLI 参数详解

```bash
gpu-grab submit "python train.py" \
  -n "训练任务名"       # --name
  -w /path/to/dir      # --workdir 工作目录
  -g 0,1               # --gpus 指定 GPU
  -c 2                 # --gpu-count 所需 GPU 数量
  -m 8.0               # --memory 最小空闲显存 (GB)
  -u 20                # --util-margin 利用率余量 (%)
  -p 10                # --priority 优先级
  -e KEY=VALUE         # --env 环境变量
```

### 配置热重载

v1.2.0 新增配置热重载功能，支持两种方式：

**方式一：CLI 命令**
```bash
gpu-grab reload
```

**方式二：发送 SIGHUP 信号**
```bash
kill -HUP <服务进程PID>
```

**可热重载的配置项**：
| 配置项 | 说明 |
|--------|------|
| `check_interval` | GPU 检查间隔（秒） |
| `max_concurrent_tasks` | 最大并发任务数 |
| `log_level` | 日志级别 |
| `default_gpu_count` | 默认 GPU 数量 |
| `default_min_memory_gb` | 默认最小显存需求 |
| `default_max_util_percent` | 默认最大利用率阈值 |

---

## 数据模型

### TaskStatus (枚举)

| 状态 | 说明 |
|------|------|
| `PENDING` | 等待调度 |
| `RUNNING` | 正在运行 |
| `COMPLETED` | 成功完成 |
| `FAILED` | 执行失败 |
| `CANCELLED` | 已取消 |

### GPURequirement

| 字段 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `gpu_ids` | `list[int]` | None | 指定 GPU，None 表示任意 |
| `min_free_memory_gb` | `float` | 0.0 | 最小空闲显存 |
| `max_util_percent` | `float` | 100.0 | 最大利用率阈值 |
| `gpu_count` | `int` | 1 | 所需 GPU 数量 |

### Task

核心任务实体，包含命令、工作目录、环境变量、资源需求、状态、时间戳、分配的 GPU 等。

### Config (含热重载)

| 配置 | 类型 | 默认值 | 可热重载 |
|------|------|--------|----------|
| `check_interval` | float | 10.0 | Yes |
| `max_concurrent_tasks` | int | 4 | Yes |
| `log_level` | str | "INFO" | Yes |
| `log_max_size_mb` | int | 10 | No |
| `log_backup_count` | int | 5 | No |
| `default_gpu_count` | int | 1 | Yes |
| `default_min_memory_gb` | float | 0.0 | Yes |
| `default_max_util_percent` | float | 100.0 | Yes |

---

## 测试策略

- 当前无正式测试目录（`tests/`）
- 存在工具脚本：`test_task.py`（简单任务模拟）、`check_env.py`（环境检查）
- 建议添加 `tests/` 目录，使用 pytest
- 重点测试：
  - `QueueManager` 持久化逻辑
  - `GPUMonitor.check_requirements()` 资源匹配
  - `Scheduler._schedule_pending_tasks()` 调度决策
  - `Config.reload()` 配置热重载逻辑
  - `Scheduler.reload_config()` 调度器配置更新

---

## 编码规范

- 使用 dataclass 定义数据模型
- 类型注解完整（Python 3.10+ 语法）
- 日志使用 `logging` 模块
- 文件锁保护并发访问（`fcntl`）
- 代码检查使用 Ruff（配置见 `ruff.toml`）

---

## AI 使用指引

### 适合 AI 协助的任务

- 添加新的 CLI 子命令
- 添加任务依赖/DAG 调度
- 实现 REST API 接口（替代/补充 Unix Socket）
- 编写单元测试
- 添加 systemd 服务单元文件
- 扩展热重载支持的配置项

### 上下文提示

与 AI 协作时，建议提供：
1. 当前需要修改的模块路径
2. 期望的输入/输出行为
3. 是否需要保持向后兼容

### 当前待完善功能

1. **CLI serve 子命令** - 可添加 `gpu-grab serve` 包装 `__main__.py`
2. **日志跟踪 (follow)** - `cmd_logs` 中 `-f` 参数标记为 TODO
3. **配置文件管理** - 可添加 `gpu-grab config` 命令
4. **任务依赖** - 当前无任务间依赖支持
5. **日志级别动态更新** - 热重载 `log_level` 后需更新 logger

---

## 覆盖率报告

| 指标 | 数值 |
|------|------|
| 估算总文件数 | 16（不含 .git/.venv/文档） |
| 已扫描文件数 | 16 |
| 覆盖率 | 100% |
| 识别模块数 | 1（gpu_grab 包） |
| 核心源文件 | 10 |

### 文件清单

| 类别 | 文件 |
|------|------|
| 配置 | `pyproject.toml`, `config.yaml`, `ruff.toml`, `.python-version`, `.gitignore` |
| 入口 | `main.py`, `gpu_grab/__main__.py`, `gpu_grab/cli.py` |
| 核心 | `config.py`, `models.py`, `gpu_monitor.py`, `queue_manager.py`, `task_runner.py`, `scheduler.py`, `server.py` |
| 工具 | `test_task.py`, `check_env.py` |

---

## 建议下一步

1. **添加 CLI serve 命令** - 在 `cli.py` 添加 `serve` 子命令调用 `__main__.main()`
2. **添加测试** - 创建 `tests/` 目录，覆盖核心逻辑（特别是热重载功能）
3. **系统服务** - 添加 systemd 单元文件实现开机启动
4. **实现日志 follow** - 完成 `cmd_logs` 的 `-f` 参数功能
5. **日志级别动态应用** - 热重载 `log_level` 后实时更新 root logger 级别

---

_此文档由 Claude 自动生成，最后更新：2026-01-10T17:00:31+0800_
