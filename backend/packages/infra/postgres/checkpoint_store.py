from __future__ import annotations

import base64
import json
from typing import Any, Iterator, Sequence

from framework.stores.interfaces import ICheckpointStore
from infra.postgres.config import PostgresSettings, validate_identifier

try:
    from langgraph.checkpoint.base import (
        WRITES_IDX_MAP,
        BaseCheckpointSaver,
        ChannelVersions,
        Checkpoint,
        CheckpointMetadata,
        CheckpointTuple,
        get_checkpoint_id,
        get_checkpoint_metadata,
    )
    from langgraph.checkpoint.memory import InMemorySaver

    LANGGRAPH_CHECKPOINTER_AVAILABLE = True
except Exception:  # pragma: no cover - защитная ветка для окружений без langgraph
    LANGGRAPH_CHECKPOINTER_AVAILABLE = False
    BaseCheckpointSaver = object  # type: ignore[assignment]
    InMemorySaver = None  # type: ignore[assignment]
    WRITES_IDX_MAP: dict[str, int] = {}


class LangGraphPostgresCheckpointStore(ICheckpointStore):
    """Checkpoint store для task payload и LangGraph checkpointer поверх PostgreSQL."""

    def __init__(
        self,
        dsn: str | None = None,
        schema: str = "app",
        *,
        use_fallback_if_unset: bool = True,
    ) -> None:
        self._schema = schema
        validate_identifier(self._schema)

        self._dsn = dsn
        self._use_fallback = use_fallback_if_unset and not bool(dsn)
        self._checkpoints: dict[str, dict[str, Any]] = {}
        self._langgraph_checkpointer: Any | None = None

        if not self._use_fallback and not self._dsn:
            raise ValueError("DSN обязателен для PostgreSQL checkpoint store")

    @classmethod
    def from_settings(
        cls,
        settings: PostgresSettings,
        *,
        use_fallback_if_unset: bool | None = None,
    ) -> "LangGraphPostgresCheckpointStore":
        fallback_enabled = settings.allow_fallback_persistence if use_fallback_if_unset is None else use_fallback_if_unset
        return cls(dsn=settings.dsn, schema=settings.schema, use_fallback_if_unset=fallback_enabled)

    def build_langgraph_checkpointer(self) -> Any | None:
        """Возвращает checkpointer для `StateGraph.compile(checkpointer=...)`."""

        if not LANGGRAPH_CHECKPOINTER_AVAILABLE:
            return None

        if self._langgraph_checkpointer is not None:
            return self._langgraph_checkpointer

        if self._use_fallback:
            self._langgraph_checkpointer = InMemorySaver()
        else:
            self._langgraph_checkpointer = PostgresLangGraphCheckpointer(
                dsn=self._dsn,
                schema=self._schema,
            )
        return self._langgraph_checkpointer

    def save_checkpoint(self, run_id: str, payload: dict) -> None:
        if self._use_fallback:
            self._checkpoints[run_id] = payload
            return

        psycopg, dict_row = _import_psycopg()
        payload_json = json.dumps(payload, ensure_ascii=False)

        with psycopg.connect(self._dsn, autocommit=True, row_factory=dict_row) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    f"""
                    INSERT INTO {self._schema}.checkpoints (run_id, payload)
                    VALUES (%s, %s::jsonb)
                    ON CONFLICT (run_id)
                    DO UPDATE SET payload = EXCLUDED.payload, updated_at = now()
                    """,
                    (run_id, payload_json),
                )

    def load_checkpoint(self, run_id: str) -> dict | None:
        if self._use_fallback:
            return self._checkpoints.get(run_id)

        psycopg, dict_row = _import_psycopg()

        with psycopg.connect(self._dsn, autocommit=True, row_factory=dict_row) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    f"SELECT payload FROM {self._schema}.checkpoints WHERE run_id = %s",
                    (run_id,),
                )
                row = cur.fetchone()

        if row is None:
            return None

        payload = row["payload"]
        if isinstance(payload, str):
            return json.loads(payload)
        return payload


