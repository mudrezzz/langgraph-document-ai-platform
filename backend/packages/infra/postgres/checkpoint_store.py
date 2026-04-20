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


_LG_RUN_ID_PREFIX = "lg_thread:"


class LangGraphPostgresCheckpointStore(ICheckpointStore):
    """Checkpoint store для LangGraph поверх PostgreSQL с in-memory fallback."""

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
        """Возвращает checkpointer, совместимый с `StateGraph.compile(checkpointer=...)`."""

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
        """LangGraph checkpointer поверх таблицы `app.checkpoints`."""

        def __init__(self, dsn: str | None, schema: str = "app") -> None:
            super().__init__()
            if not dsn:
                raise ValueError("DSN обязателен для PostgreSQL LangGraph checkpointer")

            self._dsn = dsn
            self._schema = schema
            validate_identifier(self._schema)

        def get_tuple(self, config: dict[str, Any]) -> CheckpointTuple | None:
            thread_id = str(config["configurable"]["thread_id"])
            checkpoint_ns = str(config["configurable"].get("checkpoint_ns", ""))
            namespace_state = self._load_namespace_state(thread_id=thread_id, checkpoint_ns=checkpoint_ns)

            if namespace_state is None:
                return None

            checkpoints = namespace_state["checkpoints"]
            checkpoint_id = get_checkpoint_id(config)

            if checkpoint_id:
                selected_checkpoint_id = str(checkpoint_id)
                selected_entry = checkpoints.get(selected_checkpoint_id)
                if selected_entry is None:
                    return None
                response_config = config
            else:
                if not checkpoints:
                    return None
                selected_checkpoint_id = max(checkpoints.keys())
                selected_entry = checkpoints[selected_checkpoint_id]
                response_config = {
                    "configurable": {
                        "thread_id": thread_id,
                        "checkpoint_ns": checkpoint_ns,
                        "checkpoint_id": selected_checkpoint_id,
                    }
                }

            checkpoint_payload = self.serde.loads_typed(self._decode_typed(selected_entry["checkpoint"]))
            metadata_payload = self.serde.loads_typed(self._decode_typed(selected_entry["metadata"]))

            channel_values = self._restore_channel_values(
                checkpoint=checkpoint_payload,
                blobs=namespace_state["blobs"],
            )

            parent_checkpoint_id = selected_entry.get("parent_checkpoint_id")
            parent_config = (
                {
                    "configurable": {
                        "thread_id": thread_id,
                        "checkpoint_ns": checkpoint_ns,
                        "checkpoint_id": parent_checkpoint_id,
                    }
                }
                if parent_checkpoint_id
                else None
            )

            pending_writes = self._decode_pending_writes(
                namespace_state["writes"].get(selected_checkpoint_id, []),
            )

            return CheckpointTuple(
                config=response_config,
                checkpoint={**checkpoint_payload, "channel_values": channel_values},
                metadata=metadata_payload,
                parent_config=parent_config,
                pending_writes=pending_writes,
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
            namespace_rows = self._list_namespace_rows(thread_id=thread_id, checkpoint_ns=checkpoint_ns)

            for row_thread_id, row_checkpoint_ns, namespace_state in namespace_rows:
                checkpoints = namespace_state["checkpoints"]
                for checkpoint_id, checkpoint_entry in sorted(checkpoints.items(), key=lambda item: item[0], reverse=True):
                    if config_checkpoint_id and checkpoint_id != str(config_checkpoint_id):
                        continue
                    if before_checkpoint_id and checkpoint_id >= str(before_checkpoint_id):
                        continue

                    metadata_payload = self.serde.loads_typed(self._decode_typed(checkpoint_entry["metadata"]))
                    if filter and not all(metadata_payload.get(key) == value for key, value in filter.items()):
                        continue

                    if limit is not None:
                        if limit <= 0:
                            return
                        limit -= 1

                    checkpoint_payload = self.serde.loads_typed(self._decode_typed(checkpoint_entry["checkpoint"]))
                    channel_values = self._restore_channel_values(
                        checkpoint=checkpoint_payload,
                        blobs=namespace_state["blobs"],
                    )
                    pending_writes = self._decode_pending_writes(
                        namespace_state["writes"].get(checkpoint_id, []),
                    )

                    parent_checkpoint_id = checkpoint_entry.get("parent_checkpoint_id")
                    parent_config = (
                        {
                            "configurable": {
                                "thread_id": row_thread_id,
                                "checkpoint_ns": row_checkpoint_ns,
                                "checkpoint_id": parent_checkpoint_id,
                            }
                        }
                        if parent_checkpoint_id
                        else None
                    )

                    yield CheckpointTuple(
                        config={
                            "configurable": {
                                "thread_id": row_thread_id,
                                "checkpoint_ns": row_checkpoint_ns,
                                "checkpoint_id": checkpoint_id,
                            }
                        },
                        checkpoint={**checkpoint_payload, "channel_values": channel_values},
                        metadata=metadata_payload,
                        parent_config=parent_config,
                        pending_writes=pending_writes,
                    )

        def put(
            self,
            config: dict[str, Any],
            checkpoint: Checkpoint,
            metadata: CheckpointMetadata,
            new_versions: ChannelVersions,
        ) -> dict[str, Any]:
            thread_id = str(config["configurable"]["thread_id"])
            checkpoint_ns = str(config["configurable"].get("checkpoint_ns", ""))
            checkpoint_id = str(checkpoint["id"])

            namespace_state = self._load_namespace_state(thread_id=thread_id, checkpoint_ns=checkpoint_ns)
            if namespace_state is None:
                namespace_state = _empty_namespace_state()

            checkpoint_copy = checkpoint.copy()
            channel_values: dict[str, Any] = checkpoint_copy.pop("channel_values", {})

            for channel_name, channel_version in new_versions.items():
                blob_key = _build_blob_key(channel_name=channel_name, channel_version=channel_version)
                if channel_name in channel_values:
                    namespace_state["blobs"][blob_key] = self._encode_typed(self.serde.dumps_typed(channel_values[channel_name]))
                else:
                    namespace_state["blobs"][blob_key] = {"type": "empty", "blob_b64": ""}

            namespace_state["checkpoints"][checkpoint_id] = {
                "checkpoint": self._encode_typed(self.serde.dumps_typed(checkpoint_copy)),
                "metadata": self._encode_typed(
                    self.serde.dumps_typed(get_checkpoint_metadata(config, metadata)),
                ),
                "parent_checkpoint_id": config["configurable"].get("checkpoint_id"),
            }

            self._save_namespace_state(
                thread_id=thread_id,
                checkpoint_ns=checkpoint_ns,
                payload=namespace_state,
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
            thread_id = str(config["configurable"]["thread_id"])
            checkpoint_ns = str(config["configurable"].get("checkpoint_ns", ""))
            checkpoint_id = str(config["configurable"]["checkpoint_id"])

            namespace_state = self._load_namespace_state(thread_id=thread_id, checkpoint_ns=checkpoint_ns)
            if namespace_state is None:
                namespace_state = _empty_namespace_state()

            writes_for_checkpoint = namespace_state["writes"].setdefault(checkpoint_id, [])
            existing_keys = {
                (str(item.get("task_id", "")), int(item.get("write_idx", 0)))
                for item in writes_for_checkpoint
            }

            for index, (channel_name, value) in enumerate(writes):
                write_idx = WRITES_IDX_MAP.get(channel_name, index)
                dedupe_key = (task_id, write_idx)
                if write_idx >= 0 and dedupe_key in existing_keys:
                    continue

                writes_for_checkpoint.append(
                    {
                        "task_id": task_id,
                        "channel": channel_name,
                        "value": self._encode_typed(self.serde.dumps_typed(value)),
                        "task_path": task_path,
                        "write_idx": write_idx,
                    }
                )
                existing_keys.add(dedupe_key)

            self._save_namespace_state(
                thread_id=thread_id,
                checkpoint_ns=checkpoint_ns,
                payload=namespace_state,
            )

        def delete_thread(self, thread_id: str) -> None:
            encoded_thread_id = _encode_run_id_part(thread_id)
            pattern = f"{_LG_RUN_ID_PREFIX}{encoded_thread_id}:ns:%"
            psycopg, dict_row = _import_psycopg()

            with psycopg.connect(self._dsn, autocommit=True, row_factory=dict_row) as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        f"DELETE FROM {self._schema}.checkpoints WHERE run_id LIKE %s",
                        (pattern,),
                    )

        def delete_for_runs(self, run_ids: Sequence[str]) -> None:
            for run_id in run_ids:
                self.delete_thread(run_id)

        def copy_thread(self, source_thread_id: str, target_thread_id: str) -> None:
            for _, checkpoint_ns, payload in self._list_namespace_rows(thread_id=source_thread_id, checkpoint_ns=None):
                self._save_namespace_state(
                    thread_id=target_thread_id,
                    checkpoint_ns=checkpoint_ns,
                    payload=payload,
                )

        def prune(
            self,
            thread_ids: Sequence[str],
            *,
            strategy: str = "keep_latest",
        ) -> None:
            for thread_id in thread_ids:
                namespace_rows = self._list_namespace_rows(thread_id=thread_id, checkpoint_ns=None)
                for _, checkpoint_ns, payload in namespace_rows:
                    if strategy == "delete":
                        self._save_namespace_state(
                            thread_id=thread_id,
                            checkpoint_ns=checkpoint_ns,
                            payload=_empty_namespace_state(),
                        )
                        continue

                    checkpoints = payload["checkpoints"]
                    if not checkpoints:
                        continue

                    latest_checkpoint_id = max(checkpoints.keys())
                    latest_checkpoint = checkpoints[latest_checkpoint_id]
                    checkpoint_payload = self.serde.loads_typed(self._decode_typed(latest_checkpoint["checkpoint"]))

                    channel_versions = checkpoint_payload.get("channel_versions", {})
                    blob_keys = {
                        _build_blob_key(channel_name=channel_name, channel_version=channel_version)
                        for channel_name, channel_version in channel_versions.items()
                    }

                    payload["checkpoints"] = {latest_checkpoint_id: latest_checkpoint}
                    payload["writes"] = {
                        latest_checkpoint_id: payload["writes"].get(latest_checkpoint_id, []),
                    }
                    payload["blobs"] = {
                        blob_key: blob_payload
                        for blob_key, blob_payload in payload["blobs"].items()
                        if blob_key in blob_keys
                    }

                    self._save_namespace_state(
                        thread_id=thread_id,
                        checkpoint_ns=checkpoint_ns,
                        payload=payload,
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

        def _load_namespace_state(self, *, thread_id: str, checkpoint_ns: str) -> dict[str, Any] | None:
            run_id = _build_namespace_run_id(thread_id=thread_id, checkpoint_ns=checkpoint_ns)
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
                payload = json.loads(payload)
            if not isinstance(payload, dict):
                return _empty_namespace_state()

            return _normalize_namespace_state(payload)

        def _save_namespace_state(self, *, thread_id: str, checkpoint_ns: str, payload: dict[str, Any]) -> None:
            run_id = _build_namespace_run_id(thread_id=thread_id, checkpoint_ns=checkpoint_ns)
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

        def _list_namespace_rows(
            self,
            *,
            thread_id: str | None,
            checkpoint_ns: str | None,
        ) -> list[tuple[str, str, dict[str, Any]]]:
            psycopg, dict_row = _import_psycopg()
            clauses = [f"run_id LIKE '{_LG_RUN_ID_PREFIX}%'"]
            params: list[Any] = []

            if thread_id is not None and checkpoint_ns is not None:
                clauses = ["run_id = %s"]
                params = [_build_namespace_run_id(thread_id=thread_id, checkpoint_ns=str(checkpoint_ns))]
            elif thread_id is not None:
                clauses.append("run_id LIKE %s")
                params.append(f"{_LG_RUN_ID_PREFIX}{_encode_run_id_part(thread_id)}:ns:%")

            where_clause = " AND ".join(clauses)

            with psycopg.connect(self._dsn, autocommit=True, row_factory=dict_row) as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        f"SELECT run_id, payload FROM {self._schema}.checkpoints WHERE {where_clause}",
                        params,
                    )
                    rows = cur.fetchall()

            result: list[tuple[str, str, dict[str, Any]]] = []
            for row in rows:
                run_id = row["run_id"]
                parsed = _parse_namespace_run_id(run_id)
                if parsed is None:
                    continue

                row_thread_id, row_checkpoint_ns = parsed
                if checkpoint_ns is not None and row_checkpoint_ns != str(checkpoint_ns):
                    continue

                payload = row["payload"]
                if isinstance(payload, str):
                    payload = json.loads(payload)
                if not isinstance(payload, dict):
                    continue
                result.append((row_thread_id, row_checkpoint_ns, _normalize_namespace_state(payload)))

            return result

        def _restore_channel_values(self, *, checkpoint: dict[str, Any], blobs: dict[str, Any]) -> dict[str, Any]:
            channel_values: dict[str, Any] = {}
            channel_versions = checkpoint.get("channel_versions", {})
            if not isinstance(channel_versions, dict):
                return channel_values

            for channel_name, channel_version in channel_versions.items():
                blob_key = _build_blob_key(channel_name=channel_name, channel_version=channel_version)
                encoded_blob = blobs.get(blob_key)
                if not isinstance(encoded_blob, dict):
                    continue
                if encoded_blob.get("type") == "empty":
                    continue
                channel_values[channel_name] = self.serde.loads_typed(self._decode_typed(encoded_blob))
            return channel_values

        def _decode_pending_writes(self, encoded_writes: list[dict[str, Any]]) -> list[tuple[str, str, Any]]:
            result: list[tuple[str, str, Any]] = []
            for item in encoded_writes:
                task_id = item.get("task_id")
                channel_name = item.get("channel")
                encoded_value = item.get("value")
                if not isinstance(task_id, str) or not isinstance(channel_name, str):
                    continue
                if not isinstance(encoded_value, dict):
                    continue
                result.append((task_id, channel_name, self.serde.loads_typed(self._decode_typed(encoded_value))))
            return result

        @staticmethod
        def _encode_typed(typed_payload: tuple[str, bytes]) -> dict[str, str]:
            return {
                "type": typed_payload[0],
                "blob_b64": base64.b64encode(typed_payload[1]).decode("ascii"),
            }

        @staticmethod
        def _decode_typed(payload: dict[str, Any]) -> tuple[str, bytes]:
            payload_type = payload.get("type")
            payload_blob = payload.get("blob_b64")
            if not isinstance(payload_type, str) or not isinstance(payload_blob, str):
                raise ValueError("Некорректный формат typed payload в PostgreSQL checkpointer")

            return payload_type, base64.b64decode(payload_blob.encode("ascii"))


def _empty_namespace_state() -> dict[str, Any]:
    return {
        "checkpoints": {},
        "blobs": {},
        "writes": {},
    }


def _normalize_namespace_state(payload: dict[str, Any]) -> dict[str, Any]:
    checkpoints = payload.get("checkpoints")
    blobs = payload.get("blobs")
    writes = payload.get("writes")

    return {
        "checkpoints": checkpoints if isinstance(checkpoints, dict) else {},
        "blobs": blobs if isinstance(blobs, dict) else {},
        "writes": writes if isinstance(writes, dict) else {},
    }


def _build_blob_key(*, channel_name: str, channel_version: Any) -> str:
    return f"{channel_name}::{channel_version}"


def _build_namespace_run_id(*, thread_id: str, checkpoint_ns: str) -> str:
    return f"{_LG_RUN_ID_PREFIX}{_encode_run_id_part(thread_id)}:ns:{_encode_run_id_part(checkpoint_ns)}"


def _parse_namespace_run_id(run_id: str) -> tuple[str, str] | None:
    if not run_id.startswith(_LG_RUN_ID_PREFIX):
        return None

    parts = run_id.split(":")
    if len(parts) != 4 or parts[2] != "ns":
        return None

    try:
        return _decode_run_id_part(parts[1]), _decode_run_id_part(parts[3])
    except Exception:
        return None


def _encode_run_id_part(value: str) -> str:
    raw = value.encode("utf-8")
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def _decode_run_id_part(value: str) -> str:
    padding = "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode((value + padding).encode("ascii")).decode("utf-8")


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
