"""Unix socket server for handling CLI requests."""

import json
import logging
import os
import socket
import threading
from pathlib import Path
from typing import Any, Callable, Optional

logger = logging.getLogger(__name__)


class UnixSocketServer:
    """Unix socket server for CLI communication."""

    def __init__(
        self, socket_path: Path, handlers: dict[str, Callable[..., Any]]
    ) -> None:
        self.socket_path = socket_path
        self.handlers = handlers
        self._running = False
        self._socket: Optional[socket.socket] = None

    def start(self) -> None:
        """Start the socket server."""
        # Cleanup old socket file
        if self.socket_path.exists():
            try:
                self.socket_path.unlink()
            except OSError:
                # If socket is in use by another process, we might fail here
                # But since we're starting up, we assume we can take over
                pass

        self._socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self._socket.bind(str(self.socket_path))
        self._socket.listen(5)
        self._socket.settimeout(1.0)  # Allow checking _running flag

        # Set permissions so only user can access
        os.chmod(self.socket_path, 0o600)

        self._running = True
        logger.info(f"Unix socket server listening on {self.socket_path}")

        while self._running:
            try:
                conn, _ = self._socket.accept()
                thread = threading.Thread(
                    target=self._handle_connection, args=(conn,)
                )
                thread.daemon = True
                thread.start()
            except socket.timeout:
                continue
            except Exception as e:
                if self._running:
                    logger.error(f"Socket accept error: {e}")

    def stop(self) -> None:
        """Stop the socket server."""
        self._running = False
        if self._socket:
            try:
                self._socket.close()
            except Exception:
                pass
        if self.socket_path.exists():
            try:
                self.socket_path.unlink()
            except Exception:
                pass

    def _handle_connection(self, conn: socket.socket) -> None:
        """Handle individual connection."""
        try:
            # Read data
            data = b""
            while True:
                chunk = conn.recv(4096)
                if not chunk:
                    break
                data += chunk
                if b"\n" in data:
                    break

            if data:
                try:
                    request = json.loads(data.decode("utf-8"))
                    response = self._process_request(request)
                except json.JSONDecodeError:
                    response = {"success": False, "error": "Invalid JSON"}

                conn.sendall(json.dumps(response).encode("utf-8") + b"\n")
        except Exception as e:
            logger.error(f"Connection handling error: {e}")
            try:
                conn.sendall(
                    json.dumps({"success": False, "error": str(e)}).encode(
                        "utf-8"
                    )
                    + b"\n"
                )
            except Exception:
                pass
        finally:
            conn.close()

    def _process_request(self, request: dict[str, Any]) -> dict[str, Any]:
        """Process the request using registered handlers."""
        action = request.get("action")
        params = request.get("params", {})

        if not action:
            return {"success": False, "error": "Missing 'action' field"}

        if action not in self.handlers:
            return {"success": False, "error": f"Unknown action: {action}"}

        try:
            result = self.handlers[action](**params)
            return {"success": True, "data": result}
        except Exception as e:
            logger.exception(f"Handler error for {action}")
            return {"success": False, "error": str(e)}
