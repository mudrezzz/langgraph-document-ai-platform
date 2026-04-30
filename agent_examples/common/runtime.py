from __future__ import annotations

import os
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path

from agent_examples.common.framework_client import FrameworkClient, FrameworkClientError


@dataclass
class LocalApiRuntime:
    """Starts local FastAPI runtime for example agents.

    It intentionally uses only public API endpoints from the example code.
    """

    host: str = "127.0.0.1"
    port: int = 8210
    startup_timeout_sec: int = 30

    def __post_init__(self) -> None:
        self._process: subprocess.Popen[str] | None = None

    @property
    def base_url(self) -> str:
        return f"http://{self.host}:{self.port}"

    def start(self) -> None:
        if self._process is not None:
            return

        repo_root = Path(__file__).resolve().parents[2]
        backend_root = repo_root / "backend"

        env = os.environ.copy()
        env["PYTHONPATH"] = f"{backend_root}{os.pathsep}{backend_root / 'packages'}"

        self._process = subprocess.Popen(
            [
                sys.executable,
                "-m",
                "uvicorn",
                "apps.api.main:app",
                "--host",
                self.host,
                "--port",
                str(self.port),
            ],
            cwd=str(backend_root),
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )

        client = FrameworkClient(self.base_url)
        deadline = time.time() + self.startup_timeout_sec
        while time.time() < deadline:
            if self._process.poll() is not None:
                stdout = self._process.stdout.read().strip() if self._process.stdout else ""
                stderr = self._process.stderr.read().strip() if self._process.stderr else ""
                raise RuntimeError(
                    "Local API exited before health check. "
                    f"exit_code={self._process.returncode}\nstdout:\n{stdout}\nstderr:\n{stderr}"
                )
            try:
                payload = client.health()
                if payload.get("status") == "ok":
                    return
            except FrameworkClientError:
                pass
            time.sleep(0.25)

        raise TimeoutError(f"Local API did not become healthy within {self.startup_timeout_sec}s")

    def stop(self) -> None:
        if self._process is None:
            return
        self._process.terminate()
        try:
            self._process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            self._process.kill()
        self._process = None

    def __enter__(self) -> "LocalApiRuntime":
        self.start()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:  # type: ignore[no-untyped-def]
        self.stop()
