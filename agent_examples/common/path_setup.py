from __future__ import annotations

import sys
from pathlib import Path


def ensure_backend_paths(repo_root: Path | None = None) -> None:
    """Ensure `backend` and `backend/packages` are importable for in-process demos."""

    resolved_repo = repo_root or Path(__file__).resolve().parents[2]
    backend_root = resolved_repo / "backend"
    packages_root = backend_root / "packages"

    for path in (backend_root, packages_root):
        value = str(path)
        if value not in sys.path:
            sys.path.insert(0, value)
