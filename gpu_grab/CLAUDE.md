[根目录](../CLAUDE.md) > **gpu_grab**

# gpu_grab 模块

> GPU Training Task Scheduler 核心包

---

## 变更记录 (Changelog)

| 日期 | 版本 | 变更内容 |
|------|------|----------|
| 2026-01-10 17:00 | v1.2.0 | 新增配置热重载功能：`RELOADABLE_KEYS`、`Config.reload()`、`Scheduler.reload_config()`、`reload` CLI 命令、SIGHUP 信号处理 |
| 2025-12-17 01:27 | v1.1.0 | 更新：新增 `__main__.py` 服务入口、`clean` 命令、行数更新 |
| 2025-12-09 17:27 | v1.0.0 | 初始化模块文档 |

---

## 模块职责

`gpu_grab` 是项目的核心 Python 包，实现：

- GPU 资源监控与状态查询
- 任务队列管理与持久化
- 子进程生命周期管理
- 资源感知的任务调度
- CLI 与服务端通信
- **配置热重载**（v1.2.0 新增）

---

## 入口与启动

| 入口点 | 路径 | 说明 |
|--------|------|------|
| 服务入口 | `__main__.py:main()` | 服务端主函数，可通过 `python -m gpu_grab` 启动 |
| CLI 入口 | `cli.py:main()` | 命令行工具主函数 |
| 包入口 | `__init__.py` | 版本定义 `__version__ = "0.1.0"` |

**pyproject.toml 配置**:
```toml
[project.scripts]
gpu-grab = "gpu_grab.cli:main"
```

**启动服务端**:
```bash
# 直接运行包
python -m gpu_grab

# 服务会监听 Unix Socket 并开始调度循环
```

---

## 对外接口

### CLI 命令

| 命令 | 处理函数 | 功能 |
|------|----------|------|
| `submit` | `cmd_submit()` | 提交任务 |
| `status` | `cmd_status()` | 系统状态 |
| `list` | `cmd_list()` | 任务列表 |
| `cancel` | `cmd_cancel()` | 取消任务 |
| `logs` | `cmd_logs()` | 查看日志 |
| `clean` | `cmd_clean()` | 清理已完成任务 |
| `reload` | `cmd_reload()` | **热重载配置**（v1.2.0 新增） |

### Socket 协议

客户端通过 Unix Socket (`~/.gpu-grab/gpu-grab.sock`) 发送 JSON 请求：

```json
{
  "action": "submit|status|list|cancel|logs|clean|reload",
  "params": { ... }
}
```

响应格式：
```json
{
  "success": true|false,
  "data": { ... },
  "error": "错误信息"
}
```

### 服务端请求处理器 (`__main__.py`)

| Action | 处理函数 | 参数 |
|--------|----------|------|
| `submit` | `handle_submit()` | command, name, working_dir, gpu_ids, gpu_count, ... |
| `status` | `handle_status()` | - |
| `list` | `handle_list()` | status_filter |
| `cancel` | `handle_cancel()` | task_id |
| `logs` | `handle_logs()` | task_id, tail, follow |
| `clean` | `handle_clean()` | status_filter |
| `reload` | `handle_reload()` | - (v1.2.0 新增) |

### 信号处理 (`__main__.py`)

| 信号 | 处理函数 | 行为 |
|------|----------|------|
| `SIGTERM` | `signal_handler()` | 优雅停止服务 |
| `SIGINT` | `signal_handler()` | 优雅停止服务 (Ctrl+C) |
| `SIGHUP` | `sighup_handler()` | **热重载配置**（v1.2.0 新增） |

---

## 关键依赖与配置

### 外部依赖

| 包 | 版本 | 用途 |
|----|------|------|
| `pynvml` | >=13.0.1 | NVIDIA GPU 监控 |
| `pyyaml` | >=6.0.3 | YAML 配置解析 |

### 内部依赖关系

```
__main__.py (服务入口)
  |-- scheduler.py (Scheduler)
  |     |-- gpu_monitor.py (GPUMonitor)
  |     |-- queue_manager.py (QueueManager)
  |     |-- task_runner.py (TaskRunner)
  |     +-- config.py (Config) --[reload()]--> 热重载
  |-- server.py (UnixSocketServer)
  |-- config.py (Config)
  +-- models.py (Task, GPURequirement, ...)

cli.py (CLI 客户端)
  +-- 通过 Socket 连接 server.py
```

### 配置路径

| 路径 | 用途 |
|------|------|
| `~/.gpu-grab/config.yaml` | 系统配置 |
| `~/.gpu-grab/data/tasks.json` | 任务队列持久化 |
| `~/.gpu-grab/logs/task_*.log` | 任务输出日志 |
| `~/.gpu-grab/logs/gpu-grab.log` | 服务日志（RotatingFileHandler） |
| `~/.gpu-grab/gpu-grab.sock` | Unix Socket |

---

## 数据模型

### models.py 核心类

| 类 | 说明 |
|----|------|
| `TaskStatus` | 枚举：PENDING, RUNNING, COMPLETED, FAILED, CANCELLED |
| `GPURequirement` | GPU 资源需求规格 |
| `Task` | 任务实体（ID、命令、状态、时间戳等） |
| `GPUStatus` | 单个 GPU 状态快照 |