if LANGGRAPH_CHECKPOINTER_AVAILABLE:

    class PostgresLangGraphCheckpointer(BaseCheckpointSaver[str]):
        """LangGraph checkpointer на выделенных PostgreSQL таблицах."""

        def __init__(self, dsn: str | None, schema: str = "app") -> None:
            super().__init__()
            if not dsn:
                raise ValueError("DSN обязателен для PostgreSQL LangGraph checkpointer")

            self._dsn = dsn
            self._schema = schema
            validate_identifier(self._schema)

        def get_tuple(self, config: dict[str, Any]) -> CheckpointTuple | None:
            thread_id, checkpoint_ns = self._extract_thread_and_ns(config)
            checkpoint_id = get_checkpoint_id(config)

            row = self._fetch_checkpoint_row(
                thread_id=thread_id,
                checkpoint_ns=checkpoint_ns,
                checkpoint_id=str(checkpoint_id) if checkpoint_id else None,
            )
            if row is None:
                return None

            resolved_checkpoint_id = row["checkpoint_id"]
            checkpoint_payload = self.serde.loads_typed(self._decode_typed_field(row["checkpoint_payload"]))
            metadata_payload = self.serde.loads_typed(self._decode_typed_field(row["metadata_payload"]))
            channel_values = self._load_channel_values(
                thread_id=thread_id,
                checkpoint_ns=checkpoint_ns,
                channel_versions=checkpoint_payload.get("channel_versions", {}),
            )
            parent_checkpoint_id = row["parent_checkpoint_id"]

            return CheckpointTuple(
                config={
                    "configurable": {
                        "thread_id": thread_id,
                        "checkpoint_ns": checkpoint_ns,
                        "checkpoint_id": resolved_checkpoint_id,
                    }
                },
                checkpoint={**checkpoint_payload, "channel_values": channel_values},
                metadata=metadata_payload,
                parent_config=(
                    {
                        "configurable": {
                            "thread_id": thread_id,
                            "checkpoint_ns": checkpoint_ns,
                            "checkpoint_id": parent_checkpoint_id,
                        }
                    }
                    if parent_checkpoint_id
                    else None
                ),
                pending_writes=self._fetch_pending_writes(
                    thread_id=thread_id,
                    checkpoint_ns=checkpoint_ns,
                    checkpoint_id=resolved_checkpoint_id,
                ),
            )

        def list(
            self,
            config: dict[str, Any] | None,
            *,
            filter: dict[str, Any] | None = None,
            before: dict[str, Any] | None = None,
            limit: int | None = None,
        ) -> Iterator[CheckpointTuple]:
            config_checkpoint_id = get_checkpoint_id(config) if config else None
            before_checkpoint_id = get_checkpoint_id(before) if before else None

            thread_id = str(config["configurable"]["thread_id"]) if config else None
            checkpoint_ns = config["configurable"].get("checkpoint_ns") if config else None

            rows = self._list_checkpoint_rows(
                thread_id=thread_id,
                checkpoint_ns=str(checkpoint_ns) if checkpoint_ns is not None else None,
                checkpoint_id=str(config_checkpoint_id) if config_checkpoint_id else None,
                before_checkpoint_id=str(before_checkpoint_id) if before_checkpoint_id else None,
            )

            for row in rows:
                metadata_payload = self.serde.loads_typed(self._decode_typed_field(row["metadata_payload"]))
                if filter and not all(metadata_payload.get(key) == value for key, value in filter.items()):
                    continue

                if limit is not None:
                    if limit <= 0:
                        return
                    limit -= 1

                row_thread_id = row["thread_id"]
                row_checkpoint_ns = row["checkpoint_ns"]
                row_checkpoint_id = row["checkpoint_id"]

                checkpoint_payload = self.serde.loads_typed(self._decode_typed_field(row["checkpoint_payload"]))
                channel_values = self._load_channel_values(
                    thread_id=row_thread_id,
                    checkpoint_ns=row_checkpoint_ns,
                    channel_versions=checkpoint_payload.get("channel_versions", {}),
                )
                parent_checkpoint_id = row["parent_checkpoint_id"]

                yield CheckpointTuple(
                    config={
                        "configurable": {
                            "thread_id": row_thread_id,
                            "checkpoint_ns": row_checkpoint_ns,
                            "checkpoint_id": row_checkpoint_id,
                        }
                    },
                    checkpoint={**checkpoint_payload, "channel_values": channel_values},
                    metadata=metadata_payload,
                    parent_config=(
                        {
                            "configurable": {
                                "thread_id": row_thread_id,
                                "checkpoint_ns": row_checkpoint_ns,
                                "checkpoint_id": parent_checkpoint_id,
                            }
                        }
                        if parent_checkpoint_id
                        else None
                    ),
                    pending_writes=self._fetch_pending_writes(
                        thread_id=row_thread_id,
                        checkpoint_ns=row_checkpoint_ns,
                        checkpoint_id=row_checkpoint_id,
                    ),
                )

        def put(
            self,
            config: dict[str, Any],
            checkpoint: Checkpoint,
            metadata: CheckpointMetadata,
            new_versions: ChannelVersions,
        ) -> dict[str, Any]:
            thread_id, checkpoint_ns = self._extract_thread_and_ns(config)
            checkpoint_id = str(checkpoint["id"])
            parent_checkpoint_id = config["configurable"].get("checkpoint_id")

            checkpoint_copy = checkpoint.copy()
            channel_values: dict[str, Any] = checkpoint_copy.pop("channel_values", {})
            checkpoint_encoded = self._encode_typed_field(self.serde.dumps_typed(checkpoint_copy))
            metadata_encoded = self._encode_typed_field(
                self.serde.dumps_typed(get_checkpoint_metadata(config, metadata)),
            )

            psycopg, dict_row = _import_psycopg()
            with psycopg.connect(self._dsn, autocommit=True, row_factory=dict_row) as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        f"""
                        INSERT INTO {self._schema}.langgraph_checkpoints (
                            thread_id,
                            checkpoint_ns,
                            checkpoint_id,
                            parent_checkpoint_id,
                            checkpoint_payload,
                            metadata_payload
                        ) VALUES (%s, %s, %s, %s, %s::jsonb, %s::jsonb)
                        ON CONFLICT (thread_id, checkpoint_ns, checkpoint_id)
                        DO UPDATE SET
                            parent_checkpoint_id = EXCLUDED.parent_checkpoint_id,
                            checkpoint_payload = EXCLUDED.checkpoint_payload,
                            metadata_payload = EXCLUDED.metadata_payload,
                            updated_at = now()
                        """,
                        (
                            thread_id,
                            checkpoint_ns,
                            checkpoint_id,
                            str(parent_checkpoint_id) if parent_checkpoint_id else None,
                            json.dumps(checkpoint_encoded, ensure_ascii=False),
                            json.dumps(metadata_encoded, ensure_ascii=False),
                        ),
                    )

                    for channel_name, channel_version in new_versions.items():
                        channel_version_token = str(channel_version)
                        if channel_name in channel_values:
                            blob_payload = self._encode_typed_field(self.serde.dumps_typed(channel_values[channel_name]))
                        else:
                            blob_payload = {"type": "empty", "blob_b64": ""}

                        cur.execute(
                            f"""
                            INSERT INTO {self._schema}.langgraph_checkpoint_blobs (
                                thread_id,
                                checkpoint_ns,
                                channel_name,
                                channel_version,
                                blob_payload
                            ) VALUES (%s, %s, %s, %s, %s::jsonb)
                            ON CONFLICT (thread_id, checkpoint_ns, channel_name, channel_version)
                            DO UPDATE SET
                                blob_payload = EXCLUDED.blob_payload
                            """,
                            (
                                thread_id,
                                checkpoint_ns,
                                channel_name,
                                channel_version_token,
                                json.dumps(blob_payload, ensure_ascii=False),
                            ),
                        )

            return {
                "configurable": {
                    "thread_id": thread_id,
                    "checkpoint_ns": checkpoint_ns,
                    "checkpoint_id": checkpoint_id,
                }
            }

        def put_writes(
            self,
            config: dict[str, Any],
            writes: Sequence[tuple[str, Any]],
            task_id: str,
            task_path: str = "",
        ) -> None:
            thread_id, checkpoint_ns = self._extract_thread_and_ns(config)
            checkpoint_id = str(config["configurable"]["checkpoint_id"])

            psycopg, dict_row = _import_psycopg()
            with psycopg.connect(self._dsn, autocommit=True, row_factory=dict_row) as conn:
                with conn.cursor() as cur:
                    for index, (channel_name, value) in enumerate(writes):
                        write_idx = WRITES_IDX_MAP.get(channel_name, index)
                        value_payload = self._encode_typed_field(self.serde.dumps_typed(value))

                        if write_idx >= 0:
                            # Нормальные индексы считаем идемпотентными и не перетираем повторно.
                            cur.execute(
                                f"""
                                INSERT INTO {self._schema}.langgraph_checkpoint_writes (
                                    thread_id,
                                    checkpoint_ns,
                                    checkpoint_id,
                                    task_id,
                                    write_idx,
                                    channel_name,
                                    value_payload,
                                    task_path
                                ) VALUES (%s, %s, %s, %s, %s, %s, %s::jsonb, %s)
                                ON CONFLICT (thread_id, checkpoint_ns, checkpoint_id, task_id, write_idx)
                                DO NOTHING
                                """,
                                (
                                    thread_id,
                                    checkpoint_ns,
                                    checkpoint_id,
                                    task_id,
                                    write_idx,
                                    channel_name,
                                    json.dumps(value_payload, ensure_ascii=False),
                                    task_path,
                                ),
                            )
                        else:
                            # Спец-каналы (`__error__`, `__interrupt__` и т.п.) разрешаем обновлять.
                            cur.execute(
                                f"""
                                INSERT INTO {self._schema}.langgraph_checkpoint_writes (
                                    thread_id,
                                    checkpoint_ns,
                                    checkpoint_id,
                                    task_id,
                                    write_idx,
                                    channel_name,
                                    value_payload,
                                    task_path
                                ) VALUES (%s, %s, %s, %s, %s, %s, %s::jsonb, %s)
                                ON CONFLICT (thread_id, checkpoint_ns, checkpoint_id, task_id, write_idx)
                                DO UPDATE SET
                                    channel_name = EXCLUDED.channel_name,
                                    value_payload = EXCLUDED.value_payload,
                                    task_path = EXCLUDED.task_path,
                                    created_at = now()
                                """,
                                (
                                    thread_id,
                                    checkpoint_ns,
                                    checkpoint_id,
                                    task_id,
                                    write_idx,
                                    channel_name,
                                    json.dumps(value_payload, ensure_ascii=False),
                                    task_path,
                                ),
                            )

        def delete_thread(self, thread_id: str) -> None:
            psycopg, dict_row = _import_psycopg()
            with psycopg.connect(self._dsn, autocommit=True, row_factory=dict_row) as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        f"DELETE FROM {self._schema}.langgraph_checkpoint_writes WHERE thread_id = %s",
                        (thread_id,),
                    )
                    cur.execute(
                        f"DELETE FROM {self._schema}.langgraph_checkpoint_blobs WHERE thread_id = %s",
                        (thread_id,),
                    )
                    cur.execute(
                        f"DELETE FROM {self._schema}.langgraph_checkpoints WHERE thread_id = %s",
                        (thread_id,),
                    )

        def delete_for_runs(self, run_ids: Sequence[str]) -> None:
            for run_id in run_ids:
                self.delete_thread(run_id)

        def copy_thread(self, source_thread_id: str, target_thread_id: str) -> None:
            psycopg, dict_row = _import_psycopg()
            with psycopg.connect(self._dsn, autocommit=True, row_factory=dict_row) as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        f"""
                        INSERT INTO {self._schema}.langgraph_checkpoints (
                            thread_id,
                            checkpoint_ns,
                            checkpoint_id,
                            parent_checkpoint_id,
                            checkpoint_payload,
                            metadata_payload
                        )
                        SELECT
                            %s,
                            checkpoint_ns,
                            checkpoint_id,
                            parent_checkpoint_id,
                            checkpoint_payload,
                            metadata_payload
                        FROM {self._schema}.langgraph_checkpoints
                        WHERE thread_id = %s
                        ON CONFLICT (thread_id, checkpoint_ns, checkpoint_id)
                        DO UPDATE SET
                            parent_checkpoint_id = EXCLUDED.parent_checkpoint_id,
                            checkpoint_payload = EXCLUDED.checkpoint_payload,
                            metadata_payload = EXCLUDED.metadata_payload,
                            updated_at = now()
                        """,
                        (target_thread_id, source_thread_id),
                    )
                    cur.execute(
                        f"""
                        INSERT INTO {self._schema}.langgraph_checkpoint_blobs (
                            thread_id,
                            checkpoint_ns,
                            channel_name,
                            channel_version,
                            blob_payload
                        )
                        SELECT
                            %s,
                            checkpoint_ns,
                            channel_name,
                            channel_version,
                            blob_payload
                        FROM {self._schema}.langgraph_checkpoint_blobs
                        WHERE thread_id = %s
                        ON CONFLICT (thread_id, checkpoint_ns, channel_name, channel_version)
                        DO UPDATE SET
                            blob_payload = EXCLUDED.blob_payload
                        """,
                        (target_thread_id, source_thread_id),
                    )
                    cur.execute(
                        f"""
                        INSERT INTO {self._schema}.langgraph_checkpoint_writes (
                            thread_id,
                            checkpoint_ns,
                            checkpoint_id,
                            task_id,
                            write_idx,
                            channel_name,
                            value_payload,
                            task_path
                        )
                        SELECT
                            %s,
                            checkpoint_ns,
                            checkpoint_id,
                            task_id,
                            write_idx,
                            channel_name,
                            value_payload,
                            task_path
                        FROM {self._schema}.langgraph_checkpoint_writes
                        WHERE thread_id = %s
                        ON CONFLICT (thread_id, checkpoint_ns, checkpoint_id, task_id, write_idx)
                        DO UPDATE SET
                            channel_name = EXCLUDED.channel_name,
                            value_payload = EXCLUDED.value_payload,
                            task_path = EXCLUDED.task_path,
                            created_at = now()
                        """,
                        (target_thread_id, source_thread_id),
                    )

        def prune(
            self,
            thread_ids: Sequence[str],
            *,
            strategy: str = "keep_latest",
        ) -> None:
            if strategy not in {"keep_latest", "delete"}:
                raise ValueError("strategy должен быть одним из: keep_latest, delete")

            if strategy == "delete":
                for thread_id in thread_ids:
                    self.delete_thread(thread_id)
                return

            psycopg, dict_row = _import_psycopg()
            with psycopg.connect(self._dsn, autocommit=True, row_factory=dict_row) as conn:
                with conn.cursor() as cur:
                    for thread_id in thread_ids:
                        cur.execute(
                            f"""
                            SELECT DISTINCT checkpoint_ns
                            FROM {self._schema}.langgraph_checkpoints
                            WHERE thread_id = %s
                            """,
                            (thread_id,),
                        )
                        namespaces = [row["checkpoint_ns"] for row in cur.fetchall()]

                        for checkpoint_ns in namespaces:
                            latest = self._fetch_checkpoint_row(
                                thread_id=thread_id,
                                checkpoint_ns=checkpoint_ns,
                                checkpoint_id=None,
                            )
                            if latest is None:
                                continue

                            latest_checkpoint_id = latest["checkpoint_id"]
                            checkpoint_payload = self.serde.loads_typed(
                                self._decode_typed_field(latest["checkpoint_payload"]),
                            )

                            keep_blob_keys: set[tuple[str, str]] = set()
                            channel_versions = checkpoint_payload.get("channel_versions", {})
                            if isinstance(channel_versions, dict):
                                for channel_name, channel_version in channel_versions.items():
                                    keep_blob_keys.add((str(channel_name), str(channel_version)))

                            cur.execute(
                                f"""
                                DELETE FROM {self._schema}.langgraph_checkpoint_writes
                                WHERE thread_id = %s AND checkpoint_ns = %s AND checkpoint_id <> %s
                                """,
                                (thread_id, checkpoint_ns, latest_checkpoint_id),
                            )
                            cur.execute(
                                f"""
                                DELETE FROM {self._schema}.langgraph_checkpoints
                                WHERE thread_id = %s AND checkpoint_ns = %s AND checkpoint_id <> %s
                                """,
                                (thread_id, checkpoint_ns, latest_checkpoint_id),
                            )

                            cur.execute(
                                f"""
                                SELECT channel_name, channel_version
                                FROM {self._schema}.langgraph_checkpoint_blobs
                                WHERE thread_id = %s AND checkpoint_ns = %s
                                """,
                                (thread_id, checkpoint_ns),
                            )
                            existing_blobs = [(row["channel_name"], row["channel_version"]) for row in cur.fetchall()]
                            for channel_name, channel_version in existing_blobs:
                                if (channel_name, channel_version) in keep_blob_keys:
                                    continue
                                cur.execute(
                                    f"""
                                    DELETE FROM {self._schema}.langgraph_checkpoint_blobs
                                    WHERE thread_id = %s AND checkpoint_ns = %s AND channel_name = %s AND channel_version = %s
                                    """,
                                    (thread_id, checkpoint_ns, channel_name, channel_version),
                                )

        async def aget_tuple(self, config: dict[str, Any]) -> CheckpointTuple | None:
            return self.get_tuple(config)

        async def alist(
            self,
            config: dict[str, Any] | None,
            *,
            filter: dict[str, Any] | None = None,
            before: dict[str, Any] | None = None,
            limit: int | None = None,
        ):
            for item in self.list(config=config, filter=filter, before=before, limit=limit):
                yield item

        async def aput(
            self,
            config: dict[str, Any],
            checkpoint: Checkpoint,
            metadata: CheckpointMetadata,
            new_versions: ChannelVersions,
        ) -> dict[str, Any]:
            return self.put(config=config, checkpoint=checkpoint, metadata=metadata, new_versions=new_versions)

        async def aput_writes(
            self,
            config: dict[str, Any],
            writes: Sequence[tuple[str, Any]],
            task_id: str,
            task_path: str = "",
        ) -> None:
            self.put_writes(config=config, writes=writes, task_id=task_id, task_path=task_path)

        async def adelete_thread(self, thread_id: str) -> None:
            self.delete_thread(thread_id=thread_id)

        async def adelete_for_runs(self, run_ids: Sequence[str]) -> None:
            self.delete_for_runs(run_ids=run_ids)

        async def acopy_thread(self, source_thread_id: str, target_thread_id: str) -> None:
            self.copy_thread(source_thread_id=source_thread_id, target_thread_id=target_thread_id)

        async def aprune(
            self,
            thread_ids: Sequence[str],
            *,
            strategy: str = "keep_latest",
        ) -> None:
            self.prune(thread_ids=thread_ids, strategy=strategy)

        def _extract_thread_and_ns(self, config: dict[str, Any]) -> tuple[str, str]:
            thread_id = str(config["configurable"]["thread_id"])
            checkpoint_ns = str(config["configurable"].get("checkpoint_ns", ""))
            return thread_id, checkpoint_ns

        def _fetch_checkpoint_row(
            self,
            *,
            thread_id: str,
            checkpoint_ns: str,
            checkpoint_id: str | None,
        ) -> dict[str, Any] | None:
            psycopg, dict_row = _import_psycopg()
            with psycopg.connect(self._dsn, autocommit=True, row_factory=dict_row) as conn:
                with conn.cursor() as cur:
                    if checkpoint_id is None:
                        cur.execute(
                            f"""
                            SELECT
                                thread_id,
                                checkpoint_ns,
                                checkpoint_id,
                                parent_checkpoint_id,
                                checkpoint_payload,
                                metadata_payload
                            FROM {self._schema}.langgraph_checkpoints
                            WHERE thread_id = %s AND checkpoint_ns = %s
                            ORDER BY checkpoint_id DESC
                            LIMIT 1
                            """,
                            (thread_id, checkpoint_ns),
                        )
                    else:
                        cur.execute(
                            f"""
                            SELECT
                                thread_id,
                                checkpoint_ns,
                                checkpoint_id,
                                parent_checkpoint_id,
                                checkpoint_payload,
                                metadata_payload
                            FROM {self._schema}.langgraph_checkpoints
                            WHERE thread_id = %s AND checkpoint_ns = %s AND checkpoint_id = %s
                            LIMIT 1
                            """,
                            (thread_id, checkpoint_ns, checkpoint_id),
                        )
                    return cur.fetchone()

        def _list_checkpoint_rows(
            self,
            *,
            thread_id: str | None,
            checkpoint_ns: str | None,
            checkpoint_id: str | None,
            before_checkpoint_id: str | None,
        ) -> list[dict[str, Any]]:
            clauses = ["1=1"]
            params: list[Any] = []

            if thread_id is not None:
                clauses.append("thread_id = %s")
                params.append(thread_id)
            if checkpoint_ns is not None:
                clauses.append("checkpoint_ns = %s")
                params.append(checkpoint_ns)
            if checkpoint_id is not None:
                clauses.append("checkpoint_id = %s")
                params.append(checkpoint_id)
            if before_checkpoint_id is not None:
                clauses.append("checkpoint_id < %s")
                params.append(before_checkpoint_id)

            where_clause = " AND ".join(clauses)
            psycopg, dict_row = _import_psycopg()
            with psycopg.connect(self._dsn, autocommit=True, row_factory=dict_row) as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        f"""
                        SELECT
                            thread_id,
                            checkpoint_ns,
                            checkpoint_id,
                            parent_checkpoint_id,
                            checkpoint_payload,
                            metadata_payload
                        FROM {self._schema}.langgraph_checkpoints
                        WHERE {where_clause}
                        ORDER BY thread_id ASC, checkpoint_ns ASC, checkpoint_id DESC
                        """,
                        params,
                    )
                    return list(cur.fetchall())

        def _load_channel_values(
            self,
            *,
            thread_id: str,
            checkpoint_ns: str,
            channel_versions: Any,
        ) -> dict[str, Any]:
            if not isinstance(channel_versions, dict) or not channel_versions:
                return {}

            psycopg, dict_row = _import_psycopg()
            with psycopg.connect(self._dsn, autocommit=True, row_factory=dict_row) as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        f"""
                        SELECT channel_name, channel_version, blob_payload
                        FROM {self._schema}.langgraph_checkpoint_blobs
                        WHERE thread_id = %s AND checkpoint_ns = %s
                        """,
                        (thread_id, checkpoint_ns),
                    )
                    rows = cur.fetchall()

            blob_lookup: dict[tuple[str, str], dict[str, Any]] = {}
            for row in rows:
                blob_lookup[(row["channel_name"], row["channel_version"])] = row["blob_payload"]

            channel_values: dict[str, Any] = {}
            for channel_name, channel_version in channel_versions.items():
                encoded_blob = blob_lookup.get((str(channel_name), str(channel_version)))
                if not isinstance(encoded_blob, dict):
                    continue
                if encoded_blob.get("type") == "empty":
                    continue
                channel_values[channel_name] = self.serde.loads_typed(self._decode_typed_field(encoded_blob))
            return channel_values

        def _fetch_pending_writes(
            self,
            *,
            thread_id: str,
            checkpoint_ns: str,
            checkpoint_id: str,
        ) -> list[tuple[str, str, Any]]:
            psycopg, dict_row = _import_psycopg()
            with psycopg.connect(self._dsn, autocommit=True, row_factory=dict_row) as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        f"""
                        SELECT task_id, channel_name, value_payload
                        FROM {self._schema}.langgraph_checkpoint_writes
                        WHERE thread_id = %s AND checkpoint_ns = %s AND checkpoint_id = %s
                        ORDER BY created_at ASC, task_id ASC, write_idx ASC
                        """,
                        (thread_id, checkpoint_ns, checkpoint_id),
                    )
                    rows = cur.fetchall()

            pending_writes: list[tuple[str, str, Any]] = []
            for row in rows:
                pending_writes.append(
                    (
                        row["task_id"],
                        row["channel_name"],
                        self.serde.loads_typed(self._decode_typed_field(row["value_payload"])),
                    )
                )
            return pending_writes

        @staticmethod
        def _encode_typed_field(payload: tuple[str, bytes]) -> dict[str, str]:
            return {
                "type": payload[0],
                "blob_b64": base64.b64encode(payload[1]).decode("ascii"),
            }

        @staticmethod
        def _decode_typed_field(payload: Any) -> tuple[str, bytes]:
            if isinstance(payload, str):
                payload = json.loads(payload)
            if not isinstance(payload, dict):
                raise ValueError("Некорректный формат typed payload")

            payload_type = payload.get("type")
            payload_blob = payload.get("blob_b64")
            if not isinstance(payload_type, str) or not isinstance(payload_blob, str):
                raise ValueError("Некорректный формат typed payload")
            return payload_type, base64.b64decode(payload_blob.encode("ascii"))


def _import_psycopg():
    try:
        import psycopg
        from psycopg.rows import dict_row
    except Exception as exc:  # pragma: no cover - зависит от окружения
        raise RuntimeError(
            "Для PostgreSQL режима требуется установленный psycopg. "
            "Установите зависимость 'psycopg[binary]'."
        ) from exc
    return psycopg, dict_row
