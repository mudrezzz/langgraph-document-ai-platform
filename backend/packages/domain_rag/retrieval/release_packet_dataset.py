from __future__ import annotations

import re
from pathlib import Path

from schemas.rag.contracts import RetrievedBlock


_SECTION_RE = re.compile(r"^##\s+(.+?)\s*$")
_BULLET_RE = re.compile(r"^\s*(?:[-*]|\d+\.)\s+(.+?)\s*$")
_WHITESPACE_RE = re.compile(r"\s+")

_SECTION_META: dict[str, dict[str, str]] = {
    "Scope": {
        "doc_id": "REL-001",
        "version": "1",
        "document_type": "requirements",
    },
    "Release Decision": {
        "doc_id": "REL-001",
        "version": "1",
        "document_type": "methodology",
    },
    "Key Risks": {
        "doc_id": "RISK-014",
        "version": "2",
        "document_type": "requirements",
    },
    "Security": {
        "doc_id": "SEC-021",
        "version": "1",
        "document_type": "security",
    },
    "Ops Readiness": {
        "doc_id": "OPS-017",
        "version": "3",
        "document_type": "operations",
    },
    "Approvals": {
        "doc_id": "GOV-009",
        "version": "4",
        "document_type": "governance",
    },
    "Rollback Plan": {
        "doc_id": "OPS-017",
        "version": "3",
        "document_type": "operations",
    },
    "Monitoring": {
        "doc_id": "OPS-028",
        "version": "1",
        "document_type": "operations",
    },
}

_SUMMARY_SECTIONS = ("Release Decision", "Key Risks", "Approvals")


def build_release_packet_dataset(
    *,
    markdown_path: str | Path,
    dataset_id: str = "release_go_no_go",
) -> dict:
    """Строит retrieval-датасет из markdown release packet."""

    path = Path(markdown_path)
    if not path.exists():
        raise FileNotFoundError(f"Файл release packet не найден: {path}")

    sections = _split_sections(path.read_text(encoding="utf-8"))
    if not sections:
        raise ValueError("Release packet не содержит секций уровня '##'")

    summary_blocks: list[RetrievedBlock] = []
    detail_blocks: list[RetrievedBlock] = []

    for section_name, section_body in sections.items():
        meta = _SECTION_META.get(section_name, _default_meta_for_unknown_section(section_name))
        block_prefix = _build_block_prefix(section_name)
        tags = _build_tags(section_name)

        if section_name in _SUMMARY_SECTIONS:
            summary_text = _extract_summary_text(section_body)
            if summary_text:
                summary_blocks.append(
                    _build_block(
                        text=summary_text,
                        doc_id=meta["doc_id"],
                        version=meta["version"],
                        block_id=f"{block_prefix}-S1",
                        section=section_name,
                        document_type=meta["document_type"],
                        tags=tags,
                    )
                )

        details = _extract_detail_items(section_body)
        for index, item in enumerate(details, start=1):
            detail_blocks.append(
                _build_block(
                    text=item,
                    doc_id=meta["doc_id"],
                    version=meta["version"],
                    block_id=f"{block_prefix}-D{index}",
                    section=section_name,
                    document_type=meta["document_type"],
                    tags=tags,
                )
            )

    if not summary_blocks and not detail_blocks:
        raise ValueError("Release packet не содержит извлекаемых блоков")

    return {
        "dataset_id": dataset_id,
        "description": "Датасет релизного пакета для go/no-go readiness анализа",
        "summary_blocks": [item.model_dump(mode="json") for item in summary_blocks],
        "detail_blocks": [item.model_dump(mode="json") for item in detail_blocks],
    }


def _split_sections(markdown_text: str) -> dict[str, str]:
    sections: dict[str, str] = {}
    current_name: str | None = None
    current_lines: list[str] = []

    for raw_line in markdown_text.splitlines():
        match = _SECTION_RE.match(raw_line)
        if match:
            if current_name is not None:
                sections[current_name] = "\n".join(current_lines).strip()
            current_name = match.group(1).strip()
            current_lines = []
            continue

        if current_name is not None:
            current_lines.append(raw_line)

    if current_name is not None:
        sections[current_name] = "\n".join(current_lines).strip()

    return sections


def _extract_summary_text(section_body: str) -> str | None:
    candidates = _extract_detail_items(section_body)
    if candidates:
        return candidates[0]
    normalized = _normalize_text(section_body)
    return normalized or None


def _extract_detail_items(section_body: str) -> list[str]:
    items: list[str] = []
    for line in section_body.splitlines():
        match = _BULLET_RE.match(line)
        if match:
            normalized = _normalize_text(match.group(1))
            if normalized:
                items.append(normalized)

    if items:
        return items

    normalized = _normalize_text(section_body)
    if not normalized:
        return []

    fragments = [fragment.strip() for fragment in re.split(r"(?<=[.!?])\s+", normalized) if fragment.strip()]
    if not fragments:
        return [normalized]
    return fragments[:3]


def _build_block(
    *,
    text: str,
    doc_id: str,
    version: str,
    block_id: str,
    section: str,
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
                "doc_title": "Release Packet: Payments v2",
                "section": section,
            },
        }
    )


def _build_block_prefix(section_name: str) -> str:
    normalized = re.sub(r"[^A-Za-z0-9]+", "-", section_name.upper()).strip("-")
    return normalized or "SECTION"


def _build_tags(section_name: str) -> list[str]:
    base = ["release", "go-no-go"]
    slug = re.sub(r"[^a-z0-9]+", "-", section_name.lower()).strip("-")
    if slug:
        base.append(slug)
    return base


def _default_meta_for_unknown_section(section_name: str) -> dict[str, str]:
    # Для неизвестных секций сохраняем техничный fallback, чтобы не терять данные.
    fingerprint = sum((index + 1) * ord(char) for index, char in enumerate(section_name))
    return {
        "doc_id": f"REL-{fingerprint % 1000:03d}",
        "version": "1",
        "document_type": "requirements",
    }


def _normalize_text(text: str) -> str:
    without_checks = text.replace("- [x]", "").replace("- [ ]", "")
    normalized = _WHITESPACE_RE.sub(" ", without_checks).strip()
    return normalized