### config.py 配置项与热重载

**可热重载配置项** (`RELOADABLE_KEYS`):

```python
RELOADABLE_KEYS = [
    "check_interval",
    "max_concurrent_tasks",
    "log_level",
    "default_gpu_count",
    "default_min_memory_gb",
    "default_max_util_percent",
]
```

| 配置 | 类型 | 默认值 | 可热重载 | 说明 |
|------|------|--------|----------|------|
| `check_interval` | float | 10.0 | Yes | GPU 检查间隔（秒） |
| `max_concurrent_tasks` | int | 4 | Yes | 最大并发任务数 |
| `log_level` | str | "INFO" | Yes | 日志级别 |
| `log_max_size_mb` | int | 10 | No | 日志文件最大大小 |
| `log_backup_count` | int | 5 | No | 日志备份数量 |
| `default_gpu_count` | int | 1 | Yes | 默认 GPU 数量 |
| `default_min_memory_gb` | float | 0.0 | Yes | 默认最小显存 |
| `default_max_util_percent` | float | 100.0 | Yes | 默认最大利用率 |

### Config.reload() 方法

```python
def reload(self, config_file: Optional[Path] = None) -> dict[str, dict[str, object]]:
    """Reload configuration from file.

    Only reloads keys defined in RELOADABLE_KEYS.

    Returns:
        Dict of changed values: {key: {"old": old_value, "new": new_value}}
    """
```

### Scheduler.reload_config() 方法

```python
def reload_config(self) -> dict[str, dict[str, object]]:
    """Reload configuration without interrupting running tasks.

    Returns:
        Dict of changed values from config.reload()
    """
```

---

## 测试与质量

- **测试目录**: 暂无
- **类型检查**: 完整类型注解，可用 mypy
- **代码风格**: Ruff（配置见 `ruff.toml`）

### 建议测试用例

| 模块 | 测试点 |
|------|--------|
| `queue_manager.py` | 任务 CRUD、优先级排序、文件锁、`clear_finished_tasks()` |
| `gpu_monitor.py` | 资源需求匹配逻辑、GPU 排除集合 |
| `scheduler.py` | 调度决策、并发限制、GPU 占用追踪、**`reload_config()`** |
| `task_runner.py` | 进程启动/终止、日志写入 |
| `__main__.py` | 请求处理器、信号处理、**SIGHUP 处理** |
| `config.py` | 配置加载/保存、**`reload()` 方法**、`RELOADABLE_KEYS` |

---

## 常见问题 (FAQ)

### Q: 服务端如何启动？

```bash
# 推荐方式
python -m gpu_grab

# 或者直接调用模块
python -c "from gpu_grab.__main__ import main; main()"
```

### Q: 如何指定特定 GPU？

```bash
gpu-grab submit "python train.py" --gpus 0,1
```

### Q: 任务日志在哪里？

`~/.gpu-grab/logs/task_<id>.log`

### Q: 如何清理旧任务？

```bash
# CLI 方式（需服务运行）
gpu-grab clean                    # 清理所有已完成任务
gpu-grab clean -s completed       # 只清理成功的
gpu-grab clean -s failed          # 只清理失败的

# 程序方式
from gpu_grab.queue_manager import QueueManager
qm = QueueManager(Path("~/.gpu-grab/data").expanduser())
qm.cleanup_old_tasks(max_age_days=7)  # 清理 7 天前的旧任务
```

### Q: 如何优雅停止服务？

发送 SIGTERM 或 SIGINT 信号：
```bash
kill -TERM <pid>
# 或 Ctrl+C
```

### Q: 如何热重载配置？（v1.2.0 新增）

**方式一：CLI 命令**
```bash
gpu-grab reload
# 输出示例：
# Configuration reloaded:
#   check_interval: 10.0 -> 5.0
#   max_concurrent_tasks: 4 -> 8
```

**方式二：发送 SIGHUP 信号**
```bash
# 查找服务 PID
pgrep -f "python -m gpu_grab"
# 或
ps aux | grep gpu_grab

# 发送信号
kill -HUP <pid>
```

**注意事项**：
- 只有 `RELOADABLE_KEYS` 中定义的配置项会被重载
- 重载不会中断正在运行的任务
- 重载后 `check_interval` 在下一个调度周期生效
- `log_level` 重载后需要手动更新 root logger（当前未实现）

---

## 相关文件清单

| 文件 | 行数 | 职责 |
|------|------|------|
| `__init__.py` | 4 | 版本定义 |
| `__main__.py` | 162 | 服务入口、请求处理、信号处理 |
| `config.py` | 122 | 配置管理、热重载 |
| `models.py` | 158 | 数据模型 |
| `gpu_monitor.py` | 151 | GPU 监控 |
| `queue_manager.py` | 182 | 队列管理 |
| `task_runner.py` | 166 | 任务执行 |
| `scheduler.py` | 176 | 调度器、配置重载 |
| `server.py` | 123 | Socket 服务 |
| `cli.py` | 262 | CLI |

**总计**: 约 1,506 行代码

---

_此文档由 Claude 自动生成，最后更新：2026-01-10T17:00:31+0800_
