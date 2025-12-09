[根目录](../CLAUDE.md) > **gpu_grab**

# gpu_grab 模块

> GPU Training Task Scheduler 核心包

---

## 变更记录 (Changelog)

| 日期 | 版本 | 变更内容 |
|------|------|----------|
| 2025-12-09 17:27 | v1.0.0 | 初始化模块文档 |

---

## 模块职责

`gpu_grab` 是项目的核心 Python 包，实现：

- GPU 资源监控与状态查询
- 任务队列管理与持久化
- 子进程生命周期管理
- 资源感知的任务调度
- CLI 与服务端通信

---

## 入口与启动

| 入口点 | 路径 | 说明 |
|--------|------|------|
| CLI 入口 | `cli.py:main()` | 命令行工具主函数 |
| 包入口 | `__init__.py` | 版本定义 `__version__ = "0.1.0"` |

**pyproject.toml 配置**:
```toml
[project.scripts]
gpu-grab = "gpu_grab.cli:main"
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

### Socket 协议

客户端通过 Unix Socket (`~/.gpu-grab/gpu-grab.sock`) 发送 JSON 请求：

```json
{
  "action": "submit|status|list|cancel|logs",
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

---

## 关键依赖与配置

### 外部依赖

| 包 | 版本 | 用途 |
|----|------|------|
| `pynvml` | >=13.0.1 | NVIDIA GPU 监控 |
| `pyyaml` | >=6.0.3 | YAML 配置解析 |

### 内部依赖关系

```
cli.py
  └── server.py (UnixSocketServer)
        └── scheduler.py (Scheduler)
              ├── gpu_monitor.py (GPUMonitor)
              ├── queue_manager.py (QueueManager)
              └── task_runner.py (TaskRunner)
                    └── models.py (Task, GPUStatus, ...)
                          └── config.py (Config)
```

### 配置路径

| 路径 | 用途 |
|------|------|
| `~/.gpu-grab/config.yaml` | 系统配置 |
| `~/.gpu-grab/data/tasks.json` | 任务队列持久化 |
| `~/.gpu-grab/logs/task_*.log` | 任务输出日志 |
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

### config.py 配置项

| 配置 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `check_interval` | float | 10.0 | GPU 检查间隔（秒） |
| `max_concurrent_tasks` | int | 4 | 最大并发任务数 |
| `log_level` | str | "INFO" | 日志级别 |
| `default_gpu_count` | int | 1 | 默认 GPU 数量 |
| `default_min_memory_gb` | float | 0.0 | 默认最小显存 |

---

## 测试与质量

- **测试目录**: 暂无
- **类型检查**: 完整类型注解，可用 mypy
- **代码风格**: 建议 black + ruff

### 建议测试用例

| 模块 | 测试点 |
|------|--------|
| `queue_manager.py` | 任务 CRUD、优先级排序、文件锁 |
| `gpu_monitor.py` | 资源需求匹配逻辑 |
| `scheduler.py` | 调度决策、并发限制 |
| `task_runner.py` | 进程启动/终止、日志写入 |

---

## 常见问题 (FAQ)

### Q: 服务端如何启动？

当前 `cli.py` 缺少 `serve` 子命令。需要直接调用：
```python
from gpu_grab.config import Config
from gpu_grab.scheduler import Scheduler

config = Config.load()
scheduler = Scheduler(config)
scheduler.start()  # 阻塞运行
```

### Q: 如何指定特定 GPU？

```bash
gpu-grab submit "python train.py" --gpus 0,1
```

### Q: 任务日志在哪里？

`~/.gpu-grab/logs/task_<id>.log`

### Q: 如何清理旧任务？

调用 `QueueManager.cleanup_old_tasks(max_age_days=7)`

---

## 相关文件清单

| 文件 | 行数 | 职责 |
|------|------|------|
| `__init__.py` | 3 | 版本定义 |
| `config.py` | 84 | 配置管理 |
| `models.py` | 158 | 数据模型 |
| `gpu_monitor.py` | 141 | GPU 监控 |
| `queue_manager.py` | 156 | 队列管理 |
| `task_runner.py` | 157 | 任务执行 |
| `scheduler.py` | 153 | 调度器 |
| `server.py` | 127 | Socket 服务 |
| `cli.py` | 223 | CLI |

---

_此文档由 Claude 自动生成，最后更新：2025-12-09T17:27:32+0800_
