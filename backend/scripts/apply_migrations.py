from __future__ import annotations

import os
from pathlib import Path


def main() -> None:
    dsn = os.getenv("APP_DB_DSN")
    if not dsn:
        raise RuntimeError("Переменная APP_DB_DSN не задана")

    try:
        import psycopg
    except Exception as exc:  # pragma: no cover - зависит от окружения
        raise RuntimeError("Требуется зависимость psycopg[binary]") from exc

    migrations_dir = Path(__file__).resolve().parents[1] / "migrations"
    files = sorted(migrations_dir.glob("*.sql"))

    if not files:
        print("Миграции не найдены")
        return

    with psycopg.connect(dsn, autocommit=True) as conn:
        with conn.cursor() as cur:
            for file in files:
                sql_text = file.read_text(encoding="utf-8")
                cur.execute(sql_text)
                print(f"applied: {file.name}")


if __name__ == "__main__":
    main()