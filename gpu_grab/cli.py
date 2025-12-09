"""CLI entry point for GPU Grab."""

import argparse
import json
import os
import socket
import sys
from pathlib import Path
from typing import Any, Optional

# Default socket location
DEFAULT_SOCKET_PATH = Path.home() / ".gpu-grab" / "gpu-grab.sock"


def send_request(
    socket_path: Path, action: str, params: Optional[dict[str, Any]] = None
) -> dict[str, Any]:
    """Send request to the server."""
    sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    try:
        sock.connect(str(socket_path))
        request = {"action": action, "params": params or {}}
        sock.sendall(json.dumps(request).encode("utf-8") + b"\n")

        data = b""
        while True:
            chunk = sock.recv(4096)
            if not chunk:
                break
            data += chunk
            if b"\n" in data:
                break

        return json.loads(data.decode("utf-8"))
    except FileNotFoundError:
        return {
            "success": False,
            "error": f"Socket not found at {socket_path}. Is the service running?",
        }
    except ConnectionRefusedError:
        return {
            "success": False,
            "error": "Connection refused. Is the service running?",
        }
    except Exception as e:
        return {"success": False, "error": str(e)}
    finally:
        sock.close()


def cmd_submit(args: argparse.Namespace) -> None:
    """Submit a task."""
    params = {
        "command": args.command,
        "name": args.name or f"task-{os.getpid()}",
        "working_dir": args.workdir or os.getcwd(),
        "gpu_ids": [int(x) for x in args.gpus.split(",")] if args.gpus else None,
        "min_free_memory_gb": args.memory,
        "max_util_percent": 100 - args.util_margin,
        "gpu_count": args.gpu_count,
        "priority": args.priority,
        "env": dict(item.split("=", 1) for item in args.env) if args.env else {},
    }

    result = send_request(DEFAULT_SOCKET_PATH, "submit", params)
    if result.get("success"):
        print(f"Task submitted successfully. ID: {result['data']['task_id']}")
    else:
        print(f"Error: {result.get('error')}", file=sys.stderr)
        sys.exit(1)


def cmd_status(args: argparse.Namespace) -> None:
    """Show system status."""
    result = send_request(DEFAULT_SOCKET_PATH, "status")
    if result.get("success"):
        data = result["data"]

        print("=== GPU Status ===")
        for gpu in data["gpus"]:
            print(f"  GPU {gpu['index']}: {gpu['name']}")
            print(
                f"    Memory: {gpu['used_memory_mb']}/{gpu['total_memory_mb']} MB "
                f"({gpu['free_memory_mb']} MB free)"
            )
            print(f"    Utilization: {gpu['utilization_percent']}%")
            print(f"    Temperature: {gpu['temperature']}°C")

        print("\n=== Task Statistics ===")
        tasks = data["tasks"]
        print(f"  Pending:   {tasks['pending']}")
        print(f"  Running:   {tasks['running']}")
        print(f"  Completed: {tasks['completed']}")
        print(f"  Failed:    {tasks['failed']}")
        print(f"  Cancelled: {tasks['cancelled']}")

        print(f"\n=== Service ===")
        print(f"  Status: {'Running' if data['running'] else 'Stopped'}")
        print(f"  Uptime: {data['uptime_seconds']:.0f}s")
        if "config" in data:
            print(f"  Check Interval: {data['config']['check_interval']}s")
            print(f"  Max Concurrent: {data['config']['max_concurrent_tasks']}")
    else:
        print(f"Error: {result.get('error')}", file=sys.stderr)
        sys.exit(1)


def cmd_list(args: argparse.Namespace) -> None:
    """List tasks."""
    params = {"status_filter": args.status}
    result = send_request(DEFAULT_SOCKET_PATH, "list", params)
    if result.get("success"):
        tasks = result["data"]["tasks"]
        if not tasks:
            print("No tasks found.")
            return

        # Header
        print(
            f"{'ID':<10} {'Name':<20} {'Status':<12} {'GPUs':<10} {'Created':<20}"
        )
        print("-" * 75)

        for task in tasks:
            gpus = ",".join(map(str, task.get("assigned_gpus", []))) or "-"
            created = task.get("created_at", "")[:19].replace("T", " ")
            print(
                f"{task['id']:<10} {task['name'][:20]:<20} {task['status']:<12} "
                f"{gpus:<10} {created:<20}"
            )
    else:
        print(f"Error: {result.get('error')}", file=sys.stderr)
        sys.exit(1)


def cmd_cancel(args: argparse.Namespace) -> None:
    """Cancel a task."""
    result = send_request(DEFAULT_SOCKET_PATH, "cancel", {"task_id": args.task_id})
    if result.get("success"):
        print(f"Task {args.task_id} cancelled.")
    else:
        print(f"Error: {result.get('error')}", file=sys.stderr)
        sys.exit(1)


def cmd_logs(args: argparse.Namespace) -> None:
    """View task logs."""
    result = send_request(
        DEFAULT_SOCKET_PATH,
        "logs",
        {"task_id": args.task_id, "tail": args.tail, "follow": args.follow},
    )
    if result.get("success"):
        print(result["data"]["logs"], end="")
    else:
        print(f"Error: {result.get('error')}", file=sys.stderr)
        sys.exit(1)


def main() -> None:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        prog="gpu-grab", description="GPU Training Task Scheduler"
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # submit
    p_submit = subparsers.add_parser("submit", help="Submit a new task")
    p_submit.add_argument("command", help="Command to execute")
    p_submit.add_argument("-n", "--name", help="Task name")
    p_submit.add_argument("-w", "--workdir", help="Working directory")
    p_submit.add_argument("-g", "--gpus", help="Specific GPU IDs (e.g. 0,1)")
    p_submit.add_argument(
        "-c", "--gpu-count", type=int, default=1, help="Number of GPUs required"
    )
    p_submit.add_argument(
        "-m", "--memory", type=float, default=0, help="Min free memory (GB)"
    )
    p_submit.add_argument(
        "-u", "--util-margin", type=float, default=0, help="Required idle margin (%)"
    )
    p_submit.add_argument(
        "-p", "--priority", type=int, default=0, help="Task priority"
    )
    p_submit.add_argument(
        "-e", "--env", nargs="*", help="Environment variables (KEY=VALUE)"
    )
    p_submit.set_defaults(func=cmd_submit)

    # status
    p_status = subparsers.add_parser("status", help="Show system status")
    p_status.set_defaults(func=cmd_status)

    # list
    p_list = subparsers.add_parser("list", help="List tasks")
    p_list.add_argument(
        "-s",
        "--status",
        choices=["all", "pending", "running", "completed", "failed", "cancelled"],
        default="all",
        help="Filter by status",
    )
    p_list.set_defaults(func=cmd_list)

    # cancel
    p_cancel = subparsers.add_parser("cancel", help="Cancel a task")
    p_cancel.add_argument("task_id", help="Task ID to cancel")
    p_cancel.set_defaults(func=cmd_cancel)

    # logs
    p_logs = subparsers.add_parser("logs", help="View task logs")
    p_logs.add_argument("task_id", help="Task ID")
    p_logs.add_argument(
        "-t", "--tail", type=int, default=100, help="Number of lines to show"
    )
    p_logs.add_argument(
        "-f", "--follow", action="store_true", help="Follow log output (TODO)"
    )
    p_logs.set_defaults(func=cmd_logs)

    args = parser.parse_args()
    args.func(args)
