from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from schemas.documents.contracts import (
    CanonicalContentBlock,
    CanonicalDocument,
    CanonicalSectionSummary,
    CanonicalStructureNode,
)

_SUPPORTED_EXTENSIONS = {".md", ".txt", ".json", ".docx", ".pdf"}
_HEADING_RE = re.compile(r"^\s*(#{1,6})\s+(.+?)\s*$")
_BULLET_RE = re.compile(r"^\s*(?:[-*]|\d+\.)\s+(.+?)\s*$")
_WHITESPACE_RE = re.compile(r"\s+")


class CanonicalDocumentParser:
    """Parser MVP for text-like sources into canonical document contracts."""

    def supported_extensions(self) -> set[str]:
        return set(_SUPPORTED_EXTENSIONS)

    def parse_path(self, source_path: str | Path, *, version: str = "1") -> CanonicalDocument:
        path = Path(source_path)
        if not path.exists():
            raise FileNotFoundError(f"Документ не найден: {path}")
        if not path.is_file():
            raise ValueError(f"Путь документа должен быть файлом: {path}")

        extension = path.suffix.lower()
        if extension not in _SUPPORTED_EXTENSIONS:
            raise ValueError(f"Неподдерживаемый формат документа: {extension}")

        doc_id = _build_doc_id(path)
        quality_flags: list[str] = []

        if extension == ".json":
            raw_text = path.read_text(encoding="utf-8")
            blocks, structure = self._parse_json(raw_text, quality_flags=quality_flags)
        elif extension == ".docx":
            blocks, structure = self._parse_docx(path, quality_flags=quality_flags)
            raw_text = "\n".join(block.text for block in blocks)
        elif extension == ".pdf":
            blocks, structure = self._parse_pdf(path, quality_flags=quality_flags)
            raw_text = "\n".join(block.text for block in blocks)
        else:
            raw_text = path.read_text(encoding="utf-8")
            blocks, structure = self._parse_text(raw_text, markdown=extension == ".md", quality_flags=quality_flags)

        if not raw_text.strip():
            quality_flags.append("empty_document")
        if not blocks:
            quality_flags.append("no_content_blocks")

        summaries = _build_section_summaries(blocks, structure)
        return CanonicalDocument(
            doc_id=doc_id,
            source_path=str(path),
            version=version,
            file_type=extension.lstrip("."),
            metadata_profile={
                "file_name": path.name,
                "file_size_bytes": path.stat().st_size,
                "project_id": "p1",
                "document_type": _infer_document_type(path),
                "tags": _build_tags(path),
                "parser": self.__class__.__name__,
                "supported_mime_family": "text",
            },
            structure_tree=structure,
            content_blocks=blocks,
            extracted_tables=[],
            section_summaries=summaries,
            quality_flags=_unique_keep_order(quality_flags),
        )

    def parse_dir(self, source_dir: str | Path, *, version: str = "1") -> list[CanonicalDocument]:
        root = Path(source_dir)
        if not root.exists():
            raise FileNotFoundError(f"Директория документов не найдена: {root}")
        if not root.is_dir():
            raise ValueError(f"Путь должен быть директорией: {root}")

        files = sorted(path for path in root.rglob("*") if path.is_file() and path.suffix.lower() in _SUPPORTED_EXTENSIONS)
        if not files:
            raise ValueError(f"В директории {root} нет поддерживаемых документов")
        return [self.parse_path(path, version=version) for path in files]

    def _parse_text(
        self,
        raw_text: str,
        *,
        markdown: bool,
        quality_flags: list[str],
    ) -> tuple[list[CanonicalContentBlock], CanonicalStructureNode]:
        blocks: list[CanonicalContentBlock] = []
        root = CanonicalStructureNode(node_id="root", title="Document", level=0)
        heading_stack: list[tuple[int, str]] = []
        current_heading_path: list[str] = []
        current_node = root
        paragraph_buffer: list[str] = []

        def flush_paragraph() -> None:
            nonlocal paragraph_buffer
            text = _normalize_text(" ".join(paragraph_buffer))
            paragraph_buffer = []
            if not text:
                return
            block = _build_block(
                text=text,
                block_type="paragraph",
                index=len(blocks) + 1,
                heading_path=current_heading_path,
            )
            blocks.append(block)
            current_node.block_ids.append(block.block_id)

        for raw_line in raw_text.splitlines():
            heading_match = _HEADING_RE.match(raw_line) if markdown else None
            if heading_match:
                flush_paragraph()
                title = _normalize_text(heading_match.group(2))
                level = len(heading_match.group(1))
                heading_stack = [(item_level, item_title) for item_level, item_title in heading_stack if item_level < level]
                heading_stack.append((level, title))
                current_heading_path = [item_title for _, item_title in heading_stack]
                current_node = CanonicalStructureNode(
                    node_id=f"section-{len(root.children) + 1}",
                    title=title,
                    level=level,
                )
                root.children.append(current_node)
                continue

            bullet_match = _BULLET_RE.match(raw_line)
            if bullet_match:
                flush_paragraph()
                block = _build_block(
                    text=_normalize_text(bullet_match.group(1)),
                    block_type="bullet",
                    index=len(blocks) + 1,
                    heading_path=current_heading_path,
                )
                blocks.append(block)
                current_node.block_ids.append(block.block_id)
                continue

            if raw_line.strip():
                paragraph_buffer.append(raw_line.strip())
            else:
                flush_paragraph()

        flush_paragraph()

        if markdown and not root.children:
            quality_flags.append("no_structural_headings")
        if not markdown and blocks:
            root.block_ids = [block.block_id for block in blocks]
        return blocks, root

    def _parse_json(
        self,
        raw_text: str,
        *,
        quality_flags: list[str],
    ) -> tuple[list[CanonicalContentBlock], CanonicalStructureNode]:
        try:
            payload = json.loads(raw_text)
        except json.JSONDecodeError as exc:
            quality_flags.append("json_parse_failed")
            raise ValueError(f"Некорректный JSON документ: {exc}") from exc

        values: list[tuple[str, str]] = []
        _walk_json(payload, path_prefix="", out=values)

        root = CanonicalStructureNode(node_id="root", title="JSON Document", level=0)
        blocks: list[CanonicalContentBlock] = []
        for index, (path, value) in enumerate(values, start=1):
            block = _build_block(
                text=f"{path}: {value}" if path else value,
                block_type="json_value",
                index=index,
                heading_path=[path] if path else [],
                metadata={"json_path": path},
            )
            blocks.append(block)
            root.block_ids.append(block.block_id)
        return blocks, root

    def _parse_docx(
        self,
        path: Path,
        *,
        quality_flags: list[str],
    ) -> tuple[list[CanonicalContentBlock], CanonicalStructureNode]:
        try:
            from docx import Document
        except Exception as exc:  # pragma: no cover - depends on optional runtime package
            raise RuntimeError("Для DOCX parsing требуется зависимость python-docx") from exc

        document = Document(str(path))
        blocks: list[CanonicalContentBlock] = []
        root = CanonicalStructureNode(node_id="root", title="DOCX Document", level=0)
        current_node = root
        current_heading_path: list[str] = []

        for paragraph in document.paragraphs:
            text = _normalize_text(paragraph.text)
            if not text:
                continue

            style_name = getattr(paragraph.style, "name", "") or ""
            if style_name.lower().startswith("heading"):
                current_heading_path = [text]
                current_node = CanonicalStructureNode(
                    node_id=f"section-{len(root.children) + 1}",
                    title=text,
                    level=_parse_heading_level(style_name),
                )
                root.children.append(current_node)
                continue

            block = _build_block(
                text=text,
                block_type="paragraph",
                index=len(blocks) + 1,
                heading_path=current_heading_path,
                metadata={"style": style_name} if style_name else None,
            )
            blocks.append(block)
            current_node.block_ids.append(block.block_id)

        if not root.children:
            quality_flags.append("no_structural_headings")
            root.block_ids = [block.block_id for block in blocks]
        return blocks, root

    def _parse_pdf(
        self,
        path: Path,
        *,
        quality_flags: list[str],
    ) -> tuple[list[CanonicalContentBlock], CanonicalStructureNode]:
        try:
            import fitz
        except Exception as exc:  # pragma: no cover - depends on optional runtime package
            raise RuntimeError("Для PDF parsing требуется зависимость PyMuPDF") from exc

        root = CanonicalStructureNode(node_id="root", title="PDF Document", level=0)
        blocks: list[CanonicalContentBlock] = []
        with fitz.open(str(path)) as pdf_document:
            for page_index, page in enumerate(pdf_document, start=1):
                page_text = page.get_text("text")
                for paragraph in re.split(r"\n\s*\n+", page_text):
                    text = _normalize_text(paragraph)
                    if not text:
                        continue
                    block = _build_block(
                        text=text,
                        block_type="paragraph",
                        index=len(blocks) + 1,
                        heading_path=[f"Page {page_index}"],
                        metadata={"page_number": page_index},
                    )
                    block.page_number = page_index
                    blocks.append(block)
                    root.block_ids.append(block.block_id)

        if not blocks:
            quality_flags.append("pdf_no_extractable_text")
        if blocks and len(blocks) < 2:
            quality_flags.append("low_text_density")
        return blocks, root


