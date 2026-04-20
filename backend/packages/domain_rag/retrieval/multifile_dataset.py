from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from schemas.rag.contracts import RetrievedBlock

_SUPPORTED_EXTENSIONS = {".md", ".txt", ".json"}
_BULLET_RE = re.compile(r"^\s*(?:[-*]|\d+\.)\s+(.+?)\s*$")
_HEADING_RE = re.compile(r"^\s*#{1,6}\s+(.+?)\s*$")
_WHITESPACE_RE = re.compile(r"\s+")


def load_multifile_case_dataset(dataset_dir: str | Path) -> tuple[list[RetrievedBlock], list[RetrievedBlock]]:
    """Собирает summary/detail блоки из директории с несколькими входными файлами."""

    root = Path(dataset_dir)
    if not root.exists():
        raise FileNotFoundError(f"Директория датасета не найдена: {root}")
    if not root.is_dir():
        raise ValueError(f"Путь датасета должен быть директорией: {root}")

    files = sorted(
        path
        for path in root.rglob("*")
        if path.is_file() and path.suffix.lower() in _SUPPORTED_EXTENSIONS
    )
    if not files:
        raise ValueError(
            f"В директории {root} нет поддерживаемых файлов ({', '.join(sorted(_SUPPORTED_EXTENSIONS))})"
        )

    summary_blocks: list[RetrievedBlock] = []
    detail_blocks: list[RetrievedBlock] = []

    for file_path in files:
        normalized_doc_id = _build_doc_id(file_path)
        document_type = _infer_document_type(file_path)
        tags = _build_tags(file_path)
        fragments = _extract_fragments(file_path)

        if not fragments:
            continue

        summary_blocks.append(
            _build_block(
                text=fragments[0],
                doc_id=normalized_doc_id,
                version="1",
                block_id="S-1",
                file_path=file_path,
                document_type=document_type,
                tags=tags,
            )
        )

        for index, text in enumerate(fragments, start=1):
            detail_blocks.append(
                _build_block(
                    text=text,
                    doc_id=normalized_doc_id,
                    version="1",
                    block_id=f"D-{index}",
                    file_path=file_path,
                    document_type=document_type,
                    tags=tags,
                )
            )

    if not summary_blocks and not detail_blocks:
        raise ValueError(f"Не удалось извлечь блоки из файлов директории: {root}")

    return summary_blocks, detail_blocks


def _extract_fragments(file_path: Path) -> list[str]:
    extension = file_path.suffix.lower()
    if extension in {".md", ".txt"}:
        return _extract_text_fragments(file_path.read_text(encoding="utf-8"))
    if extension == ".json":
        return _extract_json_fragments(file_path.read_text(encoding="utf-8"))
    return []


def _extract_text_fragments(text: str) -> list[str]:
    fragments: list[str] = []

    for line in text.splitlines():
        bullet_match = _BULLET_RE.match(line)
        if bullet_match:
            normalized = _normalize_text(bullet_match.group(1))
            if normalized:
                fragments.append(normalized)
            continue

        heading_match = _HEADING_RE.match(line)
        if heading_match:
            normalized_heading = _normalize_text(heading_match.group(1))
            if normalized_heading:
                fragments.append(normalized_heading)

    if fragments:
        return _unique_keep_order(fragments)[:24]

    paragraphs = [piece.strip() for piece in re.split(r"\n\s*\n+", text) if piece.strip()]
    if not paragraphs:
        return []

    collected: list[str] = []
    for paragraph in paragraphs:
        normalized = _normalize_text(paragraph)
        if normalized:
            collected.append(normalized)

    if not collected:
        return []
    return _unique_keep_order(collected)[:24]


def _extract_json_fragments(raw_json: str) -> list[str]:
    payload = json.loads(raw_json)
    values: list[str] = []
    _walk_json(payload, path_prefix="", out=values)
    if not values:
        return []
    return _unique_keep_order(values)[:24]


def _walk_json(value: Any, *, path_prefix: str, out: list[str]) -> None:
    if isinstance(value, dict):
        for key, nested in value.items():
            nested_prefix = f"{path_prefix}.{key}" if path_prefix else str(key)
            _walk_json(nested, path_prefix=nested_prefix, out=out)
        return

    if isinstance(value, list):
        for index, nested in enumerate(value):
            nested_prefix = f"{path_prefix}[{index}]"
            _walk_json(nested, path_prefix=nested_prefix, out=out)
        return

    if isinstance(value, (str, int, float, bool)):
        normalized_value = _normalize_text(str(value))
        if not normalized_value:
            return
        if path_prefix:
            out.append(_normalize_text(f"{path_prefix}: {normalized_value}"))
        else:
            out.append(normalized_value)


def _build_block(
    *,
    text: str,
    doc_id: str,
    version: str,
    block_id: str,
    file_path: Path,
    document_type: str,
    tags: list[str],
) -> RetrievedBlock:
    return RetrievedBlock.model_validate(
        {
            "text": text,
            "source": {
                "doc_id": doc_id,
                "version": version,
                "block_id": block_id,
            },
            "score": 0.0,
            "metadata": {
                "project_id": "p1",
                "document_type": document_type,
                "tags": tags,
                "doc_title": file_path.stem.replace("_", " ").strip() or file_path.name,
                "file_name": file_path.name,
            },
        }
    )


def _infer_document_type(file_path: Path) -> str:
    lowered = file_path.stem.lower()
    if any(token in lowered for token in ("security", "sec", "vuln", "pentest")):
        return "security"
    if any(token in lowered for token in ("ops", "rollback", "monitor", "sre")):
        return "operations"
    if any(token in lowered for token in ("approval", "governance", "policy")):
        return "governance"
    if any(token in lowered for token in ("decision", "method", "strategy")):
        return "methodology"
    return "requirements"


def _build_tags(file_path: Path) -> list[str]:
    tags = ["release", "go-no-go"]
    for token in re.split(r"[^a-z0-9]+", file_path.stem.lower()):
        normalized = token.strip()
        if not normalized:
            continue
        if normalized not in tags:
            tags.append(normalized)
    return tags


def _build_doc_id(file_path: Path) -> str:
    stem = file_path.stem
    fingerprint = sum((index + 1) * ord(char) for index, char in enumerate(stem))
    prefix = re.sub(r"[^A-Za-z0-9]+", "", stem.upper())[:3] or "DOC"
    return f"{prefix}-{fingerprint % 1000:03d}"


def _normalize_text(value: str) -> str:
    return _WHITESPACE_RE.sub(" ", value).strip()


def _unique_keep_order(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        result.append(value)
    return result
