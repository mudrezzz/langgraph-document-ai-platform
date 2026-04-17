from __future__ import annotations

import sys
from pathlib import Path


# Добавляем каталог backend и backend/packages в path для локальных тестов.
BACKEND_ROOT = Path(__file__).resolve().parents[1]
PACKAGES_ROOT = BACKEND_ROOT / "packages"

if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

if str(PACKAGES_ROOT) not in sys.path:
    sys.path.insert(0, str(PACKAGES_ROOT))