def _build_block(
    *,
    text: str,
    block_type: str,
    index: int,
    heading_path: list[str],
    metadata: dict[str, Any] | None = None,
) -> CanonicalContentBlock:
    return CanonicalContentBlock(
        block_id=f"B-{index}",
        block_type=block_type,
        text=text,
        heading_path=list(heading_path),
        metadata=metadata or {},
    )


def _walk_json(value: Any, *, path_prefix: str, out: list[tuple[str, str]]) -> None:
    if isinstance(value, dict):
        for key, nested in value.items():
            nested_prefix = f"{path_prefix}.{key}" if path_prefix else str(key)
            _walk_json(nested, path_prefix=nested_prefix, out=out)
        return
    if isinstance(value, list):
        for index, nested in enumerate(value):
            _walk_json(nested, path_prefix=f"{path_prefix}[{index}]", out=out)
        return
    if isinstance(value, (str, int, float, bool)):
        normalized = _normalize_text(str(value))
        if normalized:
            out.append((path_prefix, normalized))


def _build_section_summaries(
    blocks: list[CanonicalContentBlock],
    structure: CanonicalStructureNode,
) -> list[CanonicalSectionSummary]:
    if not blocks:
        return []

    summaries: list[CanonicalSectionSummary] = []
    nodes = structure.children or [structure]
    block_by_id = {block.block_id: block for block in blocks}

    for node in nodes:
        node_blocks = [block_by_id[block_id] for block_id in node.block_ids if block_id in block_by_id]
        if not node_blocks and node is structure:
            node_blocks = blocks[:3]
        if not node_blocks:
            continue
        summary_text = _normalize_text(" ".join(block.text for block in node_blocks))[:320]
        summaries.append(
            CanonicalSectionSummary(
                section_id=node.node_id,
                title=node.title,
                summary=summary_text,
                source_block_ids=[block.block_id for block in node_blocks],
            )
        )
    return summaries


def _build_doc_id(path: Path) -> str:
    stem = path.stem
    fingerprint = sum((index + 1) * ord(char) for index, char in enumerate(str(path)))
    prefix = re.sub(r"[^A-Za-z0-9]+", "", stem.upper())[:8] or "DOC"
    return f"{prefix}-{fingerprint % 10000:04d}"


def _parse_heading_level(style_name: str) -> int:
    match = re.search(r"(\d+)", style_name)
    if not match:
        return 1
    return int(match.group(1))


def _infer_document_type(path: Path) -> str:
    lowered = path.stem.lower()
    if any(token in lowered for token in ("security", "sec", "vuln", "pentest")):
        return "security"
    if any(token in lowered for token in ("ops", "rollback", "monitor", "sre")):
        return "operations"
    if any(token in lowered for token in ("approval", "governance", "policy")):
        return "governance"
    if any(token in lowered for token in ("decision", "method", "strategy", "scope")):
        return "methodology"
    return "requirements"


def _build_tags(path: Path) -> list[str]:
    tags = []
    for token in re.split(r"[^a-z0-9]+", path.stem.lower()):
        normalized = token.strip()
        if normalized and normalized not in tags:
            tags.append(normalized)
    return tags


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
